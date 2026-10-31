from abc import ABC, abstractmethod
from collections.abc import Iterator

from ingestion.models import PartPayload, PartRef


class TeamcenterClient(ABC):
    """Abstraction over Teamcenter extract so mock and REST share one pipeline."""

    @abstractmethod
    def list_parts(self, limit: int | None = None) -> Iterator[PartRef]:
        """Yield part/revision refs that have IGES datasets."""

    @abstractmethod
    def fetch_part(self, ref: PartRef) -> PartPayload:
        """Download IGES bytes and JSON-ish metadata for one revision."""

    def close(self) -> None:
        """Optional cleanup for HTTP sessions / login tokens."""
