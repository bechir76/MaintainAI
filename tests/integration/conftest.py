from __future__ import annotations

import asyncio
import random
from collections.abc import Iterator
from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool
from pydantic import SecretStr

from core.config import Settings
from core.db import create_pool, seed_machines
from core.llm.fake_embedder import FakeEmbedder
from ingestion.pipeline import ingest_directory
from mcp_server.embedded import serve_in_background
from mcp_server.server import ServerDeps
from simulator.model import parse_faults
from simulator.runner import backfill

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


VIEWER_KEY = "viewer-test-key"
TECH_KEY = "technician-test-key"


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        llm_provider="fake",
        mcp_api_keys=SecretStr(f"{VIEWER_KEY}:viewer,{TECH_KEY}:technician"),
        mcp_viewer_key=SecretStr(VIEWER_KEY),
        mcp_technician_key=SecretStr(TECH_KEY),
    )


@pytest.fixture
def sensor_data(clean_db: ConnectionPool) -> ConnectionPool:
    """Five minutes of readings with P-3 vibrating and M-2 overheating."""
    faults = parse_faults("P-3:high_vibration,M-2:overheating")
    backfill(clean_db, faults, random.Random(7), minutes=5, interval=5)
    return clean_db


@pytest.fixture(scope="session")
def mcp_url(ingested: ConnectionPool, test_settings: Settings) -> Iterator[str]:
    deps = ServerDeps(pool=ingested, embedder=FakeEmbedder(), settings=test_settings)
    with serve_in_background(deps) as url:
        yield url
