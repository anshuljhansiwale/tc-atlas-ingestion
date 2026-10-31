"""Build searchable text that Atlas auto-embeds via Voyage (autoEmbed index)."""

from __future__ import annotations


def build_embedding_text(
    *,
    item_id: str,
    revision_id: str,
    name: str,
    description: str,
    metadata: dict,
) -> str:
    """
    Flatten part fields into a single string stored as `embedding_text`.

    MongoDB Atlas Vector Search with type `autoEmbed` (Voyage) generates
    and maintains vectors for this field — the app does not embed client-side.
    """
    parts = [
        f"item_id: {item_id}",
        f"revision: {revision_id}",
        f"name: {name}",
        f"description: {description}",
    ]
    for key in sorted(metadata.keys()):
        if key == "tc_export":
            continue
        value = metadata[key]
        if isinstance(value, (dict, list)):
            continue
        parts.append(f"{key}: {value}")
    return "\n".join(parts)
