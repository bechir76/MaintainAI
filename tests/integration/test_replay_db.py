import random
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from psycopg_pool import ConnectionPool

from core.db import seed_machines
from core.llm.fake_embedder import FakeEmbedder
from core.mcp_client import connect, result_payload
from core.retrieval import search
from ingestion.pipeline import ingest_directory
from simulator.prepare import prepare_cwru, prepare_metropt, replay_profiles, write_profiles
from simulator.replay import ReplaySource
from simulator.runner import tick
from tests.integration.conftest import MANUALS, VIEWER_KEY
from tests.unit.test_replay import START, cwru_recordings, write_metropt_csv

pytestmark = pytest.mark.integration


async def test_replayed_machines_through_mcp(
    mcp_url: str, clean_db: ConnectionPool, tmp_path: Path
) -> None:
    source = tmp_path / "metropt.csv"
    write_metropt_csv(source)
    out = tmp_path / "processed"
    metropt, cwru = prepare_metropt(source, out), prepare_cwru(cwru_recordings(), out)
    write_profiles(out, replay_profiles(metropt, cwru), metropt, cwru)
    replay = ReplaySource.load(
        out, start=START + timedelta(minutes=60), speed=60, stage_seconds=60, rng=random.Random(0)
    )
    seed_machines(clean_db, replay.profiles)
    try:
        now = datetime.now(UTC)
        for i in range(4):  # inside the synthetic air leak, P-3 on its faulty stage
            tick(clean_db, {}, random.Random(i), now - timedelta(seconds=5 * (4 - i)), replay, 70)

        async with connect(mcp_url, VIEWER_KEY) as client:
            c1 = result_payload(
                await client.call_tool("get_sensor_readings", {"machine_id": "C-1"})
            )
            p3 = result_payload(
                await client.call_tool("get_sensor_readings", {"machine_id": "P-3"})
            )

        assert c1["machine"]["data_source"].startswith("MetroPT-3")
        assert c1["status"] == "alarm"
        assert ("load_duty_pct", "alarm") in {(f["metric"], f["level"]) for f in c1["flags"]}
        assert c1["recent"][-1]["load_duty_pct"] == 100.0
        assert p3["machine"]["data_source"] == "CWRU bearing data replay"
        assert p3["flags"][0]["metric"] == "bearing_accel_g"
        assert p3["flags"][0]["source"].startswith("CWRU normal recording baseline")
    finally:
        seed_machines(clean_db)  # back to the simulated registry for the other tests

    async with connect(mcp_url, VIEWER_KEY) as client:
        reset = result_payload(await client.call_tool("list_machines", {}))
    assert {m["data_source"] for m in reset["machines"]} == {"simulated"}


async def test_source_url_of_downloaded_manuals_reaches_search(
    ingested: ConnectionPool, tmp_path: Path
) -> None:
    pdf = "P-MT-02_pump_maintenance_troubleshooting.pdf"
    shutil.copy(MANUALS / pdf, tmp_path / pdf)
    url = "https://example.com/manuals/pump.pdf"
    (tmp_path / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "documents": [
                    {
                        "file": pdf,
                        "doc_id": "TEST-REAL-PUMP",
                        "title": "Test manufacturer pump manual",
                        "machine_type": "pump",
                        "access_level": "viewer",
                        "source_url": url,
                    }
                ]
            }
        )
    )
    try:
        await ingest_directory(ingested, FakeEmbedder(), tmp_path)
        result = await search(
            ingested, FakeEmbedder(), "test manufacturer pump impeller nut torque", role="viewer"
        )
        hits = [c for c in result.chunks if c.doc_id == "TEST-REAL-PUMP"]
        assert hits
        assert hits[0].source_url == url
    finally:
        with ingested.connection() as conn:
            conn.execute("DELETE FROM documents WHERE doc_id = 'TEST-REAL-PUMP'")
