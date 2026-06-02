from datetime import datetime

from alternance_tracker.pipeline.deduplicator import (
    deduplicate,
    find_near_duplicates,
    similarity_score,
)
from alternance_tracker.storage.models import Offer


def _offer(title: str, company: str, offer_id: str = "", location: str = "Grenoble") -> Offer:
    return Offer(
        id=offer_id or title[:8].replace(" ", "_"),
        title=title,
        company=company,
        location=location,
        description="Description de l'offre d'alternance.",
        url="https://example.com",
        source="test",
        posted_at=datetime(2026, 1, 15),
    )


class TestDeduplicate:
    def test_exact_duplicate_removed(self):
        o1 = _offer("Développeur Web", "Acme", offer_id="abc123")
        o2 = _offer("Développeur Web", "Acme", offer_id="abc123")
        assert len(deduplicate([o1, o2])) == 1

    def test_different_ids_kept(self):
        o1 = _offer("Développeur Web", "Acme", offer_id="aaa")
        o2 = _offer("Data Engineer", "Beta", offer_id="bbb")
        assert len(deduplicate([o1, o2])) == 2

    def test_first_occurrence_wins(self):
        o1 = _offer("Développeur Web", "Acme", offer_id="same")
        o2 = _offer("Développeur Backend", "Acme", offer_id="same")
        result = deduplicate([o1, o2])
        assert result[0].title == "Développeur Web"

    def test_empty_list(self):
        assert deduplicate([]) == []


class TestSimilarityScore:
    def test_near_duplicate_high_score(self):
        o1 = _offer("Développeur Web H/F", "Acme SAS")
        o2 = _offer("Développeur Web", "Acme")
        assert similarity_score(o1, o2) >= 0.75

    def test_same_offer_max_score(self):
        o = _offer("Développeur Web en alternance", "TechCorp")
        assert similarity_score(o, o) == 1.0

    def test_different_offers_low_score(self):
        o1 = _offer("Développeur Web", "Acme")
        o2 = _offer("Chef de projet Marketing", "Beta Agency")
        assert similarity_score(o1, o2) < 0.4


class TestFindNearDuplicates:
    def test_finds_near_duplicate(self):
        candidate = _offer("Développeur Web H/F", "Acme SAS", offer_id="x1")
        pool = [
            _offer("Développeur Web", "Acme", offer_id="x2"),
            _offer("Data Scientist", "Other Corp", offer_id="x3"),
        ]
        result = find_near_duplicates(candidate, pool, threshold=0.70)
        assert len(result) == 1
        assert result[0].id == "x2"

    def test_no_false_positive(self):
        candidate = _offer("Développeur Web", "Acme", offer_id="x1")
        pool = [_offer("Commercial terrain B2B", "Sales Inc", offer_id="x2")]
        result = find_near_duplicates(candidate, pool)
        assert result == []
