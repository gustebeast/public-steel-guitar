"""The bench's tests: what to make a motor do, and what to read off the result.

Each scenario is a list of timed moves for ONE motor and string, built from a base step `d`
(encoder counts, 16384 per turn). Every one ends where it began. They are meant to be run
small first: `d` is a guess until `sizes` has said how many cents a count is worth on the
string under test, and run()'s travel limit refuses anything bigger than it was told to allow.

    hold       nothing moves: how steady the pitch reading is on its own
    step       one step up, one back: delay, settling time, overshoot, and does it come back
    sizes      steps of 1/4, 1/2, 1, 2 and 4 d, each up and back: cents per count, and
               whether small moves are as true as large ones
    speeds     the same step at 300, 600, 1200, 2400 and 3000 rpm: what speed buys
    accels     the same step at five acceleration settings, 0 (none) to 255
    approach   the same place reached from below and from above, five times: lost motion
    repeat     fifty steps up and back: drift, and anything that happens only sometimes
    rapid      up-and-back pairs with the gap between commands shrinking from 300 ms to
               10 ms: how closely moves can follow one another
    retarget   a new place commanded while the motor is still on its way to the last one
               (absolute moves): the lever that changes its mind

analyze() turns a run and its recording into one row per move and a few totals; report()
prints them. Nothing here decides pass or fail: the numbers are for a person to read until
the first real runs say what good looks like.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import pitch
from .run import Move, Recording, travel

REST = 0.6          # seconds between moves that are meant to settle


def hold(motor, d, rpm, acc):
    return []


def step(motor, d, rpm, acc):
    return [Move(REST, motor, d, rpm, acc), Move(2 * REST, motor, -d, rpm, acc)]


def sizes(motor, d, rpm, acc):
    out, t = [], REST
    for k in (0.25, 0.5, 1, 2, 4):
        n = int(round(d * k))
        out += [Move(t, motor, n, rpm, acc), Move(t + REST, motor, -n, rpm, acc)]
        t += 2 * REST
    return out


def speeds(motor, d, rpm, acc):
    out, t = [], REST
    for v in (300, 600, 1200, 2400, 3000):
        out += [Move(t, motor, d, v, acc), Move(t + REST, motor, -d, v, acc)]
        t += 2 * REST
    return out


def accels(motor, d, rpm, acc):
    out, t = [], REST
    for a in (0, 2, 16, 64, 255):
        out += [Move(t, motor, d, rpm, a), Move(t + REST, motor, -d, rpm, a)]
        t += 2 * REST
    return out


def approach(motor, d, rpm, acc):
    """To +d from 0 (from below), then to +d from +2d (from above), back to 0; five times."""
    out, t = [], REST
    for _ in range(5):
        out += [Move(t, motor, d, rpm, acc), Move(t + REST, motor, d, rpm, acc),
                Move(t + 2 * REST, motor, -d, rpm, acc), Move(t + 3 * REST, motor, -d, rpm, acc)]
        t += 4 * REST
    return out


def repeat(motor, d, rpm, acc, n=50):
    out, t = [], REST
    for _ in range(n):
        out += [Move(t, motor, d, rpm, acc), Move(t + REST, motor, -d, rpm, acc)]
        t += 2 * REST
    return out


def rapid(motor, d, rpm, acc):
    out, t = [], REST
    for gap in (0.3, 0.2, 0.1, 0.05, 0.02, 0.01):
        for _ in range(3):
            out += [Move(t, motor, d, rpm, acc), Move(t + gap, motor, -d, rpm, acc)]
            t += 2 * gap
        t += REST                       # ...and let it settle before the next, shorter, gap
    return out


def retarget(motor, d, rpm, acc):
    """Sent to +2d, and told to go to 0, to +d or to +4d after 5, 15 and 40 ms."""
    out, t = [], REST
    for dt in (0.005, 0.015, 0.040):
        for to in (0, d, 4 * d):
            out += [Move(t, motor, 2 * d, rpm, acc, True), Move(t + dt, motor, to, rpm, acc, True),
                    Move(t + REST, motor, 0, rpm, acc, True)]
            t += 2 * REST
    return out


SCENARIOS = {f.__name__: f for f in (hold, step, sizes, speeds, accels, approach, repeat, rapid, retarget)}


@dataclass
class Row:
    t: float                    # the move's time in the run, seconds
    place: int                  # where it was sent, counts from the start
    came_from: int              # ...and from where
    rpm: int
    acc: int
    late_ms: float              # the command left this long after it was asked to
    travel_ms: float            # command -> the motor's "arrived" (nan: none before the next)
    enc_err: float              # encoder at the end of the move's window, minus `place`
                                # (nan when the next move came before this one could finish)
    st: pitch.Step | None       # what the string did (None: the window is too short to say)


@dataclass
class Result:
    name: str
    rows: list[Row]
    hz: float                           # the string's pitch at rest
    noise_cents: float                  # spread of the reading before anything moved
    cents_per_1000: float               # settled pitch against place, least squares
    fit_err_cents: float                # worst settled pitch off that line
    home_spread_cents: float            # range of the settled pitch every time it was back at 0
    lost_motion_cents: float            # same place from below minus from above (nan: never both)
    worst_enc_err: float
    polls_hz: float                     # encoder readings a second actually received
    notes: list[str] = field(default_factory=list)


def analyze(name: str, rec: Recording, motor: int, t0: float, sr: float, audio: np.ndarray,
            hz: float | None = None, tol_cents: float = 3.0) -> Result:
    """`audio` is the string, its first sample at t0 on the run's clock."""
    audio = np.asarray(audio, dtype=float) - np.mean(audio)
    moves = [(i, m) for i, m in enumerate(rec.moves) if m.motor == motor]
    quiet_end = rec.sent[moves[0][0]] if moves else rec.t_end
    quiet = audio[: max(int((quiet_end - t0) * sr), int(0.2 * sr))]
    hz = hz or pitch.guess(quiet, sr)
    f, _ = pitch.track(audio, sr, hz)
    t = t0 + np.arange(len(f)) / sr
    edge = int(0.03 * sr)
    q = f[edge:max(edge + 1, len(quiet) - edge)]
    rest_hz = float(np.median(q))
    noise = float(np.std(pitch.cents(np.maximum(q, 1e-6), rest_hz)))

    pos = rec.positions.get(motor, [])
    pt = np.array([p[0] for p in pos]); pc = np.array([p[1] for p in pos], dtype=float)
    start = pc[0] if len(pc) else 0.0
    rows, at, notes = [], 0, []
    for n, (i, m) in enumerate(moves):
        place = m.counts if m.absolute else at + m.counts
        sent = rec.sent[i]
        nxt = rec.sent[moves[n + 1][0]] if n + 1 < len(moves) else rec.t_end
        if math.isnan(sent):
            notes.append("move %d was never sent" % n)
            rows.append(Row(m.t, place, at, m.rpm, m.acc, math.nan, math.nan, math.nan, None))
            at = place
            continue
        arr = [a for a in rec.arrived.get(motor, []) if sent <= a < nxt]
        inwin = (pt >= sent) & (pt < nxt)
        enc = pc[inwin][-1] - start - place if inwin.any() else math.nan
        st = None
        settles = nxt - sent >= 0.3
        if settles and place != at:
            # (the recording's last tenth of a second is the filter's, not the string's)
            st = pitch.step(f, sr, t0, sent, tol_cents, t_end=min(nxt, rec.t_end - 0.1))
        if not settles:
            enc = math.nan              # it was sent on before it could get there
        rows.append(Row(m.t, place, at, m.rpm, m.acc, (sent - rec.t_start - m.t) * 1e3,
                        (arr[0] - sent) * 1e3 if arr else math.nan, enc, st))
        at = place

    settled = [(r.place, r.came_from, pitch.cents(r.st.after_hz, rest_hz)) for r in rows if r.st]
    slope = fit = math.nan
    if len({p for p, _, _ in settled}) >= 2:
        x = np.array([p for p, _, _ in settled], dtype=float); y = np.array([c for _, _, c in settled])
        slope, icpt = np.polyfit(x, y, 1)
        fit = float(np.max(np.abs(y - (slope * x + icpt))))
        slope = float(slope * 1000.0)
    home = [c for p, _, c in settled if p == 0]
    lost = math.nan
    places = {p for p, _, _ in settled}
    diffs = []
    for p in places:
        up = [c for q_, frm, c in settled if q_ == p and frm < p]
        dn = [c for q_, frm, c in settled if q_ == p and frm > p]
        if up and dn:
            diffs.append(float(np.mean(up) - np.mean(dn)))
    if diffs:
        lost = max(diffs, key=abs)
    encs = [abs(r.enc_err) for r in rows if not math.isnan(r.enc_err)]
    dur = rec.t_end - rec.t_start
    return Result(name, rows, rest_hz, noise, slope, fit,
                  float(max(home) - min(home)) if len(home) > 1 else math.nan, lost,
                  max(encs) if encs else math.nan, len(pos) / dur if dur > 0 else 0.0, notes)


def _n(v, fmt="%7.1f"):
    return "      -" if v is None or (isinstance(v, float) and math.isnan(v)) else fmt % v


def report(r: Result) -> str:
    out = ["%s: string at %.2f Hz, reading steady to %.2f cents (1 sigma) before any move"
           % (r.name, r.hz, r.noise_cents),
           "    t s    from      to   rpm acc  late ms  travel   enc err |   cents   onset  settle    over",
           ]
    for w in r.rows:
        s = w.st
        out.append("%7.2f %7d %7d %5d %3d  %s %s %s | %s %s %s %s" % (
            w.t, w.came_from, w.place, w.rpm, w.acc, _n(w.late_ms, "%7.2f"), _n(w.travel_ms), _n(w.enc_err, "%7.0f"),
            _n(s.moved_cents if s else None), _n(s.onset_s * 1e3 if s else None),
            _n(s.settle_s * 1e3 if s else None), _n(s.overshoot_cents if s else None)))
    out += ["(late, travel, onset, settle in ms; enc err in counts; settle = inside %.0f cents for good)"
            % (r.rows[0].st.tol_cents if r.rows and r.rows[0].st else 3.0),
            "cents per 1000 counts      %s   (worst settled pitch off that line: %s cents)"
            % (_n(r.cents_per_1000, "%8.2f"), _n(r.fit_err_cents, "%.2f")),
            "pitch back at the start    %s cents between the best and worst return" % _n(r.home_spread_cents, "%8.2f"),
            "lost motion                %s cents (same place from below minus from above)" % _n(r.lost_motion_cents, "%8.2f"),
            "encoder, worst             %s counts off where it was sent" % _n(r.worst_enc_err, "%8.0f"),
            "encoder readings           %8.0f a second" % r.polls_hz]
    out += ["NOTE: " + n for n in r.notes]
    return "\n".join(out)


def plan(name: str, motor: int, d: int, rpm: int = 600, acc: int = 0):
    """(moves, the furthest any of them goes from the start, in counts)."""
    moves = SCENARIOS[name](motor, d, rpm, acc)
    lo, hi, end = travel(moves).get(motor, (0, 0, 0))
    assert end == 0, "%s does not end where it began" % name
    return moves, max(-lo, hi)
