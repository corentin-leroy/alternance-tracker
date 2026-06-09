"""Route de récupération des offres.

Réplique la logique de ``cli.cmd_fetch`` (scrapers → déduplication → filtrage →
upsert) mais renvoie un résumé chiffré au lieu d'afficher dans le terminal.

Note : l'appel est volontairement bloquant. Les scrapers utilisent Playwright +
réseau et peuvent prendre plusieurs dizaines de secondes ; le frontend affiche
un spinner pendant ce temps. On pourra passer à une tâche en arrière-plan plus
tard si besoin.
"""

import logging
import os

import requests
from fastapi import APIRouter, Depends

from ...pipeline.deduplicator import deduplicate
from ...pipeline.filter import apply_filter
from ...scrapers.francetravail import FranceTravailScraper
from ...scrapers.hellowork import HelloworkScraper
from ...scrapers.labanealternance import LaBonneAlternanceScraper
from ...scrapers.wttj import WttjScraper
from ...storage.db import Database
from ...storage.models import Offer
from ..deps import get_db
from ..schemas import FetchResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["fetch"])


@router.post("/fetch", response_model=FetchResult)
def fetch_offers(db: Database = Depends(get_db)):
    scrapers = [LaBonneAlternanceScraper(), HelloworkScraper(), WttjScraper()]
    if os.getenv("FT_CLIENT_ID") and os.getenv("FT_CLIENT_SECRET"):
        scrapers.append(FranceTravailScraper())

    all_offers: list[Offer] = []
    for scraper in scrapers:
        try:
            all_offers.extend(scraper.fetch())
        except requests.exceptions.RequestException as e:
            logger.warning("Erreur réseau sur %s : %s", scraper.name, e)
        except (EnvironmentError, ImportError) as e:
            logger.warning("Configuration manquante pour %s : %s", scraper.name, e)
        except Exception as e:  # noqa: BLE001 - on ne veut jamais qu'un scraper casse les autres
            logger.error("Erreur sur %s : %s", scraper.name, e)

    unique = deduplicate(all_offers)
    duplicate_count = len(all_offers) - len(unique)
    filtered = [apply_filter(o) for o in unique]

    new_count = sum(1 for o in filtered if db.upsert_offer(o))
    suspicious_count = sum(1 for o in filtered if o.suspicion_score >= 0.5)

    return FetchResult(
        total_fetched=len(all_offers),
        new_count=new_count,
        known_count=len(filtered) - new_count,
        duplicate_count=duplicate_count,
        suspicious_count=suspicious_count,
    )
