from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from core.config import get_settings
from core.db import create_pool
from core.llm import build_embedder
from ingestion.pipeline import ingest_directory


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest equipment manuals into pgvector")
    parser.add_argument("--dir", type=Path, default=Path("data/manuals"))
    parser.add_argument("--force", action="store_true", help="re-ingest unchanged documents")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    embedder = build_embedder(settings)
    pool = create_pool(settings.database_url, max_size=2)
    try:
        report = asyncio.run(
            ingest_directory(
                pool,
                embedder,
                args.dir,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                force=args.force,
            )
        )
    finally:
        pool.close()
    logging.getLogger("ingestion").info(
        "done with %s: %d documents ingested (%d chunks), %d unchanged",
        embedder.name,
        len(report.ingested),
        report.chunks,
        len(report.skipped),
    )
