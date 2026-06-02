from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..config import SEARCH
from ..pipeline.normalizer import make_offer_id
from ..storage.models import Offer
from .base import BaseScraper

_SEARCH_URL = "https://www.hellowork.com/fr-fr/emploi/recherche.html"
_JOB_BASE = "https://www.hellowork.com"
_RESULTS_PER_PAGE = 30
_MAX_PAGES = 5

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Mots-clés envoyés à Hellowork. "alternance" est inclus dans le keyword
# car le paramètre de filtre contrat n'est pas fiable sur l'URL de recherche.
_KEYWORDS = [
    f"{kw} alternance"
    for kw in ["développeur web", "développeur application", "développeur fullstack"]
]


class HelloworkScraper(BaseScraper):
    name = "hellowork"

    def fetch(self) -> list[Offer]:
        offers: list[Offer] = []
        seen_ids: set[str] = set()

        for keyword in _KEYWORDS:
            for page in range(1, _MAX_PAGES + 1):
                page_offers = self._fetch_page(keyword, page)
                if not page_offers:
                    break
                for offer in page_offers:
                    if offer.id not in seen_ids:
                        seen_ids.add(offer.id)
                        offers.append(offer)
                if len(page_offers) < _RESULTS_PER_PAGE:
                    break  # dernière page

        return offers

    def _fetch_page(self, keyword: str, page: int) -> list[Offer]:
        params = {
            "k": keyword,
            "l": f"{SEARCH['location_label']} ({SEARCH['department']})",
            "ray": SEARCH["radius_km"],
            "p": page,
        }
        resp = requests.get(
            _SEARCH_URL, params=params, headers=_HEADERS, timeout=15
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("li", attrs={"data-hide-offer-item-id-value": True})
        return [o for card in cards if (o := self._parse_card(card))]

    def _parse_card(self, card) -> Optional[Offer]:
        try:
            job_id = card.get("data-hide-offer-item-id-value", "")

            title_input = card.find("input", {"name": "title"})
            company_input = card.find("input", {"name": "company"})
            title = title_input["value"] if title_input else ""
            company = company_input["value"] if company_input else "Entreprise inconnue"

            if not title:
                return None

            loc_div = card.find(attrs={"data-cy": "localisationCard"})
            location = loc_div.get_text(strip=True) if loc_div else SEARCH["location_label"]

            ct_div = card.find(attrs={"data-cy": "contractCard"})
            contract_type = ct_div.get_text(strip=True) if ct_div else "alternance"

            url = f"{_JOB_BASE}/fr-fr/emplois/{job_id}.html" if job_id else ""

            return Offer(
                id=make_offer_id(title, company, location),
                title=title,
                company=company,
                location=location,
                description="",  # non disponible sur la page de recherche
                url=url,
                source=self.name,
                posted_at=None,
                contract_type=contract_type,
            )
        except Exception:
            return None
