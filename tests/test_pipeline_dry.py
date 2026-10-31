from pathlib import Path
from unittest.mock import MagicMock

from ingestion.config import Settings
from ingestion.pipeline import IngestionPipeline
from ingestion.storage import LocalIgesStore
from ingestion.teamcenter.mock import MockTeamcenterClient


def test_pipeline_writes_files_and_upserts(tmp_path: Path):
    settings = Settings(
        cad_root=tmp_path / "iges",
        batch_size=10,
        tc_mode="mock",
        voyage_model="voyage-4",
    )
    repo = MagicMock()
    pipeline = IngestionPipeline(
        settings,
        tc=MockTeamcenterClient(),
        store=LocalIgesStore(settings),
        repo=repo,
    )
    stats = pipeline.run(limit=3)
    assert stats.listed == 3
    assert stats.written == 3
    assert stats.failed == 0
    assert repo.upsert_many.called
    stored = repo.upsert_many.call_args[0][0]
    assert all(p.embedding_text for p in stored)
    assert all(not hasattr(p, "embedding") or getattr(p, "embedding", None) is None for p in stored)
    # StoredPart should not carry a client-side vector field
    assert "embedding" not in stored[0].model_dump()
    written = list((tmp_path / "iges").rglob("*.igs"))
    assert len(written) == 3
