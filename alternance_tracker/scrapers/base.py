from abc import ABC, abstractmethod

from ..storage.models import Offer


class BaseScraper(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self) -> list[Offer]:
        """Fetch raw data and return normalized Offer objects."""
        ...
