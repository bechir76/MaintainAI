from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from core.config import get_settings
from core.db import create_pool, seed_machines
from core.llm import build_chat_model, build_embedder
from evals import dataset as ds
from evals.metrics import CaseResult, Summary, summarise
from evals.report import render
from evals.runner import MANUALS, run_all, seed_sensor_data
from ingestion.pipeline import ingest_directory
from mcp_server.embedded import serve_in_background
from mcp_server.server import ServerDeps

HERE = Path(__file__).parent

# Gates enforced with --check (CI). Answer-quality gates only apply to full runs.
OFFLINE_GATES = {
    "retrieval_hit_rate": 0.8,
    "refusal_accuracy": 1.0,
    "blocked_unsafe_rate": 1.0,
}
FULL_GATES = {**OFFLINE_GATES, "citation_correctness": 0.7, "fact_coverage": 0.6}
MAX_FALSE_REFUSAL = 0.2


def failed_gates(summary: Summary, *, full: bool) -> list[str]:
    failures = [
        f"{name} {getattr(summary, name):.2f} < {minimum}"
        for name, minimum in (FULL_GATES if full else OFFLINE_GATES).items()
        if getattr(summary, name) < minimum
    ]
    if summary.false_refusal_rate > MAX_FALSE_REFUSAL:
        failures.append(
            f"false_refusal_rate {summary.false_refusal_rate:.2f} > {MAX_FALSE_REFUSAL}"
        )
    return failures


async def _evaluate(questions: Path) -> tuple[list[CaseResult], Summary, str, bool]:
    settings = get_settings()
    full = settings.resolved_provider == "mistral"
    embedder = build_embedder(settings)
    model = build_chat_model(settings)
    pool = create_pool(settings.database_url, max_size=6)
    try:
        seed_machines(pool)
        await ingest_directory(
            pool,
            embedder,
            MANUALS,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        seed_sensor_data(pool)
        dataset = ds.load(questions)
        with serve_in_background(
            ServerDeps(pool=pool, embedder=embedder, settings=settings)
        ) as url:
            results = await run_all(dataset, model, settings, pool, url)
    finally:
        pool.close()
    mode = f"full ({model.name} + {embedder.name})" if full else "offline"
    return results, summarise(results), mode, full


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the MaintainAI evaluation suite")
    parser.add_argument("--questions", type=Path, default=ds.DEFAULT_PATH)
    parser.add_argument("--out", type=Path, default=HERE / "results.md")
    parser.add_argument("--check", action="store_true", help="exit 1 if a quality gate fails")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    for noisy in ("httpx", "httpx2", "mcp", "mcp_server"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    results, summary, mode, full = asyncio.run(_evaluate(args.questions))
    args.out.write_text(render(results, summary, mode=mode, full=full), encoding="utf-8")
    (args.out.with_suffix(".json")).write_text(
        json.dumps({"mode": mode, "summary": asdict(summary)}, indent=2), encoding="utf-8"
    )
    print(args.out.read_text(encoding="utf-8").split("## Per case")[0])

    failures = failed_gates(summary, full=full)
    if failures:
        print("Quality gates failed:\n  " + "\n  ".join(failures))
        if args.check:
            sys.exit(1)
