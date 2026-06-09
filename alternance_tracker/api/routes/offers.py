"""Routes liées aux offres : lister, changer le statut, postuler.

Réutilise directement les méthodes de la classe ``Database`` — la même couche
métier que la CLI.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from ...storage.db import Database
from ...storage.models import Application, OfferStatus
from ..deps import get_db
from ..schemas import ApplyRequest, OfferOut, StatusUpdate

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=list[OfferOut])
def list_offers(
    status: Optional[OfferStatus] = None,
    include_suspicious: bool = False,
    db: Database = Depends(get_db),
):
    """Liste les offres, triées par score de suspicion puis date.

    Par défaut on masque les pièges évidents (score > 0.9), comme la commande
    CLI ``review``. Passer ``include_suspicious=true`` pour tout voir.
    """
    max_suspicion = None if include_suspicious else 0.9
    return db.get_offers(status=status, max_suspicion=max_suspicion)


@router.patch("/{offer_id}/status", response_model=StatusUpdate)
def update_offer_status(
    offer_id: str,
    body: StatusUpdate,
    db: Database = Depends(get_db),
):
    """Change le statut d'une offre (ex: la marquer ``seen`` ou ``skipped``)."""
    db.update_status(offer_id, body.status)
    return body


@router.post("/{offer_id}/apply", status_code=201)
def apply_to_offer(
    offer_id: str,
    body: ApplyRequest,
    db: Database = Depends(get_db),
):
    """Enregistre une candidature et passe l'offre au statut ``applied``."""
    db.add_application(Application(offer_id=offer_id, notes=body.notes))
    return {"offer_id": offer_id, "status": OfferStatus.APPLIED.value}
