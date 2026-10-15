from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A real Postgres 16 + pgvector instance.

    Uses TEST_DATABASE_URL when set (CI service container), otherwise starts one
    with Testcontainers.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver=None) as pg:
        yield pg.get_connection_url()
