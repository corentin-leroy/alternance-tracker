import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Optional


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace — used for ID generation."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def make_offer_id(title: str, company: str, location: str) -> str:
    key = f"{normalize_text(title)}|{normalize_text(company)}|{normalize_text(location)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def clean_html(text: str) -> str:
    """Strip HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO date strings tolerantly across Python 3.10/3.11 differences."""
    if not date_str:
        return None
    # Try full ISO format first (Python 3.11 handles TZ offsets natively)
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    # Fallback: strip timezone and milliseconds, parse date only
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except ValueError:
        return None
