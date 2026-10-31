"""MongoDB Atlas persistence; Voyage embeddings via Atlas autoEmbed."""

from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.results import BulkWriteResult

from ingestion.config import Settings
from ingestion.models import StoredPart

logger = logging.getLogger(__name__)


class PartsRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = MongoClient(settings.mongodb_uri)
        self._db = self._client[settings.mongodb_db]
        self._collection: Collection = self._db[settings.mongodb_collection]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self._collection.create_index(
            [("item_id", ASCENDING), ("revision_id", ASCENDING)],
            unique=True,
            name="uniq_item_revision",
        )
        self._collection.create_index([("content_checksum", ASCENDING)], name="idx_checksum")

    def upsert_many(self, parts: list[StoredPart]) -> BulkWriteResult | None:
        if not parts:
            return None
        ops = [
            UpdateOne(
                part.document_key,
                {"$set": part.model_dump(mode="json")},
                upsert=True,
            )
            for part in parts
        ]
        result = self._collection.bulk_write(ops, ordered=False)
        logger.info(
            "Upserted parts: matched=%s modified=%s upserted=%s",
            result.matched_count,
            result.modified_count,
            result.upserted_count,
        )
        return result

    def vector_search(
        self,
        query: str,
        *,
        limit: int = 5,
        index_name: str | None = None,
        model: str | None = None,
        num_candidates: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search using Atlas Automated Embedding (Voyage).

        Pass natural-language `query` — Atlas embeds it with the same Voyage
        model as the `autoEmbed` index on `embedding_text`. Do not pass
        `queryVector`.
        """
        candidates = num_candidates or max(limit * 20, 100)
        stage: dict[str, Any] = {
            "index": index_name or self._settings.vector_index_name,
            "path": "embedding_text",
            "query": query,
            "numCandidates": candidates,
            "limit": limit,
        }
        # Optional override; omit to use the model from the index definition
        resolved_model = model or self._settings.voyage_model
        if resolved_model:
            stage["model"] = resolved_model

        pipeline = [
            {"$vectorSearch": stage},
            {
                "$project": {
                    "_id": 0,
                    "item_id": 1,
                    "revision_id": 1,
                    "name": 1,
                    "description": 1,
                    "iges_path": 1,
                    "embedding_text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        return list(self._collection.aggregate(pipeline))

    def close(self) -> None:
        self._client.close()
