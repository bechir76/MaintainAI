from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool

from core.db import create_pool, seed_machines
from core.llm.fake_embedder import FakeEmbedder
from ingestion.pipeline import ingest_directory

MANUALS = Path(__file__).resolve().parents[2] / "data" / "manuals"


@pytest.fixture(scope="session")
def pool(database_url: str) -> Iterator[ConnectionPool]:
    pool = create_pool(database_url, max_size=8)
    seed_machines(pool)
    yield pool
    pool.close()


@pytest.fixture
def clean_db(pool: ConnectionPool) -> ConnectionPool:
    with pool.connection() as conn:
        conn.execute("TRUNCATE sensor_readings, tickets, audit_log RESTART IDENTITY")
    return pool


@pytest.fixture(scope="session")
def ingested(pool: ConnectionPool) -> ConnectionPool:
    """All sample manuals ingested once with the offline embedder."""
    asyncio.run(ingest_directory(pool, FakeEmbedder(), MANUALS))
    return pool
