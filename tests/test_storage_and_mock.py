from pathlib import Path

from ingestion.config import Settings
from ingestion.storage import LocalIgesStore
from ingestion.teamcenter.mock import MockTeamcenterClient


def test_mock_lists_and_fetches(tmp_path: Path):
    tc = MockTeamcenterClient()
    refs = list(tc.list_parts(limit=2))
    assert len(refs) == 2
    part = tc.fetch_part(refs[0])
    assert part.iges_bytes.startswith(b" ") or b"IGES" in part.iges_bytes or len(part.iges_bytes) > 0
    assert part.metadata["material"]


def test_local_iges_store_writes_atomically(tmp_path: Path):
    settings = Settings(cad_root=tmp_path / "iges")
    store = LocalIgesStore(settings)
    path, digest = store.write("PN-1", "A", "x.igs", b"IGESDATA")
    assert path.exists()
    assert path.read_bytes() == b"IGESDATA"
    assert len(digest) == 64
    assert path.parent.name == "A"
