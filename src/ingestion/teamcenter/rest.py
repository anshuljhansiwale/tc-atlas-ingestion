"""Teamcenter REST/SOA-shaped client.

This is a scaffold for a real Teamcenter deployment. Endpoints and payload
shapes vary by TC version and gateway (AWC REST vs custom middleware). Wire
your environment's login, query, and dataset download calls into the TODOs.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.config import Settings
from ingestion.models import PartPayload, PartRef
from ingestion.teamcenter.base import TeamcenterClient

logger = logging.getLogger(__name__)


class RestTeamcenterClient(TeamcenterClient):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.tc_base_url.rstrip("/"),
            timeout=60.0,
            headers={"Accept": "application/json"},
        )
        self._session_token: str | None = None
        self._login()

    def _login(self) -> None:
        """Authenticate against Teamcenter. Replace path/body for your gateway."""
        if not self._settings.tc_username or not self._settings.tc_password:
            raise ValueError("TC_USERNAME and TC_PASSWORD are required when TC_MODE=rest")

        # TODO: map to your TC login endpoint (example placeholder).
        response = self._client.post(
            "/tc/rest/login",
            json={
                "username": self._settings.tc_username,
                "password": self._settings.tc_password,
                "group": self._settings.tc_group,
                "role": self._settings.tc_role,
            },
        )
        response.raise_for_status()
        payload = response.json()
        self._session_token = payload.get("token") or payload.get("sessionId")
        if self._session_token:
            self._client.headers["Authorization"] = f"Bearer {self._session_token}"
        logger.info("Authenticated to Teamcenter at %s", self._settings.tc_base_url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def _get_json(self, path: str, **kwargs: Any) -> Any:
        response = self._client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    def list_parts(self, limit: int | None = None) -> Iterator[PartRef]:
        """
        Query revisions that have an IGES dataset.

        TODO: replace with your saved query / BOM / classification search API.
        Expected response items: item_id, revision_id, object_uid.
        """
        params: dict[str, Any] = {"datasetType": "IGES"}
        if limit is not None:
            params["limit"] = limit

        data = self._get_json("/tc/rest/parts", params=params)
        rows = data if isinstance(data, list) else data.get("items", [])
        for row in rows:
            yield PartRef(
                item_id=row["item_id"],
                revision_id=row["revision_id"],
                object_uid=row.get("object_uid") or row.get("uid"),
            )

    def fetch_part(self, ref: PartRef) -> PartPayload:
        """
        Fetch metadata JSON + IGES file bytes for one revision.

        TODO: map to dataset download + property export for your TC API.
        """
        uid = ref.object_uid or f"{ref.item_id}/{ref.revision_id}"
        meta = self._get_json(f"/tc/rest/parts/{uid}/metadata")
        file_resp = self._client.get(f"/tc/rest/parts/{uid}/datasets/iges")
        file_resp.raise_for_status()

        filename = (
            file_resp.headers.get("content-disposition", "")
            .split("filename=")[-1]
            .strip('"')
            or f"{ref.item_id}_{ref.revision_id}.igs"
        )

        return PartPayload(
            item_id=ref.item_id,
            revision_id=ref.revision_id,
            object_uid=ref.object_uid,
            name=meta.get("name", ""),
            description=meta.get("description", ""),
            metadata=meta if isinstance(meta, dict) else {"raw": meta},
            iges_bytes=file_resp.content,
            iges_filename=filename,
            source_checksum=meta.get("checksum"),
        )

    def close(self) -> None:
        self._client.close()
