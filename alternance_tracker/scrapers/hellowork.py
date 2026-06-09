"""Scraper HelloWork via Playwright (Chrome réel + stealth).

HelloWork charge ses résultats organiques uniquement après qu'une session
browser authentique soit établie côté serveur (via cookies de session). Une
navigation directe en requête HTTP classique (ou Playwright sans warmup) ne
retourne qu'une offre sponsorisée.

Mécanisme retenu :
  1. Warmup : visite la homepage + soumet le formulaire de recherche → les
     cookies de session sont positionnés et HelloWork "fait confiance" au
     navigateur pour les navigations suivantes.
  2. Navigation directe vers les pages de recherche paginées avec le filtre
     `c=Alternance` — le serveur retourne alors la liste complète.
"""

import json
import time
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from ..config import SEARCH
from ..pipeline.normalizer import make_offer_id
from ..storage.models import Offer
from .base import BaseScraper

_HOME_URL = "https://www.hellowork.com/fr-fr/"
_SEARCH_URL = "https://www.hellowork.com/fr-fr/emploi/recherche.html"
_JOB_BASE = "https://www.hellowork.com"
_MAX_PAGES = 5

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_KEYWORDS = [
    "développeur web",
    "développeur application",
    "développeur fullstack",
]


class HelloworkScraper(BaseScraper):
    name = "hellowork"

    def fetch(self) -> list[Offer]:
        try:
            from playwright.sync_api import TimeoutError as PWTimeout
            from playwright.sync_api import sync_playwright
            from playwright_stealth import Stealth
        except ImportError as e:
            raise ImportError(
                f"Dépendance manquante : {e}\n"
                "  pip install playwright playwright-stealth\n"
                "  py -m playwright install chromium"
            ) from e

        offers: list[Offer] = []
        seen_ids: set[str] = set()

        with Stealth().use_sync(sync_playwright()) as pw:
            browser = self._launch_browser(pw)
            context = browser.new_context(
                user_agent=_USER_AGENT,
                locale="fr-FR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            self._warmup(page)

            for keyword in _KEYWORDS:
                self._scrape_keyword(page, keyword, seen_ids, offers, PWTimeout)

            pw_cookies = context.cookies()
            browser.close()

        session = requests.Session()
        session.headers.update({
            "User-Agent": _USER_AGENT,
            "Accept-Language": "fr-FR,fr;q=0.9",
        })
        for c in pw_cookies:
            session.cookies.set(c["name"], c["value"])

        for offer in offers:
            if offer.url:
                offer.description = self._fetch_description(offer.url, session)
                time.sleep(0.3)

        return offers

    def _launch_browser(self, pw):
        # Chrome réel (si installé) → fingerprint TLS authentique
        try:
            return pw.chromium.launch(
                channel="chrome",
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            return pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )

    def _warmup(self, page) -> None:
        page.goto(_HOME_URL, wait_until="networkidle", timeout=30_000)
        try:
            page.fill("input[name='k']", "développeur", timeout=5_000)
            page.fill("input[name='l']", SEARCH["location_label"], timeout=5_000)
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        time.sleep(1)

    def _scrape_keyword(self, page, keyword: str, seen_ids: set, offers: list, PWTimeout) -> None:
        for page_num in range(1, _MAX_PAGES + 1):
            params = {
                "k": keyword,
                "l": SEARCH["location_label"],
                "ray": SEARCH["radius_km"],
                "c": "Alternance",
                "p": page_num,
            }
            page.goto(
                f"{_SEARCH_URL}?{urlencode(params)}",
                wait_until="networkidle",
                timeout=30_000,
            )

            try:
                page.wait_for_selector("li[data-hide-offer-item-id-value]", timeout=8_000)
            except PWTimeout:
                break

            cards = page.query_selector_all("li[data-hide-offer-item-id-value]")
            if not cards:
                break

            for card in cards:
                offer = self._parse_card(card)
                if offer and offer.id not in seen_ids:
                    seen_ids.add(offer.id)
                    offers.append(offer)

            time.sleep(0.8)

    def _parse_card(self, card) -> Optional[Offer]:
        try:
            job_id = card.get_attribute("data-hide-offer-item-id-value") or ""

            title_el = card.query_selector("input[name='title']")
            company_el = card.query_selector("input[name='company']")
            title = (title_el.get_attribute("value") if title_el else "") or ""
            company = (company_el.get_attribute("value") if company_el else "") or "Entreprise inconnue"

            if not title:
                return None

            loc_el = card.query_selector("[data-cy='localisationCard']")
            location = loc_el.inner_text().strip() if loc_el else SEARCH["location_label"]

            ct_el = card.query_selector("[data-cy='contractCard']")
            contract_type = ct_el.inner_text().strip() if ct_el else "Alternance"

            url = f"{_JOB_BASE}/fr-fr/emplois/{job_id}.html" if job_id else ""

            return Offer(
                id=make_offer_id(title, company, location),
                title=title,
                company=company,
                location=location,
                description="",
                url=url,
                source=self.name,
                posted_at=None,
                contract_type=contract_type,
            )
        except Exception:
            return None

    def _fetch_description(self, url: str, session: requests.Session) -> str:
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and "description" in data:
                        return BeautifulSoup(data["description"], "html.parser").get_text(
                            separator="\n", strip=True
                        )
                except Exception:
                    continue

            div = soup.find("div", attrs={"data-controller": "truncate-text"})
            if div:
                return div.get_text(separator="\n", strip=True)

            return ""
        except Exception:
            return ""
