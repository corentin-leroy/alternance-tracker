import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Application, Offer, OfferStatus


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS offers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    source TEXT NOT NULL,
                    posted_at TEXT,
                    fetched_at TEXT NOT NULL,
                    status TEXT DEFAULT 'new',
                    suspicion_score REAL DEFAULT 0.0,
                    suspicion_reasons TEXT DEFAULT '[]',
                    contract_type TEXT DEFAULT 'alternance',
                    salary TEXT
                );

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_id TEXT NOT NULL REFERENCES offers(id),
                    applied_at TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    response TEXT,
                    follow_up_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);
                CREATE INDEX IF NOT EXISTS idx_offers_source ON offers(source);
                CREATE INDEX IF NOT EXISTS idx_offers_fetched ON offers(fetched_at);
            """)

    def upsert_offer(self, offer: Offer) -> bool:
        """Insert offer if ID is new. Returns True if actually inserted.
        If the offer already exists with an empty description, updates it."""
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id, description FROM offers WHERE id = ?", (offer.id,)
            ).fetchone()
            if existing:
                if not existing["description"] and offer.description:
                    conn.execute(
                        "UPDATE offers SET description = ? WHERE id = ?",
                        (offer.description, offer.id),
                    )
                return False
            conn.execute(
                """INSERT INTO offers
                   (id, title, company, location, description, url, source,
                    posted_at, fetched_at, status, suspicion_score,
                    suspicion_reasons, contract_type, salary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    offer.id,
                    offer.title,
                    offer.company,
                    offer.location,
                    offer.description,
                    offer.url,
                    offer.source,
                    offer.posted_at.isoformat() if offer.posted_at else None,
                    offer.fetched_at.isoformat(),
                    offer.status.value,
                    offer.suspicion_score,
                    json.dumps(offer.suspicion_reasons, ensure_ascii=False),
                    offer.contract_type,
                    offer.salary,
                ),
            )
            return True

    def get_offers(
        self,
        status: Optional[OfferStatus] = None,
        max_suspicion: Optional[float] = None,
    ) -> list[Offer]:
        query = "SELECT * FROM offers WHERE 1=1"
        params: list = []
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        if max_suspicion is not None:
            query += " AND suspicion_score <= ?"
            params.append(max_suspicion)
        query += " ORDER BY suspicion_score ASC, fetched_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_offer(r) for r in rows]

    def get_offer(self, offer_id: str) -> Optional[Offer]:
        """Retourne une offre par son id, ou None si elle n'existe pas."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM offers WHERE id = ?", (offer_id,)
            ).fetchone()
        return self._row_to_offer(row) if row else None

    def update_status(self, offer_id: str, status: OfferStatus):
        with self._conn() as conn:
            conn.execute(
                "UPDATE offers SET status = ? WHERE id = ?",
                (status.value, offer_id),
            )

    def add_application(self, application: Application):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO applications
                   (offer_id, applied_at, notes, response, follow_up_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    application.offer_id,
                    application.applied_at.isoformat(),
                    application.notes,
                    application.response,
                    application.follow_up_at.isoformat() if application.follow_up_at else None,
                ),
            )
        self.update_status(application.offer_id, OfferStatus.APPLIED)

    def get_applications(self) -> list[Application]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY applied_at DESC"
            ).fetchall()
        return [
            Application(
                id=r["id"],
                offer_id=r["offer_id"],
                applied_at=datetime.fromisoformat(r["applied_at"]),
                notes=r["notes"] or "",
                response=r["response"],
                follow_up_at=datetime.fromisoformat(r["follow_up_at"]) if r["follow_up_at"] else None,
            )
            for r in rows
        ]

    def get_applications_with_offer(self) -> list[dict]:
        """Comme get_applications, mais joint le titre et l'entreprise de l'offre.

        LEFT JOIN : si l'offre liée a disparu, offer_title/offer_company valent
        None plutôt que d'exclure la candidature.
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT a.*, o.title AS offer_title, o.company AS offer_company
                   FROM applications a
                   LEFT JOIN offers o ON o.id = a.offer_id
                   ORDER BY a.applied_at DESC"""
            ).fetchall()
        return [
            {
                "id": r["id"],
                "offer_id": r["offer_id"],
                "applied_at": datetime.fromisoformat(r["applied_at"]),
                "notes": r["notes"] or "",
                "response": r["response"],
                "follow_up_at": datetime.fromisoformat(r["follow_up_at"])
                if r["follow_up_at"]
                else None,
                "offer_title": r["offer_title"],
                "offer_company": r["offer_company"],
            }
            for r in rows
        ]

    def get_stats(self) -> dict:
        with self._conn() as conn:
            counts = conn.execute(
                "SELECT status, COUNT(*) as n FROM offers GROUP BY status"
            ).fetchall()
            total_apps = conn.execute(
                "SELECT COUNT(*) as n FROM applications"
            ).fetchone()["n"]
            sources = conn.execute(
                "SELECT source, COUNT(*) as n FROM offers GROUP BY source"
            ).fetchall()
        return {
            "by_status": {r["status"]: r["n"] for r in counts},
            "by_source": {r["source"]: r["n"] for r in sources},
            "total_applications": total_apps,
        }

    @staticmethod
    def _row_to_offer(row: sqlite3.Row) -> Offer:
        return Offer(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            description=row["description"] or "",
            url=row["url"] or "",
            source=row["source"],
            posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            status=OfferStatus(row["status"]),
            suspicion_score=row["suspicion_score"],
            suspicion_reasons=json.loads(row["suspicion_reasons"] or "[]"),
            contract_type=row["contract_type"] or "alternance",
            salary=row["salary"],
        )
