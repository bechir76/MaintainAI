"""Download the public sensor datasets used by the replay mode and prepare them.

    uv run --group data python scripts/download_datasets.py

* MetroPT-3 (UCI Machine Learning Repository, CC BY 4.0): air compressor of a metro
  train, Feb-Aug 2020, with four reported air-leak failures. Replayed as compressor C-1.
* CWRU Bearing Data Center: drive-end accelerometer of a motor test rig with a healthy
  bearing and inner-race faults of 0.007, 0.014 and 0.021 in. Replayed as pump P-3.

Raw files go to data/raw/ (gitignored, never committed); the replay files and the
data-driven alarm limits go to data/raw/processed/.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator.prepare import (  # noqa: E402
    Recording,
    prepare_cwru,
    prepare_metropt,
    replay_profiles,
    write_profiles,
)

RAW = ROOT / "data" / "raw"
METROPT_URL = "https://archive.ics.uci.edu/static/public/791/metropt+3+dataset.zip"
METROPT_CSV = "MetroPT3(AirCompressor).csv"

# 1 hp motor load (about 1772 rpm), drive-end bearing. Order defines the replay sequence.
CWRU_BASE = "https://engineering.case.edu/sites/default/files"
CWRU_FILES = (
    # (file, stage, sampling rate). The normal baseline was recorded at 48 kHz, the
    # 12k drive-end fault files at 12 kHz.
    ("98.mat", "normal", 48_000),
    ("106.mat", "inner race fault 0.007 in", 12_000),
    ("170.mat", "inner race fault 0.014 in", 12_000),
    ("210.mat", "inner race fault 0.021 in", 12_000),
)


def download(url: str, target: Path, *, force: bool = False) -> Path:
    if target.exists() and target.stat().st_size > 0 and not force:
        print(f"  have {target.relative_to(ROOT)}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    tmp = target.with_suffix(target.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_bytes(1 << 20):
                f.write(chunk)
    tmp.replace(target)
    return target


def metropt(force: bool) -> Path:
    folder = RAW / "metropt3"
    archive = download(METROPT_URL, folder / "metropt3.zip", force=force)
    csv_path = folder / METROPT_CSV
    if force or not csv_path.exists():
        with zipfile.ZipFile(archive) as z:
            z.extract(METROPT_CSV, folder)
    return csv_path


def cwru(force: bool) -> list[Recording]:
    from scipy.io import loadmat  # only needed here, see the "data" dependency group

    recordings = []
    for name, stage, fs in CWRU_FILES:
        path = download(f"{CWRU_BASE}/{name}", RAW / "cwru" / name, force=force)
        mat = loadmat(path)
        key = next(k for k in mat if k.endswith("DE_time"))
        recordings.append(Recording(stage, np.asarray(mat[key], dtype=np.float64).ravel(), fs))
    return recordings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--force", action="store_true", help="download again")
    args = parser.parse_args()
    out = RAW / "processed"

    print("MetroPT-3")
    metropt_summary = prepare_metropt(metropt(args.force), out)
    print(
        f"  {metropt_summary.rows} rows {metropt_summary.first} .. {metropt_summary.last}\n"
        f"  oil temperature limits {metropt_summary.oil_p99} / {metropt_summary.oil_p999} C, "
        f"TP3 low limits {metropt_summary.tp3_p1} / {metropt_summary.tp3_p01} bar\n"
        f"  duty >= 80% during reported failures: {metropt_summary.duty_flag_rate_in_failures}, "
        f"outside: {metropt_summary.duty_flag_rate_outside}"
    )

    print("CWRU bearing data")
    cwru_summary = prepare_cwru(cwru(args.force), out)
    for stage, accel in cwru_summary.median_accel_g.items():
        velocity = cwru_summary.median_velocity_mm_s[stage]
        print(f"  {stage:<28} accel {accel:.4f} g RMS, velocity {velocity:.3f} mm/s RMS")

    path = write_profiles(
        out, replay_profiles(metropt_summary, cwru_summary), metropt_summary, cwru_summary
    )
    print(f"Wrote {path.relative_to(ROOT)}. Start the replay with SIM_MODE=replay.")


if __name__ == "__main__":
    main()
