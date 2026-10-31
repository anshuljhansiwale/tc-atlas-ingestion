"""Offline Teamcenter stand-in for local development without a live server."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator

from ingestion.models import PartPayload, PartRef
from ingestion.teamcenter.base import TeamcenterClient

_SAMPLE_PARTS: list[dict] = [
    {
        "item_id": "PN-10001",
        "revision_id": "A",
        "object_uid": "uid-10001-A",
        "name": "Bracket Mount",
        "description": "Aluminum mounting bracket for chassis assembly",
        "metadata": {
            "material": "Aluminum 6061",
            "classification": "Structural / Bracket",
            "mass_kg": 0.42,
            "bom_notes": "Used on front subframe",
            "owner": "mech-design",
        },
    },
    {
        "item_id": "PN-10002",
        "revision_id": "B",
        "object_uid": "uid-10002-B",
        "name": "Cooling Duct",
        "description": "Plastic air duct for battery pack cooling",
        "metadata": {
            "material": "ABS",
            "classification": "Thermal / Duct",
            "mass_kg": 0.18,
            "bom_notes": "Pairs with fan housing PN-10010",
            "owner": "thermal",
        },
    },
    {
        "item_id": "PN-10003",
        "revision_id": "A",
        "object_uid": "uid-10003-A",
        "name": "Shaft Collar",
        "description": "Steel collar for drive shaft retention",
        "metadata": {
            "material": "Steel 1045",
            "classification": "Powertrain / Fastener",
            "mass_kg": 0.09,
            "bom_notes": "Torque to 12 Nm",
            "owner": "powertrain",
        },
    },
]


def _minimal_iges(part_name: str) -> bytes:
    """Produce a tiny valid-looking IGES ASCII stub for demos."""
    lines = [
        f"                                                                         S      1",
        f"1H,,1H;,4HIGES,40H{part_name[:40]:<40},32Hmock-teamcenter,                    G      1",
        f"116,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.,1.;                                      D      1",
        f"116,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0;                                   D      2",
        f"116,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.,1.;                                      P      1",
        f"S0000001G0000001D0000002P0000001                                           T      1",
    ]
    body = "\n".join(lines) + "\n"
    return body.encode("ascii", errors="replace")


class MockTeamcenterClient(TeamcenterClient):
    def list_parts(self, limit: int | None = None) -> Iterator[PartRef]:
        items = _SAMPLE_PARTS if limit is None else _SAMPLE_PARTS[:limit]
        for row in items:
            yield PartRef(
                item_id=row["item_id"],
                revision_id=row["revision_id"],
                object_uid=row["object_uid"],
            )

    def fetch_part(self, ref: PartRef) -> PartPayload:
        row = next(
            (
                p
                for p in _SAMPLE_PARTS
                if p["item_id"] == ref.item_id and p["revision_id"] == ref.revision_id
            ),
            None,
        )
        if row is None:
            raise KeyError(f"Unknown mock part {ref.item_id}/{ref.revision_id}")

        iges_bytes = _minimal_iges(row["name"])
        checksum = hashlib.sha256(iges_bytes).hexdigest()
        # Include a JSON snapshot as Teamcenter-style metadata export
        metadata = {
            **row["metadata"],
            "tc_export": json.loads(
                json.dumps(
                    {
                        "item_id": row["item_id"],
                        "revision_id": row["revision_id"],
                        "name": row["name"],
                        "description": row["description"],
                        **row["metadata"],
                    }
                )
            ),
        }
        return PartPayload(
            item_id=row["item_id"],
            revision_id=row["revision_id"],
            object_uid=row["object_uid"],
            name=row["name"],
            description=row["description"],
            metadata=metadata,
            iges_bytes=iges_bytes,
            iges_filename=f"{row['item_id']}_{row['revision_id']}.igs",
            source_checksum=checksum,
        )
