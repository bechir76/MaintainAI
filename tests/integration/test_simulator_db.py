import random
from datetime import UTC, datetime

import pytest
from psycopg_pool import ConnectionPool

from core.machines import MACHINES
from simulator.runner import backfill, tick

pytestmark = pytest.mark.integration


def test_backfill_and_tick_write_readings(clean_db: ConnectionPool) -> None:
    rng = random.Random(0)
    backfill(clean_db, {"P-3": "high_vibration"}, rng, minutes=1, interval=5)
    tick(clean_db, {}, rng, datetime.now(UTC))
    with clean_db.connection() as conn:
        total = conn.execute("SELECT count(*) FROM sensor_readings").fetchone()
        p3 = conn.execute(
            "SELECT max(vibration_mm_s) FROM sensor_readings WHERE machine_id = 'P-3'"
        ).fetchone()
    assert total is not None and total[0] == 13 * len(MACHINES)
    assert p3 is not None and p3[0] > 7.1


def test_seeded_machines(pool: ConnectionPool) -> None:
    with pool.connection() as conn:
        rows = conn.execute("SELECT id FROM machines ORDER BY id").fetchall()
    assert [r[0] for r in rows] == sorted(MACHINES)
