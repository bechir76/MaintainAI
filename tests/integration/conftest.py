from __future__ import annotations

from collections.abc import Iterator

import pytest
from psycopg_pool import ConnectionPool

from core.db import create_pool, seed_machines


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
