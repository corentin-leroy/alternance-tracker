import os

import requests
from dotenv import load_dotenv

from ..config import SEARCH
from ..pipeline.normalizer import make_offer_id, parse_date
from ..storage.models import Offer
from .base import BaseScraper

load_dotenv()

_SEARCH_URL = "https://api.apprentissage.beta.gouv.fr/job/v1/search"


class LaBonneAlternanceScraper(BaseScraper):
    name = "lba"

    def __init__(self):
        self.api_key = os.getenv("LBA_API_KEY", "")

    def fetch(self) -> list[Offer]:
        if not self.api_key:
            raise EnvironmentError(
                "LBA_API_KEY absent — crée un compte sur https://api.apprentissage.beta.gouv.fr "
                "et ajoute la clé dans ton .env."
            )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "latitude": SEARCH["latitude"],
            "longitude": SEARCH["longitude"],
            "radius": SEARCH["radius_km"],
            "romes": ",".join(SEARCH["rome_codes"]),
        }
        resp = requests.get(_SEARCH_URL, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        offers: list[Offer] = []
        for item in data.get("jobs") or []:
            offer = self._to_offer(item)
            if offer:
                offers.append(offer)

        return offers

    def _to_offer(self, item: dict) -> Offer | None:
        try:
            offer_data = item.get("offer", {})
            title = offer_data.get("title", "")
            if not title:
                return None

            workplace = item.get("workplace", {})
            company = (
                workplace.get("brand")
                or workplace.get("name")
                or workplace.get("legal_name")
                or "Entreprise inconnue"
            )
            location = workplace.get("location", {}).get("address") or SEARCH["location_label"]

            description = offer_data.get("description", "")

            apply = item.get("apply", {})
            url = apply.get("url", "")

            contract = item.get("contract", {})
            contract_types = contract.get("type") or []
            contract_label = " / ".join(contract_types) if contract_types else "alternance"

            publication = offer_data.get("publication", {})
            posted_at = parse_date(publication.get("creation"))

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
            )
        except Exception:
            return None
