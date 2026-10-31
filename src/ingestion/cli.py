"""CLI entrypoints for ingest and similarity search."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from ingestion.config import get_settings
from ingestion.mongo import PartsRepository
from ingestion.pipeline import IngestionPipeline


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    _configure_logging(settings.log_level)
    pipeline = IngestionPipeline(settings, dry_run=args.dry_run)
    try:
        stats = pipeline.run(limit=args.limit)
    finally:
        pipeline.close()

    print(
        json.dumps(
            {
                "listed": stats.listed,
                "written": stats.written,
                "failed": stats.failed,
                "errors": stats.errors,
            },
            indent=2,
        )
    )
    return 1 if stats.failed else 0


def cmd_search(args: argparse.Namespace) -> int:
    settings = get_settings()
    _configure_logging(settings.log_level)
    repo = PartsRepository(settings)
    try:
        hits = repo.vector_search(args.query, limit=args.limit)
    finally:
        repo.close()

    print(json.dumps(hits, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Teamcenter IGES + metadata → local FS + MongoDB Atlas (Voyage autoEmbed)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("run", help="Run the ingestion pipeline")
    ingest_p.add_argument("--limit", type=int, default=None, help="Max parts to ingest")
    ingest_p.add_argument(
        "--dry-run",
        action="store_true",
        help="Write IGES + embedding_text locally but skip MongoDB upserts",
    )
    ingest_p.set_defaults(func=cmd_ingest)

    search_p = sub.add_parser(
        "search",
        help="Semantic search (Atlas embeds the query with Voyage)",
    )
    search_p.add_argument("query", help="Natural-language search query")
    search_p.add_argument("--limit", type=int, default=5)
    search_p.set_defaults(func=cmd_search)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
