import os
from typing import Optional

import requests
from dotenv import load_dotenv

from ..config import SEARCH
from ..pipeline.normalizer import clean_html, make_offer_id, parse_date
from ..storage.models import Offer
from .base import BaseScraper

load_dotenv()

_TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


class FranceTravailScraper(BaseScraper):
    name = "france-travail"

    def __init__(self):
        self.client_id = os.getenv("FT_CLIENT_ID", "")
        self.client_secret = os.getenv("FT_CLIENT_SECRET", "")

    def fetch(self) -> list[Offer]:
        if not self.client_id or not self.client_secret:
            raise EnvironmentError(
                "FT_CLIENT_ID et FT_CLIENT_SECRET absents — copie .env.example en .env "
                "et renseigne tes credentials France Travail (francetravail.io)."
            )
        token = self._get_token()
        return self._fetch_offers(token)

    def _get_token(self) -> str:
        resp = requests.post(
            _TOKEN_URL,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _fetch_offers(self, token: str) -> list[Offer]:
        headers = {"Authorization": f"Bearer {token}"}
        # France Travail accepte jusqu'à 150 résultats par appel (range 0-149)
        params = {
            "motsCles": "développeur alternance",
            "departement": SEARCH["department"],
            "range": "0-149",
        }
        resp = requests.get(_SEARCH_URL, headers=headers, params=params, timeout=15)
        if resp.status_code == 204:
            return []
        if not resp.ok:
            raise RuntimeError(
                f"France Travail API {resp.status_code} : {resp.text[:400]}"
            )
        return [self._to_offer(item) for item in resp.json().get("resultats", [])]

    def _to_offer(self, item: dict) -> Offer:
        title = item.get("intitule", "")
        company = item.get("entreprise", {}).get("nom") or "Entreprise confidentielle"
        location = item.get("lieuTravail", {}).get("libelle") or SEARCH["location_label"]
        description = clean_html(item.get("description", ""))
        url = item.get("origineOffre", {}).get("urlOrigine", "")
        posted_at = parse_date(item.get("dateCreation"))
        salary = item.get("salaire", {}).get("libelle")
        contract_label = item.get("typeContratLibelle", "alternance")

        return Offer(
            id=make_offer_id(title, company, location),
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            source=self.name,
            posted_at=posted_at,
            contract_type=contract_label,
            salary=salary,
        )
