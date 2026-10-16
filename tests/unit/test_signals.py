import math
from datetime import datetime, timedelta

import numpy as np
import pytest

from simulator.signals import (
    G,
    band_rms_g,
    percentile,
    rolling_duty,
    velocity_rms_mm_s,
    windows,
)

FS = 12_000.0


def sine_g(freq: float, amplitude_g: float, seconds: float = 1.0) -> np.ndarray:
    t = np.arange(int(FS * seconds)) / FS
    return amplitude_g * np.sin(2 * np.pi * freq * t)


def test_velocity_of_a_sine_matches_analytic_integration() -> None:
    # a = A sin(wt)  ->  v = A/w cos(wt), RMS = A / (w * sqrt 2)
    freq, amp = 100.0, 0.5
    expected = amp * G / (2 * math.pi * freq) / math.sqrt(2) * 1000
    assert velocity_rms_mm_s(sine_g(freq, amp), FS) == pytest.approx(expected, rel=1e-3)


def test_velocity_band_excludes_out_of_band_content() -> None:
    assert velocity_rms_mm_s(sine_g(3000.0, 1.0), FS) == pytest.approx(0.0, abs=1e-6)


def test_band_rms_keeps_only_the_band() -> None:
    signal = sine_g(1000.0, 0.4) + sine_g(50.0, 2.0)
    assert band_rms_g(signal, FS) == pytest.approx(0.4 / math.sqrt(2), rel=1e-3)


def test_windows_overlap_by_half() -> None:
    chunks = list(windows(np.zeros(int(FS * 3)), FS, seconds=1.0))
    assert len(chunks) == 5
    assert all(len(c) == int(FS) for c in chunks)


def test_rolling_duty_tracks_the_trailing_window() -> None:
    start = datetime(2020, 1, 1)
    samples = [(start + timedelta(minutes=i), i >= 5) for i in range(10)]
    duties = list(rolling_duty(samples, window_seconds=4 * 60))
    assert duties[0] == 0.0
    assert duties[4] == 0.0
    assert duties[6] == pytest.approx(40.0)  # minutes 2..6, two of five loaded
    assert duties[9] == 100.0


def test_percentile() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
