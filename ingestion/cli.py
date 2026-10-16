from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from core.config import get_settings
from core.db import create_pool
from core.llm import build_embedder
from ingestion.pipeline import IngestReport, ingest_directory

DEFAULT_DIRS = (Path("data/manuals"), Path("data/manuals_real"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest equipment manuals into pgvector")
    parser.add_argument(
        "--dir",
        type=Path,
        action="append",
        help="folder with a manifest.yaml (repeatable). Default: the sample manuals, plus "
        "data/manuals_real when the manufacturer manuals have been downloaded",
    )
    parser.add_argument("--force", action="store_true", help="re-ingest unchanged documents")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    embedder = build_embedder(settings)
    directories = args.dir or [d for d in DEFAULT_DIRS if (d / "manifest.yaml").exists()]
    pool = create_pool(settings.database_url, max_size=2)
    reports = []
    try:
        for directory in directories:
            reports.append(
                asyncio.run(
                    ingest_directory(
                        pool,
                        embedder,
                        directory,
                        chunk_size=settings.chunk_size,
                        chunk_overlap=settings.chunk_overlap,
                        force=args.force,
                    )
                )
            )
    finally:
        pool.close()
    report = IngestReport(
        ingested=[d for r in reports for d in r.ingested],
        skipped=[d for r in reports for d in r.skipped],
        chunks=sum(r.chunks for r in reports),
    )
    logging.getLogger("ingestion").info(
        "done with %s: %d documents ingested (%d chunks), %d unchanged",
        embedder.name,
        len(report.ingested),
        report.chunks,
        len(report.skipped),
    )
