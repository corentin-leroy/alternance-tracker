from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OfferStatus(str, Enum):
    NEW = "new"
    SEEN = "seen"
    APPLIED = "applied"
    SKIPPED = "skipped"
    REJECTED = "rejected"


@dataclass
class Offer:
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_at: Optional[datetime]
    fetched_at: datetime = field(default_factory=datetime.now)
    status: OfferStatus = OfferStatus.NEW
    suspicion_score: float = 0.0
    suspicion_reasons: list[str] = field(default_factory=list)
    contract_type: str = "alternance"
    salary: Optional[str] = None


@dataclass
class Application:
    offer_id: str
    applied_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    response: Optional[str] = None  # None / "positive" / "negative" / "ghosted"
    follow_up_at: Optional[datetime] = None
    id: Optional[int] = None
