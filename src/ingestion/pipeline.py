"""End-to-end ingest: Teamcenter → local IGES → Atlas (Voyage autoEmbed)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ingestion.config import Settings, get_settings
from ingestion.embeddings import build_embedding_text
from ingestion.models import StoredPart
from ingestion.mongo import PartsRepository
from ingestion.storage import LocalIgesStore
from ingestion.teamcenter import TeamcenterClient, create_teamcenter_client

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    listed: int = 0
    written: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class NullPartsRepository:
    """No-op repository for --dry-run (filesystem only)."""

    def upsert_many(self, parts: list[StoredPart]):  # noqa: ANN201
        logger.info("Dry-run: skipping Mongo upsert of %d parts", len(parts))
        return None

    def close(self) -> None:
        return None


class IngestionPipeline:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        tc: TeamcenterClient | None = None,
        store: LocalIgesStore | None = None,
        repo: PartsRepository | NullPartsRepository | None = None,
        dry_run: bool = False,
    ) -> None:
        self.settings = settings or get_settings()
        self.tc = tc or create_teamcenter_client(self.settings)
        self.store = store or LocalIgesStore(self.settings)
        if repo is not None:
            self.repo = repo
        elif dry_run:
            self.repo = NullPartsRepository()
        else:
            self.repo = PartsRepository(self.settings)

    def run(self, *, limit: int | None = None) -> IngestStats:
        stats = IngestStats()
        batch: list[StoredPart] = []
        batch_size = self.settings.batch_size

        for ref in self.tc.list_parts(limit=limit):
            stats.listed += 1
            try:
                payload = self.tc.fetch_part(ref)
                abs_path, digest = self.store.write(
                    payload.item_id,
                    payload.revision_id,
                    payload.iges_filename,
                    payload.iges_bytes,
                )
                text = build_embedding_text(
                    item_id=payload.item_id,
                    revision_id=payload.revision_id,
                    name=payload.name,
                    description=payload.description,
                    metadata=payload.metadata,
                )
                batch.append(
                    StoredPart(
                        item_id=payload.item_id,
                        revision_id=payload.revision_id,
                        object_uid=payload.object_uid,
                        name=payload.name,
                        description=payload.description,
                        metadata=payload.metadata,
                        iges_path=str(abs_path),
                        iges_filename=payload.iges_filename,
                        content_checksum=digest,
                        embedding_text=text,
                        voyage_model=self.settings.voyage_model,
                    )
                )
                if len(batch) >= batch_size:
                    self.repo.upsert_many(batch)
                    stats.written += len(batch)
                    batch.clear()
            except Exception as exc:  # noqa: BLE001 — continue batch; collect failures
                stats.failed += 1
                msg = f"{ref.item_id}/{ref.revision_id}: {exc}"
                stats.errors.append(msg)
                logger.exception("Failed to ingest %s", msg)

        if batch:
            self.repo.upsert_many(batch)
            stats.written += len(batch)

        logger.info(
            "Ingest complete listed=%s written=%s failed=%s",
            stats.listed,
            stats.written,
            stats.failed,
        )
        return stats

    def close(self) -> None:
        self.tc.close()
        self.repo.close()
