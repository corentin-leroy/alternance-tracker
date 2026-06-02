from ..config import SCHOOL_TRAP_COMPANIES, SCHOOL_TRAP_KEYWORDS
from ..pipeline.normalizer import normalize_text
from ..storage.models import Offer


def compute_suspicion(offer: Offer) -> tuple[float, list[str]]:
    """
    Returns (score 0.0–1.0, reasons).
    Score >= 0.5 = probablement un piège école/CFA.
    """
    reasons: list[str] = []
    score = 0.0

    desc_lower = offer.description.lower()
    title_lower = offer.title.lower()
    company_norm = normalize_text(offer.company)

    for kw in SCHOOL_TRAP_KEYWORDS:
        if kw in desc_lower or kw in title_lower:
            reasons.append(f"mot-clé suspect : « {kw} »")
            score += 0.25

    for school in SCHOOL_TRAP_COMPANIES:
        if school in company_norm:
            reasons.append(f"entreprise listée comme école recrutant pour elle-même : « {school} »")
            score += 0.5
            break

    # Description très courte = souvent une annonce appât sans détails réels
    stripped = offer.description.strip()
    if stripped and len(stripped) < 200:
        reasons.append("description très courte (< 200 caractères)")
        score += 0.15

    # Absence d'URL directe = impossible de vérifier la source
    if not offer.url:
        reasons.append("aucun lien vers l'offre originale")
        score += 0.1

    return min(score, 1.0), reasons


def apply_filter(offer: Offer) -> Offer:
    score, reasons = compute_suspicion(offer)
    offer.suspicion_score = score
    offer.suspicion_reasons = reasons
    return offer
