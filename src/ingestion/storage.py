"""Persist IGES binaries on a local (or NFS-mounted) filesystem."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from ingestion.config import Settings

logger = logging.getLogger(__name__)


class LocalIgesStore:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.cad_root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def checksum(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def relative_path(self, item_id: str, revision_id: str, filename: str) -> Path:
        safe_item = item_id.replace("/", "_")
        safe_rev = revision_id.replace("/", "_")
        # Keep original extension when present
        suffix = Path(filename).suffix or ".igs"
        return Path(safe_item) / safe_rev / f"{safe_item}_{safe_rev}{suffix}"

    def write(
        self,
        item_id: str,
        revision_id: str,
        filename: str,
        data: bytes,
    ) -> tuple[Path, str]:
        """
        Atomically write IGES bytes under CAD_ROOT.

        Returns (absolute path, sha256 hex digest).
        """
        rel = self.relative_path(item_id, revision_id, filename)
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        digest = self.checksum(data)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)

        logger.info("Wrote IGES %s (%d bytes)", dest, len(data))
        return dest.resolve(), digest
