import csv
import gzip
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from core.machines import MACHINES, limits_for
from mcp_server.anomaly import evaluate
from simulator.prepare import (
    DUTY_ALARM,
    Recording,
    prepare_cwru,
    prepare_metropt,
    replay_profiles,
    write_profiles,
)
from simulator.replay import (
    CWRU_FILE,
    METROPT_FILE,
    CWRUStream,
    MetroPTStream,
    ReplayDataMissingError,
    ReplaySource,
    load_profiles,
)

START = datetime(2020, 3, 31, 23, 0)


def write_metropt_csv(path: Path, minutes: int = 120, leak_from: int = 60) -> None:
    """Synthetic MetroPT-3 extract: 10 s samples, loaded continuously after `leak_from`."""
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["", "timestamp", "TP3", "Oil_temperature", "Motor_current", "DV_eletric"])
        for i in range(minutes * 6):
            ts = START + timedelta(seconds=10 * i)
            minute = i // 6
            loaded = minute >= leak_from or minute % 10 == 0
            writer.writerow(
                [
                    i,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    9.0 - 0.01 * (minute >= leak_from),
                    60 + minute / 10,
                    5.5 if loaded else 4.0,
                    1 if loaded else 0,
                ]
            )


def cwru_recordings() -> list[Recording]:
    t = np.arange(24_000) / 12_000
    return [
        Recording("normal", 0.05 * np.sin(2 * np.pi * 1000 * t), 12_000),
        Recording("inner race fault 0.021 in", 0.5 * np.sin(2 * np.pi * 1000 * t), 12_000),
    ]


@pytest.fixture
def prepared(tmp_path: Path) -> Path:
    source = tmp_path / "metropt.csv"
    write_metropt_csv(source)
    out = tmp_path / "processed"
    metropt = prepare_metropt(source, out)
    cwru = prepare_cwru(cwru_recordings(), out)
    write_profiles(out, replay_profiles(metropt, cwru), metropt, cwru)
    return out


def test_prepare_metropt_writes_duty_and_limits(tmp_path: Path) -> None:
    source = tmp_path / "metropt.csv"
    write_metropt_csv(source)
    summary = prepare_metropt(source, tmp_path)
    assert summary.rows == 720
    with gzip.open(tmp_path / METROPT_FILE, "rt") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[-1]["load_duty_pct"]) == 100.0
    assert float(rows[300]["load_duty_pct"]) < 20  # loaded one minute in ten
    assert summary.oil_p99 > summary.oil_p999 - 1  # percentiles of the healthy part only


def test_prepare_metropt_rejects_unordered_rows(tmp_path: Path) -> None:
    source = tmp_path / "bad.csv"
    source.write_text(
        ",timestamp,TP3,Oil_temperature,Motor_current,DV_eletric\n"
        "0,2020-03-01 00:00:10,9,60,4,0\n1,2020-03-01 00:00:00,9,60,4,0\n"
    )
    with pytest.raises(ValueError, match="time order"):
        prepare_metropt(source, tmp_path)


def test_prepare_cwru_baseline_limits(prepared: Path) -> None:
    profiles = load_profiles(prepared)
    pump = profiles["P-3"]
    accel = next(lim for lim in pump.limits if lim.metric == "bearing_accel_g")
    baseline = 0.05 / np.sqrt(2)
    assert accel.warning == pytest.approx(2 * baseline, rel=1e-2)
    assert accel.alarm == pytest.approx(4 * baseline, rel=1e-2)
    assert pump.data_source == "CWRU bearing data replay"
    assert profiles["C-1"].rated_current_a == 7.0


def test_profile_limits_replace_type_defaults(prepared: Path) -> None:
    compressor = load_profiles(prepared)["C-1"]
    limits = {lim.metric: lim for lim in limits_for(compressor)}
    assert limits["pressure_bar"].direction == "low"  # TP3 low limit replaces the high one
    assert limits["load_duty_pct"].alarm == DUTY_ALARM
    assert limits["vibration_mm_s"].alarm == 7.1  # simulated channel keeps the manual limit
    assert limits["current_a"].warning == pytest.approx(7.35)
    flags = evaluate(compressor, {"load_duty_pct": [100.0, 100.0, 100.0]})
    assert [(f.metric, f.level) for f in flags] == [("load_duty_pct", "alarm")]


def test_metropt_stream_averages_and_wraps(prepared: Path) -> None:
    stream = MetroPTStream(prepared / METROPT_FILE, START + timedelta(minutes=30), speed=60)
    first = stream.advance(0)
    assert first.ts == START + timedelta(minutes=30)
    later = stream.advance(60)  # one dataset hour later
    assert later.ts == START + timedelta(minutes=90)
    assert later.load_duty_pct == 100.0
    assert stream.advance(60) is later  # no new rows: the last reading is repeated
    stream.advance(10_000)  # past the end: starts over
    assert stream.advance(0).ts >= START


def test_metropt_stream_validation(prepared: Path) -> None:
    with pytest.raises(ValueError):
        MetroPTStream(prepared / METROPT_FILE, START, speed=0)
    with pytest.raises(ReplayDataMissingError):
        MetroPTStream(prepared / METROPT_FILE, START + timedelta(days=30), speed=1)


def test_cwru_stream_cycles_stages(prepared: Path) -> None:
    stream = CWRUStream(prepared / CWRU_FILE, stage_seconds=60)
    assert stream.stage_at(0) == "normal"
    assert stream.stage_at(61) == "inner race fault 0.021 in"
    assert stream.stage_at(125) == "normal"
    assert stream.advance(70).bearing_accel_g > 0.3
    with pytest.raises(ValueError):
        CWRUStream(prepared / CWRU_FILE, stage_seconds=0)


def test_replay_source_merges_real_and_simulated_channels(prepared: Path) -> None:
    source = ReplaySource.load(
        prepared, start=START, speed=60, stage_seconds=60, rng=random.Random(1)
    )
    assert source.machine_ids == {"C-1", "P-3"}
    now = datetime.now(UTC)
    c1 = source.reading("C-1", now, 0)
    assert c1.pressure_bar == 9.0
    assert c1.load_duty_pct is not None
    assert c1.vibration_mm_s > 0  # simulated: MetroPT-3 has no vibration sensor
    p3 = source.reading("P-3", now, 90)
    assert p3.bearing_accel_g is not None and p3.bearing_accel_g > 0.3
    assert p3.temperature_c > 0  # simulated


def test_missing_replay_files_explain_what_to_run(tmp_path: Path) -> None:
    with pytest.raises(ReplayDataMissingError, match="make datasets"):
        ReplaySource.load(tmp_path, start=START, speed=60, stage_seconds=60, rng=random.Random())
    (tmp_path / METROPT_FILE).touch()
    (tmp_path / CWRU_FILE).touch()
    with pytest.raises(ReplayDataMissingError, match="make datasets"):
        load_profiles(tmp_path)


def test_machine_registry_is_unchanged() -> None:
    assert MACHINES["C-1"].data_source == "simulated"
    assert MACHINES["C-1"].limits == ()
