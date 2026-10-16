"""Turn the raw public datasets into compact replay files and data-driven alarm limits."""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from core.machines import MACHINES, Limit, Machine
from simulator.replay import CWRU_FILE, METROPT_FILE, PROFILES_FILE
from simulator.signals import RollingDuty, band_rms_g, percentile, velocity_rms_mm_s, windows

# Air-leak failures reported by the operator (UCI MetroPT-3 dataset page)
METROPT_FAILURES: tuple[tuple[str, str], ...] = (
    ("2020-04-18 00:00:00", "2020-04-18 23:59:00"),
    ("2020-05-29 23:30:00", "2020-05-30 06:00:00"),
    ("2020-06-05 10:00:00", "2020-06-07 14:30:00"),
    ("2020-07-15 14:30:00", "2020-07-15 19:00:00"),
)
HEALTHY_UNTIL = datetime(2020, 4, 1)  # Feb-Mar 2020: no reported failures
DUTY_WARNING, DUTY_ALARM = 80.0, 95.0
DUTY_WINDOW_SECONDS = 1800.0
METROPT_RATED_CURRENT_A = 7.0  # dataset description: about 7 A when loaded
CWRU_WARNING_FACTOR, CWRU_ALARM_FACTOR = 2.0, 4.0


@dataclass
class MetroPTSummary:
    rows: int
    first: str
    last: str
    oil_p99: float
    oil_p999: float
    tp3_p1: float
    tp3_p01: float
    duty_flag_rate_in_failures: list[float] = field(default_factory=list)
    duty_flag_rate_outside: float = 0.0


def _in_failure(ts: datetime, windows_: Sequence[tuple[datetime, datetime]]) -> int | None:
    for i, (start, end) in enumerate(windows_):
        if start <= ts <= end:
            return i
    return None


def prepare_metropt(source: Path, out_dir: Path) -> MetroPTSummary:
    """Write metropt3_c1.csv.gz (pressure, oil temperature, current, loaded duty)."""
    failures = [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a, b in METROPT_FAILURES]
    healthy_oil: list[float] = []
    healthy_tp3: list[float] = []
    flagged_in = [0] * len(failures)
    total_in = [0] * len(failures)
    flagged_out = total_out = rows = 0
    first = last = ""

    duty_tracker = RollingDuty(DUTY_WINDOW_SECONDS)
    previous: datetime | None = None
    out_dir.mkdir(parents=True, exist_ok=True)
    # The source CSV is in time order, so it is streamed rather than loaded.
    with (
        source.open(newline="") as f_in,
        gzip.open(out_dir / METROPT_FILE, "wt", newline="") as f_out,
    ):
        writer = csv.writer(f_out)
        writer.writerow(["ts", "tp3", "oil_temperature", "motor_current", "load_duty_pct"])
        for r in csv.DictReader(f_in):
            ts = datetime.fromisoformat(r["timestamp"])
            if previous is not None and ts < previous:
                raise ValueError(f"MetroPT-3 rows are not in time order at {ts}")
            previous = ts
            tp3, oil = float(r["TP3"]), float(r["Oil_temperature"])
            duty = duty_tracker.update(ts, float(r["DV_eletric"]) > 0.5)
            writer.writerow([ts.isoformat(), tp3, oil, float(r["Motor_current"]), round(duty, 1)])
            rows += 1
            first = first or ts.isoformat()
            last = ts.isoformat()
            if ts < HEALTHY_UNTIL:
                healthy_oil.append(oil)
                healthy_tp3.append(tp3)
            failure = _in_failure(ts, failures)
            if failure is None:
                total_out += 1
                flagged_out += duty >= DUTY_WARNING
            else:
                total_in[failure] += 1
                flagged_in[failure] += duty >= DUTY_WARNING

    return MetroPTSummary(
        rows=rows,
        first=first,
        last=last,
        oil_p99=round(percentile(healthy_oil, 99), 1),
        oil_p999=round(percentile(healthy_oil, 99.9), 1),
        tp3_p1=round(percentile(healthy_tp3, 1), 2),
        tp3_p01=round(percentile(healthy_tp3, 0.1), 2),
        duty_flag_rate_in_failures=[
            round(f / t, 3) if t else 0.0 for f, t in zip(flagged_in, total_in, strict=True)
        ],
        duty_flag_rate_outside=round(flagged_out / total_out, 4) if total_out else 0.0,
    )


@dataclass(frozen=True)
class Recording:
    stage: str  # e.g. "normal", "inner race 0.007 in"
    acceleration_g: np.ndarray
    fs: float


@dataclass
class CWRUSummary:
    windows: dict[str, int]
    baseline_accel_g: float
    median_accel_g: dict[str, float]
    median_velocity_mm_s: dict[str, float]


def prepare_cwru(recordings: Iterable[Recording], out_dir: Path) -> CWRUSummary:
    """Write cwru_p3.csv: one row per 1 s window (50% overlap) of each recording."""
    out_dir.mkdir(parents=True, exist_ok=True)
    per_stage: dict[str, list[tuple[float, float]]] = {}
    with (out_dir / CWRU_FILE).open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stage", "window", "velocity_mm_s", "bearing_accel_g"])
        for rec in recordings:
            values = per_stage.setdefault(rec.stage, [])
            for i, window in enumerate(windows(rec.acceleration_g, rec.fs)):
                velocity = velocity_rms_mm_s(window, rec.fs)
                accel = band_rms_g(window, rec.fs)
                values.append((velocity, accel))
                writer.writerow([rec.stage, i, round(velocity, 4), round(accel, 5)])
    if not per_stage:
        raise ValueError("no CWRU recordings")
    baseline_stage = next(iter(per_stage))
    medians = {s: float(np.median([a for _, a in v])) for s, v in per_stage.items()}
    return CWRUSummary(
        windows={s: len(v) for s, v in per_stage.items()},
        baseline_accel_g=round(medians[baseline_stage], 4),
        median_accel_g={s: round(m, 4) for s, m in medians.items()},
        median_velocity_mm_s={
            s: round(float(np.median([v for v, _ in vals])), 3) for s, vals in per_stage.items()
        },
    )


def replay_profiles(metropt: MetroPTSummary, cwru: CWRUSummary) -> list[Machine]:
    c1, p3 = MACHINES["C-1"], MACHINES["P-3"]
    healthy = "MetroPT-3 healthy period Feb-Mar 2020"
    compressor = Machine(
        id=c1.id,
        name=c1.name,
        type=c1.type,
        model="Metro train APU compressor (MetroPT-3)",
        location=c1.location,
        rated_current_a=METROPT_RATED_CURRENT_A,
        data_source="MetroPT-3 replay (UCI, CC BY 4.0)",
        limits=(
            Limit(
                "temperature_c",
                "Oil temperature (°C)",
                metropt.oil_p99,
                metropt.oil_p999,
                source=f"{healthy}: 99th / 99.9th percentile",
            ),
            Limit(
                "pressure_bar",
                "Pneumatic panel pressure TP3 (bar)",
                metropt.tp3_p1,
                metropt.tp3_p01,
                direction="low",
                source=f"{healthy}: 1st / 0.1th percentile",
            ),
            Limit(
                "load_duty_pct",
                "Compressor loaded duty, last 30 min (%)",
                DUTY_WARNING,
                DUTY_ALARM,
                source="MetroPT-3 analysis: air leaks keep the compressor loaded",
            ),
        ),
    )
    baseline = cwru.baseline_accel_g
    pump = Machine(
        id=p3.id,
        name=p3.name,
        type=p3.type,
        model=f"{p3.model} (bearing signal: CWRU test rig, drive end)",
        location=p3.location,
        rated_current_a=p3.rated_current_a,
        data_source="CWRU bearing data replay",
        limits=(
            Limit(
                "bearing_accel_g",
                "Bearing acceleration 500-5000 Hz (g RMS)",
                round(baseline * CWRU_WARNING_FACTOR, 4),
                round(baseline * CWRU_ALARM_FACTOR, 4),
                source=f"CWRU normal recording baseline {baseline} g: 2x / 4x",
            ),
        ),
    )
    return [compressor, pump]


def write_profiles(
    out_dir: Path, machines: list[Machine], metropt: MetroPTSummary, cwru: CWRUSummary
) -> Path:
    entries = []
    for m in machines:
        entry = {k: v for k, v in asdict(m).items() if k != "limits"}
        entry["limits"] = [lim.to_dict() for lim in m.limits]
        entries.append(entry)
    path = out_dir / PROFILES_FILE
    path.write_text(
        json.dumps(
            {"machines": entries, "metropt3": asdict(metropt), "cwru": asdict(cwru)}, indent=2
        ),
        encoding="utf-8",
    )
    return path
