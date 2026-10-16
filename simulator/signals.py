"""Signal processing used to turn the raw public datasets into replayable readings."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator, Sequence
from datetime import datetime

import numpy as np
from numpy.typing import NDArray

G = 9.80665  # m/s2 per g

FloatArray = NDArray[np.float64]


def _spectrum(acc_g: FloatArray, fs: float) -> tuple[FloatArray, NDArray[np.complex128]]:
    a = (acc_g - acc_g.mean()) * G
    return np.fft.rfftfreq(len(a), 1 / fs), np.fft.rfft(a)


def velocity_rms_mm_s(
    acc_g: FloatArray, fs: float, band: tuple[float, float] = (10.0, 1000.0)
) -> float:
    """Velocity RMS in mm/s from acceleration in g, integrated in the frequency domain.

    10-1000 Hz is the band of ISO 10816 vibration severity, the quantity the alarm
    limits in the manuals are written in.
    """
    freqs, spectrum = _spectrum(acc_g, fs)
    keep = (freqs >= band[0]) & (freqs <= band[1])
    velocity = np.zeros_like(spectrum)
    velocity[keep] = spectrum[keep] / (2j * np.pi * freqs[keep])
    v = np.fft.irfft(velocity, len(acc_g))
    return float(np.sqrt(np.mean(v**2)) * 1000)


def band_rms_g(acc_g: FloatArray, fs: float, band: tuple[float, float] = (500.0, 5000.0)) -> float:
    """Acceleration RMS in g within a band; high-frequency energy is where bearing defects show."""
    freqs, spectrum = _spectrum(acc_g, fs)
    keep = (freqs >= band[0]) & (freqs <= band[1])
    filtered = np.zeros_like(spectrum)
    filtered[keep] = spectrum[keep]
    a = np.fft.irfft(filtered, len(acc_g))
    return float(np.sqrt(np.mean(a**2)) / G)


def windows(signal: FloatArray, fs: float, seconds: float = 1.0) -> Iterator[FloatArray]:
    """Consecutive windows with 50% overlap."""
    size = int(fs * seconds)
    for start in range(0, len(signal) - size + 1, size // 2):
        yield signal[start : start + size]


class RollingDuty:
    """Percentage of a trailing time window during which the machine was loaded.

    Fed (timestamp, loaded) samples in chronological order; each sample counts as one
    observation (the dataset is evenly sampled apart from gaps).
    """

    def __init__(self, window_seconds: float = 1800.0) -> None:
        self.window_seconds = window_seconds
        self._recent: deque[tuple[datetime, bool]] = deque()
        self._loaded = 0

    def update(self, ts: datetime, loaded: bool) -> float:
        self._recent.append((ts, loaded))
        self._loaded += loaded
        while (ts - self._recent[0][0]).total_seconds() > self.window_seconds:
            _, old = self._recent.popleft()
            self._loaded -= old
        return 100.0 * self._loaded / len(self._recent)


def rolling_duty(
    samples: Iterable[tuple[datetime, bool]], window_seconds: float = 1800.0
) -> Iterator[float]:
    duty = RollingDuty(window_seconds)
    for ts, loaded in samples:
        yield duty.update(ts, loaded)


def percentile(values: Sequence[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))
