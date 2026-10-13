"""Pitch against time from a recording of ONE string, and what a tension change did to it.

The bench knows roughly what note a string is at, so this does not search for a pitch: it
band-passes round the fundamental and reads the frequency off the phase of the analytic
signal. That gives a pitch value per sample, smoothed over a few milliseconds, which is what
a "how fast did it get there" measurement needs and what a frame-by-frame detector blurs.

Any source will do -- the optical board's stream, a pickup into a sound card, a WAV file --
as long as the samples carry times on the same clock as the motor commands.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt


def cents(f, ref):
    return 1200.0 * np.log2(np.asarray(f, dtype=float) / ref)


def track(audio: np.ndarray, sr: float, f_guess: float, span_semitones: float = 5.0,
          smooth_ms: float = 15.0):
    """(frequency per sample in Hz, envelope per sample). `f_guess` must be within
    span_semitones of the fundamental throughout; keep the span under an octave's half so
    the second harmonic stays out of the band.

    smooth_ms trades time for pitch: noise in the reading falls as its 1.5th power, and a
    change is smeared over it. With a signal 40 dB over its noise at 220 Hz, 3 ms reads to
    about 6 cents and 15 ms to about half a cent."""
    lo = f_guess * 2 ** (-span_semitones / 12.0)
    hi = min(f_guess * 2 ** (span_semitones / 12.0), sr * 0.45)
    sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    z = hilbert(sosfiltfilt(sos, audio))
    f = np.diff(np.unwrap(np.angle(z))) * sr / (2 * np.pi)
    f = np.append(f, f[-1])
    n = max(1, int(sr * smooth_ms / 1000.0))
    k = np.ones(n) / n
    return np.convolve(f, k, mode="same"), np.convolve(np.abs(z), k, mode="same")


@dataclass
class Step:
    before_hz: float        # the pitch before the command
    after_hz: float         # ...and once settled
    moved_cents: float      # the change
    onset_s: float          # command -> pitch first leaves `tol_cents` of where it was
    settle_s: float         # command -> pitch inside tol_cents of the end, for good
    overshoot_cents: float  # furthest past the end value, in the direction of the move
    tol_cents: float


def step(f: np.ndarray, sr: float, t0: float, t_cmd: float, tol_cents: float = 3.0,
         rest_s: float = 0.1, edge_s: float = 0.03) -> Step:
    """Measure one pitch change. `f` is track()'s output, its first sample at time t0;
    `t_cmd` is when the command left. The last and first rest_s of the stretch looked at
    are taken as "settled" and "before". edge_s at each end of the recording is not looked
    at: the filter and the phase have nothing to stand on there."""
    k = int(edge_s * sr)
    f, t0 = np.maximum(f[k:len(f) - k], 1e-6), t0 + k / sr
    t = t0 + np.arange(len(f)) / sr
    pre = f[(t > t_cmd - rest_s) & (t < t_cmd)]
    post = f[t > t[-1] - rest_s]
    before, after = float(np.median(pre)), float(np.median(post))
    c = cents(f, after)
    c_before = float(cents(before, after))
    aft = t >= t_cmd
    left = aft & (np.abs(c - c_before) > tol_cents)
    onset = float(t[left][0] - t_cmd) if left.any() else float("nan")
    out = aft & (np.abs(c) > tol_cents)
    settle = float(t[out][-1] - t_cmd + 1.0 / sr) if out.any() else 0.0
    sign = -1.0 if c_before > 0 else 1.0        # +1: pitch rose to get here
    over = float(max(0.0, np.max(sign * c[aft])))
    return Step(before, after, -c_before, onset, settle, over, tol_cents)
