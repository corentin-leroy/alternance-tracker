"""Tests de l'API FastAPI.

On n'utilise jamais la vraie base : on en crée une temporaire et on l'injecte à
la place de celle de production via ``app.dependency_overrides``. C'est le
mécanisme prévu par FastAPI pour les tests.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from alternance_tracker.api.deps import get_db
from alternance_tracker.api.main import app
from alternance_tracker.storage.db import Database
from alternance_tracker.storage.models import Offer


def _make_offer(offer_id="off1", **overrides) -> Offer:
    data = dict(
        id=offer_id,
        title="Développeur web en alternance",
        company="ACME",
        location="Grenoble",
        description="Une vraie offre détaillée " * 10,
        url="https://example.com/offre",
        source="test",
        posted_at=None,
        fetched_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    data.update(overrides)
    return Offer(**data)


@pytest.fixture
def client(tmp_path):
    """Client de test branché sur une base SQLite temporaire avec une offre."""
    db = Database(tmp_path / "test.db")
    db.upsert_offer(_make_offer())

    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_offers_returns_seeded_offer(client):
    resp = client.get("/api/offers", params={"status": "new"})
    assert resp.status_code == 200
    offers = resp.json()
    assert len(offers) == 1
    assert offers[0]["id"] == "off1"


def test_update_status_ok(client):
    resp = client.patch("/api/offers/off1/status", json={"status": "seen"})
    assert resp.status_code == 200
    # L'offre n'est plus dans la liste "new".
    assert client.get("/api/offers", params={"status": "new"}).json() == []
    assert len(client.get("/api/offers", params={"status": "seen"}).json()) == 1


def test_update_status_unknown_offer_returns_404(client):
    resp = client.patch("/api/offers/does-not-exist/status", json={"status": "seen"})
    assert resp.status_code == 404


def test_update_status_invalid_value_returns_422(client):
    # "applied" n'est pas accepté par ce endpoint (réservé à /apply).
    resp = client.patch("/api/offers/off1/status", json={"status": "applied"})
    assert resp.status_code == 422


def test_apply_ok_records_application_and_sets_status(client):
    resp = client.post("/api/offers/off1/apply", json={"notes": "motivé"})
    assert resp.status_code == 201

    apps = client.get("/api/applications").json()
    assert len(apps) == 1
    assert apps[0]["notes"] == "motivé"
    # La jointure ramène bien le titre de l'offre.
    assert apps[0]["offer_title"] == "Développeur web en alternance"

    stats = client.get("/api/stats").json()
    assert stats["total_applications"] == 1
    assert stats["by_status"].get("applied") == 1


def test_apply_unknown_offer_returns_404(client):
    resp = client.post("/api/offers/nope/apply", json={"notes": ""})
    assert resp.status_code == 404
