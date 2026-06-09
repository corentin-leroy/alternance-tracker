"""Routes statistiques et historique des candidatures."""

from fastapi import APIRouter, Depends

from ...storage.db import Database
from ..deps import get_db
from ..schemas import ApplicationOut, StatsOut

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Database = Depends(get_db)):
    """Compteurs par statut, par source, et total des candidatures."""
    return db.get_stats()


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Database = Depends(get_db)):
    """Historique des candidatures, plus récentes d'abord."""
    return db.get_applications()
