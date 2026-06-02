from datetime import datetime

from alternance_tracker.pipeline.filter import compute_suspicion
from alternance_tracker.storage.models import Offer


def _offer(
    title: str = "Développeur Web en alternance",
    company: str = "Tech Corp",
    description: str = "",
    url: str = "https://example.com",
) -> Offer:
    return Offer(
        id="test_offer",
        title=title,
        company=company,
        location="Grenoble",
        description=description or (
            "Nous recherchons un développeur web en alternance pour rejoindre notre équipe. "
            "Vous travaillerez sur des projets React et Node.js au sein d'une startup grenobloise. "
            "Profil recherché : bac+2 ou bac+3 en informatique, curieux et motivé."
        ),
        url=url,
        source="test",
        posted_at=datetime(2026, 1, 15),
    )


class TestComputeSuspicion:
    def test_legitimate_offer_low_score(self):
        score, reasons = compute_suspicion(_offer())
        assert score < 0.3
        assert reasons == []

    def test_fee_keyword_raises_score(self):
        score, reasons = compute_suspicion(
            _offer(description="Rejoignez-nous. Frais de scolarité pris en charge par l'entreprise.")
        )
        assert score >= 0.25
        assert any("frais de scolarité" in r for r in reasons)

    def test_multiple_keywords_accumulate(self):
        score, reasons = compute_suspicion(
            _offer(
                description=(
                    "Trouver votre entreprise d'accueil grâce à notre réseau. "
                    "Vous devez être inscrit dans notre école partenaire. "
                    "Financement de votre formation assuré."
                )
            )
        )
        assert score >= 0.5
        assert len(reasons) >= 2

    def test_blacklisted_company_raises_score(self):
        score, reasons = compute_suspicion(
            _offer(company="AMOS Sport", description="Offre d'alternance en développement web. " * 5)
        )
        assert score >= 0.5
        assert any("amos sport" in r for r in reasons)

    def test_very_short_description_adds_score(self):
        score, reasons = compute_suspicion(_offer(description="Alternance dev web."))
        assert score >= 0.1
        assert any("courte" in r for r in reasons)

    def test_missing_url_adds_score(self):
        score, reasons = compute_suspicion(_offer(url=""))
        assert score >= 0.1
        assert any("lien" in r for r in reasons)

    def test_score_capped_at_one(self):
        # Worst case : tout cumule
        score, _ = compute_suspicion(
            _offer(
                company="AMOS Sport",
                url="",
                description="Frais de scolarité. Notre école. Notre formation. Frais pédagogiques.",
            )
        )
        assert score <= 1.0
