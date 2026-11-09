"""Detect whether the input audio is a tight loop and, if so, the loop period.

Cross-correlation of a downsampled mono mix is robust to small amplitude
variations and cheap (FFT-based, ~25 ms for a 3-minute clip). When the input
genuinely loops — game-music corpora, drum-loop libraries, ambient beds —
this enables `separate_loop_aware` to run Demucs on a single period and tile
the stems back to full length, cutting separation cost by Nx where N is the
loop count.

The detector is deliberately conservative: a false positive corrupts every
downstream artifact, so the confidence floor sits well above what generic
music achieves on autocorrelation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LoopDetection:
    period_samples: int   # detected loop period at the input sample rate
    period_s: float
    confidence: float     # normalized autocorrelation peak height in [0, 1]
    n_repeats: int        # number of full periods that fit in the input


def detect_loop_period(
    samples: np.ndarray,
    sample_rate: int,
    *,
    min_period_s: float = 1.5,
    max_period_s: float = 60.0,
    min_confidence: float = 0.92,
    target_sr: int = 8000,
) -> LoopDetection | None:
    """Return loop-period info if `samples` is a tight loop, else None.

    `samples` is `(channels, n)` or `(n,)` float32 audio. Confidence is the
    normalized autocorrelation peak; the default 0.92 threshold rejects
    generic music (which sits around 0.4-0.7) and accepts clean loops (>0.95
    on the Encarta MindMaze QUESTION/BGLOOPx renders).

    Also requires the detected period to evenly divide the input duration
    within 1 % — true loops repeat an integer number of times.
    """
    mono = samples.mean(axis=0) if samples.ndim == 2 else samples
    mono = mono.astype(np.float32, copy=False)
    n_full = mono.size
    if n_full == 0:
        return None

    # Downsample by integer stride for cheap autocorrelation. 8 kHz is plenty
    # to localize a loop period to ~125 µs at the downsampled rate, which
    # rescales to ~14 ms at 44.1 kHz — well below a 16th note even at 240 BPM.
    step = max(1, sample_rate // target_sr)
    y = mono[::step]
    sr_ds = sample_rate // step
    n = y.size
    if n < int(min_period_s * sr_ds) * 2:
        return None  # too short to host a loop

    # Energy-normalize so the autocorrelation peak height is in [0, 1].
    y = y - y.mean()
    energy = float(np.dot(y, y))
    if energy < 1e-9:
        return None

    # FFT autocorrelation. Zero-pad to next power of two ≥ 2n to avoid wraparound.
    fft_size = 1 << int(np.ceil(np.log2(2 * n)))
    Y = np.fft.rfft(y, fft_size)
    raw_ac = np.fft.irfft(Y * np.conj(Y), fft_size).real[:n]

    # Coverage correction: raw_ac[k] sums over (N-k) pairs, so a perfectly
    # periodic signal still drops as k grows. Dividing by (N-k) gives a
    # per-pair correlation that hits ~1.0 for true repetition regardless of
    # how many periods fit. Normalize against per-window energy so amplitude
    # variation between cycles doesn't bias the score.
    lags = np.arange(n, dtype=np.float64)
    overlap = np.clip(n - lags, 1.0, None)
    # Per-pair correlation; bounded above by per-window energy / overlap.
    ac = raw_ac / (overlap * (energy / n))

    min_lag = int(min_period_s * sr_ds)
    # Cap max_lag at n//2 so every candidate keeps ≥ one full period of overlap.
    # Without this, the coverage-corrected ratio blows up at the tail where
    # only a handful of samples overlap and noise can correlate by accident.
    max_lag = min(int(max_period_s * sr_ds), n // 2)
    if max_lag <= min_lag:
        return None
    region = ac[min_lag:max_lag]
    peak_value = float(np.max(region))
    # Repeated periods and their integer multiples are all correlation peaks.
    # A small tolerance also absorbs coverage-correction drift for smooth
    # signals; it is separate from the conservative confidence floor. Then
    # choose the earliest period that also fits the input duration.
    tie_tolerance = max(1e-3, abs(peak_value) * 1e-3)
    local_maxima = np.ones(region.shape, dtype=bool)
    if region.size > 1:
        local_maxima[0] = region[0] >= region[1]
        local_maxima[-1] = region[-1] >= region[-2]
    if region.size > 2:
        local_maxima[1:-1] = (region[1:-1] >= region[:-2]) & (region[1:-1] >= region[2:])
    peak_candidates = np.flatnonzero(
        local_maxima
        & (region >= min_confidence)
        & (region >= peak_value - tie_tolerance)
    )
    if peak_candidates.size == 0:
        return None

    # Sub-minimum loops must not be re-labelled as a longer harmonic. Ignore
    # the near-zero-lag autocorrelation shoulder; only strong local peaks from
    # 100 ms up to the configured search floor count as shorter periods.
    short_min_lag = max(1, int(0.1 * sr_ds))
    short_region = ac[short_min_lag:min_lag]
    short_peaks = np.zeros(short_region.shape, dtype=bool)
    if short_region.size > 1:
        short_peaks[0] = short_region[0] >= short_region[1]
        short_peaks[-1] = short_region[-1] >= short_region[-2]
    if short_region.size > 2:
        short_peaks[1:-1] = (
            (short_region[1:-1] >= short_region[:-2])
            & (short_region[1:-1] >= short_region[2:])
        )
    short_period_lags = (
        np.flatnonzero(short_peaks & (short_region >= min_confidence)) + short_min_lag
    )

    for peak_rel in peak_candidates:
        period_ds = min_lag + int(peak_rel)
        period_samples = round(period_ds * step)
        n_repeats = round(n_full / period_samples)

        # True loops repeat at least twice and divide the input within ~1 %.
        if n_repeats < 2:
            continue
        residual = abs(n_full - n_repeats * period_samples) / max(n_full, 1)
        if residual > 0.01:
            continue

        # If this candidate is an integer multiple of a strong period below the
        # configured minimum, it is a harmonic, not an admissible loop period.
        has_shorter_period = bool(
            short_period_lags.size
            and np.any(period_ds % short_period_lags == 0)
        )
        if has_shorter_period:
            continue

        return LoopDetection(
            period_samples=period_samples,
            period_s=period_samples / sample_rate,
            confidence=float(ac[period_ds]),
            n_repeats=n_repeats,
        )
    return None
