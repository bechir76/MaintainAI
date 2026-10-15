from __future__ import annotations

import logging
import time
from importlib.resources import files

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from core.machines import MACHINES

log = logging.getLogger(__name__)


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


def create_pool(database_url: str, *, min_size: int = 1, max_size: int = 5) -> ConnectionPool:
    """Open a pool once the database accepts connections and the schema is in place."""
    wait_for_database(database_url)
    apply_schema(database_url)
    pool = ConnectionPool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        configure=_configure,
        open=False,
    )
    pool.open(wait=True, timeout=30)
    return pool


def wait_for_database(database_url: str, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            with psycopg.connect(database_url, connect_timeout=3):
                return
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise
            log.info("waiting for database...")
            time.sleep(1.0)


def apply_schema(database_url: str) -> None:
    sql = files("core").joinpath("schema.sql").read_text(encoding="utf-8")
    with psycopg.connect(database_url, autocommit=True) as conn:
        # Serialise concurrent start-ups (several services apply the schema).
        conn.execute("SELECT pg_advisory_lock(727274)")
        try:
            conn.execute(sql)
        finally:
            conn.execute("SELECT pg_advisory_unlock(727274)")


def seed_machines(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        for m in MACHINES.values():
            conn.execute(
                """
                INSERT INTO machines (id, name, machine_type, model, location, rated_current_a)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, model = EXCLUDED.model,
                    location = EXCLUDED.location, rated_current_a = EXCLUDED.rated_current_a
                """,
                (m.id, m.name, m.type, m.model, m.location, m.rated_current_a),
            )
