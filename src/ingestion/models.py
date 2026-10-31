from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PartRef(BaseModel):
    """Lightweight Teamcenter item/revision reference."""

    item_id: str
    revision_id: str
    object_uid: str | None = None


class PartPayload(BaseModel):
    """IGES bytes + JSON metadata pulled from Teamcenter for one revision."""

    item_id: str
    revision_id: str
    object_uid: str | None = None
    name: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    iges_bytes: bytes
    iges_filename: str
    source_checksum: str | None = None


class StoredPart(BaseModel):
    """Document shape written to MongoDB Atlas.

    `embedding_text` is indexed with Atlas Vector Search `autoEmbed` (Voyage).
    Atlas generates/stores vectors — do not write an `embedding` array here.
    """

    item_id: str
    revision_id: str
    object_uid: str | None = None
    name: str = ""
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    iges_path: str
    iges_filename: str
    content_checksum: str
    embedding_text: str
    embedding_provider: str = "atlas-voyage-autoembed"
    voyage_model: str = "voyage-4"
    ingested_at: datetime = Field(default_factory=utc_now)
    storage_scheme: str = "file"

    @property
    def document_key(self) -> dict[str, str]:
        return {"item_id": self.item_id, "revision_id": self.revision_id}
