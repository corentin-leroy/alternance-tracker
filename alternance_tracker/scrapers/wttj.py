import os
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from ..config import SEARCH
from ..pipeline.normalizer import make_offer_id, parse_date
from ..storage.models import Offer
from .base import BaseScraper

load_dotenv()

_SIGNIN_URL = "https://www.welcometothejungle.com/fr/authenticate/signin"
_LOGIN_API = "https://api.welcometothejungle.com/api/v1/sessions"
_SEARCH_API = "https://api.welcometothejungle.com/api/v3/search/jobs"
_JOB_URL_TPL = "https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{job_slug}"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PER_PAGE = 30
_MAX_PAGES = 5


def _search_page_url() -> str:
    qs = urlencode({
        "query": "développeur",
        "contract_type_names[]": "Alternance / Apprentissage",
        "aroundQuery": SEARCH["location_label"],
    })
    return f"https://www.welcometothejungle.com/fr/jobs?{qs}"


class WttjScraper(BaseScraper):
    name = "wttj"

    def __init__(self):
        self.email = os.getenv("WTTJ_EMAIL", "")
        self.password = os.getenv("WTTJ_PASSWORD", "")

    def fetch(self) -> list[Offer]:
        if not self.email or not self.password:
            raise EnvironmentError(
                "WTTJ_EMAIL et WTTJ_PASSWORD absents — ajoute-les dans ton .env."
            )
        session = self._build_authenticated_session()
        return self._fetch_pages(session)

    # ------------------------------------------------------------------
    # Authentification
    # ------------------------------------------------------------------

    def _build_authenticated_session(self) -> requests.Session:
        """
        1. Playwright charge la page signin pour récupérer les cookies JS
           (csrf-token, wttj_api_session_key…).
        2. requests fait le POST de login avec ces cookies — sans sec-ch-ua
           qui trahissait HeadlessChrome.
        3. Retourne une session requests authentifiée prête pour l'API.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright n'est pas installé.\n"
                "  pip install playwright && py -m playwright install chromium"
            )

        # Étape 1 : cookies initiaux via Playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=_USER_AGENT,
                locale="fr-FR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page.goto(_SIGNIN_URL, wait_until="networkidle", timeout=30_000)
            pw_cookies = context.cookies()
            browser.close()

        csrf = next((c["value"] for c in pw_cookies if c["name"] == "csrf-token"), "")
        if not csrf:
            raise RuntimeError("WTTJ : csrf-token introuvable dans les cookies de la page signin.")

        # Étape 2 : POST de login via requests (pas de sec-ch-ua)
        # On gère les cookies manuellement en header string pour éviter
        # les conflits de noms entre domaines dans le cookie jar de requests.
        cookie_map: dict[str, str] = {}
        for c in pw_cookies:
            # En cas de doublon, on privilégie api. > www. > autres
            domain = c.get("domain", "")
            existing_domain = ""  # inconnu si première insertion
            if c["name"] not in cookie_map or "api.welcometothejungle" in domain:
                cookie_map[c["name"]] = c["value"]

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookie_map.items())

        session = requests.Session()
        # Désactiver la gestion automatique des cookies pour garder le contrôle total
        session.cookies.clear()
        session.headers.update({
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.welcometothejungle.com",
            "Referer": _SIGNIN_URL,
            "Wttj-User-Language": "fr",
            "Cookie": cookie_header,
            "X-Csrf-Token": csrf,
        })

        resp = session.post(
            _LOGIN_API,
            data={"session[email]": self.email, "session[password]": self.password},
            timeout=15,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"WTTJ : échec de la connexion (HTTP {resp.status_code}). "
                f"Vérifiez WTTJ_EMAIL et WTTJ_PASSWORD dans votre .env.\n"
                f"Détail : {resp.text[:200]}"
            )

        # Mettre à jour le cookie header avec les nouveaux cookies post-login
        for name, value in resp.cookies.items():
            cookie_map[name] = value
        new_csrf = cookie_map.get("csrf-token", csrf)
        session.headers.update({
            "Cookie": "; ".join(f"{k}={v}" for k, v in cookie_map.items()),
            "X-Csrf-Token": new_csrf,
        })
        # Vider le jar pour éviter toute interférence avec le header Cookie manuel
        session.cookies.clear()

        return session

    # ------------------------------------------------------------------
    # Récupération des offres
    # ------------------------------------------------------------------

    def _fetch_pages(self, session: requests.Session) -> list[Offer]:
        # L'API /v3/search/jobs est une API de recommandations personnalisées :
        # elle retourne les offres correspondant au profil WTTJ de l'utilisateur.
        # Les paramètres de filtrage (query, location, contract_type) renvoient 422 —
        # seuls page, per_page et version sont acceptés.
        # Pour que les résultats soient pertinents, le profil WTTJ doit être configuré
        # (poste souhaité, localisation, type de contrat).
        offers: list[Offer] = []
        for page_num in range(1, _MAX_PAGES + 1):
            resp = session.get(
                _SEARCH_API,
                params={"page": page_num, "per_page": _PER_PAGE, "version": "v1"},
                timeout=15,
            )
            resp.raise_for_status()

            try:
                data = resp.json()
            except Exception as exc:
                raise ValueError(
                    f"WTTJ : réponse non-JSON (status {resp.status_code}, "
                    f"content-type={resp.headers.get('content-type', '?')}). "
                    f"Body : {resp.text[:300]!r}"
                ) from exc

            items = data.get("data") or []
            if not items:
                break

            for item in items:
                offer = self._to_offer(item)
                if offer:
                    offers.append(offer)

            meta = data.get("metadata", {})
            total = meta.get("total", 0)
            if page_num * _PER_PAGE >= total:
                break

        return offers

    def _to_offer(self, item: dict) -> Optional[Offer]:
        try:
            title = item.get("name", "")
            if not title:
                return None

            org = item.get("organization", {})
            company = org.get("name") or "Entreprise inconnue"
            org_slug = org.get("slug", "")

            office = item.get("office", {})
            location = office.get("city") or SEARCH["location_label"]

            description = item.get("description") or item.get("company_summary") or ""

            job_slug = item.get("slug", "")
            url = (
                _JOB_URL_TPL.format(org_slug=org_slug, job_slug=job_slug)
                if org_slug and job_slug
                else ""
            )

            contract_type = item.get("contract_type", "alternance")
            posted_at = parse_date(item.get("published_at"))

            return Offer(
                id=make_offer_id(title, company, location),
                title=title,
                company=company,
                location=location,
                description=description,
                url=url,
                source=self.name,
                posted_at=posted_at,
                contract_type=str(contract_type),
            )
        except Exception:
            return None
