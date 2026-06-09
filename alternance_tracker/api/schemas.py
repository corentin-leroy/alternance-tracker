"""Modèles Pydantic pour la frontière HTTP.

Ce sont les objets que FastAPI sérialise en JSON (sortie) ou valide depuis le
corps des requêtes (entrée). Ils reflètent les dataclasses de
``storage/models.py`` mais restent séparés : les dataclasses sont la logique
métier interne, ces schémas sont le contrat de l'API. ``from_attributes=True``
permet de construire un schéma directement depuis une dataclass
(ex: ``OfferOut.model_validate(offer)``).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from ..storage.models import OfferStatus


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_at: Optional[datetime]
    fetched_at: datetime
    status: OfferStatus
    suspicion_score: float
    suspicion_reasons: list[str]
    contract_type: str
    salary: Optional[str]


class StatusUpdate(BaseModel):
    """Corps de PATCH /offers/{id}/status."""

    status: OfferStatus


class ApplyRequest(BaseModel):
    """Corps de POST /offers/{id}/apply."""

    notes: str = ""


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int]
    offer_id: str
    applied_at: datetime
    notes: str
    response: Optional[str]
    follow_up_at: Optional[datetime]


class StatsOut(BaseModel):
    by_status: dict[str, int]
    by_source: dict[str, int]
    total_applications: int


class FetchResult(BaseModel):
    """Résumé renvoyé après POST /fetch (équivaut au récap de `cmd_fetch`)."""

    total_fetched: int
    new_count: int
    known_count: int
    duplicate_count: int
    suspicious_count: int
