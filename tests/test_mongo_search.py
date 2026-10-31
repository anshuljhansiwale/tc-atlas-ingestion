from unittest.mock import MagicMock, patch

from ingestion.config import Settings
from ingestion.mongo import PartsRepository


def test_vector_search_uses_query_text_not_query_vector():
    settings = Settings(
        mongodb_uri="mongodb://localhost:27017",
        voyage_model="voyage-4",
        vector_index_name="parts_vector_index",
    )
    with patch("ingestion.mongo.MongoClient") as client_cls:
        collection = MagicMock()
        collection.aggregate.return_value = iter([])
        client_cls.return_value.__getitem__.return_value.__getitem__.return_value = collection
        # create_index is called on init
        repo = PartsRepository(settings)
        repo.vector_search("aluminum bracket", limit=3)

        pipeline = collection.aggregate.call_args[0][0]
        stage = pipeline[0]["$vectorSearch"]
        assert stage["query"] == "aluminum bracket"
        assert "queryVector" not in stage
        assert stage["path"] == "embedding_text"
        assert stage["model"] == "voyage-4"
        assert stage["index"] == "parts_vector_index"
        assert stage["limit"] == 3
