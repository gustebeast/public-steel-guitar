"""publicbench.tune end to end on a pretend string: takes.py's plucked-string sound (the optical
board's SUM, its noise floor and pluck level), a motor whose counts move the string's tension
by a law the model does NOT know, and the real measure / fit / open / verify code. Then the
table compiled from the curves, played by play.c itself (simplay), must land each control on its
note."""
import math
import os
import sys

import numpy as np
import pytest

from publicbench import copedent, tune

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi", "pitch"))
import takes  # noqa: E402


class SimString:
    """The string's pitch from its motor's counts: r = (f / f_open)^2 = 1 + u + q u^2, u the
    stretch from open in units of `k` counts. The model says k = DL_OPEN * COUNTS_PER_MM and
    q = 0; these strings are stiffer or softer and bend the line."""

    def __init__(self, f_open, k_scale=1.3, q=0.06, sign=+1, start_cents=-120.0):
        self.f_open, self.q, self.sign = f_open, q, sign
        self.k = copedent.DL_OPEN_MM * copedent.COUNTS_PER_MM * k_scale
        self.c_open = 50000                                     # wherever the encoder says
        self.pos = int(round(self.counts_at(start_cents)))

    def hz(self, counts):
        u = self.sign * (counts - self.c_open) / self.k
        return self.f_open * math.sqrt(1 + u + self.q * u * u)

    def counts_at(self, c):
        r = 2 ** (c / 600.0)
        u = (-1 + math.sqrt(1 + 4 * self.q * (r - 1))) / (2 * self.q) if self.q else r - 1
        return self.c_open + self.sign * u * self.k


class SimRig:
    def __init__(self, strings, sign=+1):
        self.s, self.sign, self.link = strings, sign, None
        self.played, self.based = [], 0

    def play(self, on): self.played.append(on)
    def playing(self): return True
    def position(self, n): return self.s[n].pos
    def goto(self, n, counts): self.s[n].pos = int(counts)
    def rebase(self): self.based += 1


class SimEar:
    """LISTEN_S of SUM, each listen 0.5 s later than the last; a pluck dies away (2 s, takes.py)
    and asking for one starts it again."""

    def __init__(self, strings, seed=3):
        self.s, self.rng = strings, np.random.default_rng(seed)
        self.age = {n: 99.0 for n in strings}
        self.plucks = 0

    def pluck(self, n):
        self.age[n] = 0.0
        self.plucks += 1

    def hz(self, n, f_guess):
        m = int(tune.LISTEN_S * takes.FS)
        a, b = takes.scaled(*takes.string_wave(self.s[n].hz(self.s[n].pos), m, self.rng))
        x = (a + b) * math.exp(-self.age[n] / 2.0) + self.rng.normal(0, takes.FLOOR, m)
        self.age[n] += 0.5
        return tune.measure(x, takes.FS, f_guess, takes.FLOOR)


def run(strings, sign=+1, tmp=None):
    cop = copedent.load()
    S = {n: SimString(tune.note_hz(cop["open"][n - 1]), sign=sign, **strings[n]) for n in strings}
    rig, ear = SimRig(S, sign), SimEar(S)
    path = os.path.join(tmp, "curves.json")
    data = tune.tune(rig, ear, list(strings), cop, ear.pluck, path, write=False, log=lambda *a: None)
    return cop, S, rig, ear, data, path


def test_note_names():
    assert tune.note_hz("A4") == pytest.approx(440.0)
    assert tune.note_hz("C4") == pytest.approx(261.626, abs=1e-3)
    assert tune.note_hz("F#2") == pytest.approx(92.499, abs=1e-3)
    assert tune.note_hz("Bb3") == pytest.approx(233.082, abs=1e-3)


def test_a_detuned_string_is_left_on_its_open_note(tmp_path):
    cop, S, rig, ear, data, _ = run({4: dict(start_cents=-180.0), 9: dict(start_cents=60.0, k_scale=0.8)},
                                    tmp=str(tmp_path))
    for n in (4, 9):
        assert abs(tune.cents(S[n].hz(S[n].pos), S[n].f_open)) <= tune.TOL_CENTS + 0.5
        assert data["strings"][str(n)]["open_counts"] == S[n].pos
    assert rig.played == [False, True]             # play off while tuning, on again after
    assert ear.plucks > 2                          # it rang out and asked again


def test_the_curve_lands_every_swept_knot(tmp_path):
    _cop, S, _rig, _ear, data, _ = run({3: {}, 10: dict(q=0.12, k_scale=1.6)}, tmp=str(tmp_path))
    for n in (3, 10):
        d, s = data["strings"][str(n)], S[n]
        for c, k in zip(copedent.KNOT_CENTS, d["curve"]):
            if c in d["extrapolated"]:
                continue
            got = tune.cents(s.hz(d["open_counts"] + k), s.f_open)
            assert got == pytest.approx(c, abs=3.0), (n, c, got)
        assert d["verify_worst_cents"] < 3.0
        assert 600 in d["extrapolated"] and 0 not in d["extrapolated"]


def test_a_motor_that_lowers_with_positive_counts(tmp_path):
    _cop, S, _rig, _ear, data, _ = run({1: {}}, sign=-1, tmp=str(tmp_path))
    d = data["strings"]["1"]
    assert d["curve"][-1] < 0 < d["curve"][0]       # raising is negative counts on this motor
    assert d["verify_worst_cents"] < 3.0


def test_a_string_far_over_open_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="over open"):
        run({2: dict(start_cents=600.0)}, tmp=str(tmp_path))


def test_the_table_plays_the_copedent_on_the_measured_curves(tmp_path):
    """The curves into copedent.compile_table, and play.c's own interpolation (copedent.pitch /
    counts, the board's arithmetic) then puts each string where the copedent says."""
    cop, S, _rig, _ear, data, path = run({3: {}, 4: dict(k_scale=0.9)}, tmp=str(tmp_path))
    tune.save(data, path)
    curves = tune.curves_for(tune.load(path))
    assert curves[0] == copedent.model_curve()                  # string 1 was not tuned
    copedent.compile_table(cop, curves=curves)
    ct = copedent.cents_table(cop)
    for k in cop["controls"]:
        for n in (3, 4):
            want = copedent.pitch(ct, {k["slot"]: 1.0}, n - 1)
            if not want:
                continue
            at = data["strings"][str(n)]["open_counts"] + copedent.counts(curves[n - 1], want)
            assert tune.cents(S[n].hz(at), S[n].f_open) == pytest.approx(want, abs=3.0), (k["name"], n)
