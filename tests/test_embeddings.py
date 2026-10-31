from ingestion.embeddings import build_embedding_text


def test_build_embedding_text_includes_core_fields():
    text = build_embedding_text(
        item_id="PN-1",
        revision_id="A",
        name="Bracket",
        description="Mount",
        metadata={"material": "Al", "tc_export": {"x": 1}},
    )
    assert "PN-1" in text
    assert "material: Al" in text
    assert "tc_export" not in text
