"""Dépendances FastAPI partagées.

`get_db` est injecté dans les routes via `Depends(get_db)`. La classe
``Database`` ouvre/ferme une connexion SQLite à chaque méthode (voir
``storage/db.py``), donc on peut réutiliser une seule instance sans souci de
concurrence.
"""

from ..config import DB_PATH
from ..storage.db import Database

_db = Database(DB_PATH)


def get_db() -> Database:
    return _db
