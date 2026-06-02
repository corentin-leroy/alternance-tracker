from rapidfuzz import fuzz

from ..config import DEDUP
from ..storage.models import Offer


def similarity_score(a: Offer, b: Offer) -> float:
    """Weighted similarity: 65% titre (token-order-insensitive), 35% entreprise."""
    title_sim = fuzz.token_sort_ratio(a.title.lower(), b.title.lower()) / 100
    company_sim = fuzz.ratio(a.company.lower(), b.company.lower()) / 100
    return title_sim * 0.65 + company_sim * 0.35


def deduplicate(offers: list[Offer]) -> list[Offer]:
    """Remove exact duplicates (same hash ID). Order is preserved, first occurrence wins."""
    seen: set[str] = set()
    unique: list[Offer] = []
    for offer in offers:
        if offer.id not in seen:
            seen.add(offer.id)
            unique.append(offer)
    return unique


def find_near_duplicates(
    candidate: Offer,
    pool: list[Offer],
    threshold: float | None = None,
) -> list[Offer]:
    """Return offers from pool that are fuzzy-duplicates of candidate."""
    threshold = threshold if threshold is not None else DEDUP["fuzzy_threshold"]
    return [o for o in pool if o.id != candidate.id and similarity_score(candidate, o) >= threshold]
