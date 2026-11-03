"""Run a list of timed motor moves and keep everything that came back.

A test is a list of Move: "at 0.200 s, motor 3, +4096 counts at 600 rpm". run() hands the
whole list to the link before anything is due, so the times are kept by whatever keeps them
best (the motor controller's own clock when the link is MotorCtrlLink), asks every motor its
position `poll_hz` times a second throughout, and returns the lot on one clock.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .link import Frame
from .servo import Servo


@dataclass(frozen=True)
class Move:
    t: float            # seconds after the run starts
    motor: int          # the motor's CAN id
    counts: int         # 16384 per turn; a change, or a place if `absolute`
    rpm: int = 600
    acc: int = 0
    absolute: bool = False      # counts from where the motor stood when the run began


class TravelError(ValueError):
    pass


def travel(moves: list[Move]) -> dict[int, tuple[int, int, int]]:
    """{motor: (lowest, highest, final)} commanded place, in counts from the start."""
    out = {}
    for m in sorted(moves, key=lambda m: m.t):
        lo, hi, at = out.get(m.motor, (0, 0, 0))
        at = m.counts if m.absolute else at + m.counts
        out[m.motor] = (min(lo, at), max(hi, at), at)
    return out


@dataclass
class Recording:
    t_start: float                                  # time.monotonic() of the run's zero
    t_end: float
    moves: list[Move]
    sent: list[float]                               # when each move's command left; nan if never
    frames: list[Frame]
    positions: dict[int, list[tuple[float, int]]] = field(default_factory=dict)
    arrived: dict[int, list[float]] = field(default_factory=dict)


def run(link, moves: list[Move], limit: int, poll_hz: float = 500.0, lead: float = 0.2,
        tail: float = 0.5, bus: int = 0, listen: tuple[int, ...] = ()) -> Recording:
    """`limit` is how far, in counts either way from where it stands, any motor may be
    commanded during the run: a list that goes further is refused whole, before anything
    moves. It is the only thing between a typing mistake and a broken string. `listen`
    names motors to poll that are not moved."""
    moves = sorted(moves, key=lambda m: m.t)
    for mid, (lo, hi, _) in travel(moves).items():
        if lo < -limit or hi > limit:
            raise TravelError("motor %d would be sent to %d..%d counts; the limit is +-%d"
                              % (mid, lo, hi, limit))
    servos = {mid: Servo(link, mid, bus) for mid in {m.motor for m in moves} | set(listen)}
    home = {mid: s.position() for mid, s in servos.items() if any(m.absolute for m in moves)}
    first = len(link.rx)
    t_start = time.monotonic() + lead
    t_end = t_start + (moves[-1].t if moves else 0.0) + tail
    # one list in time order: the firmware's queue wants it that way
    jobs = [(t_start + m.t, 0, i) for i, m in enumerate(moves)]
    n = int((t_end - t_start) * poll_hz)
    ids = sorted(servos)
    for k in range(n):
        for j, mid in enumerate(ids):
            jobs.append((t_start + (k + (j + 0.5) / len(ids)) / poll_hz, 1, mid))
    seqs = {}
    for at, kind, x in sorted(jobs):
        if kind == 0:
            m = moves[x]
            s = servos[m.motor]
            seqs[x] = (s.move_abs(home[m.motor] + m.counts, m.rpm, m.acc, at=at) if m.absolute
                       else s.move_rel(m.counts, m.rpm, m.acc, at=at))
        else:
            servos[x].ask_position(at=at)
    time.sleep(max(0.0, t_end - time.monotonic()) + 0.1)
    frames = list(link.rx[first:])
    rec = Recording(t_start, t_end, moves,
                    [link.sent.get(seqs[i], float("nan")) for i in range(len(moves))], frames)
    for mid, s in servos.items():
        rec.positions[mid] = s.positions(frames)
        rec.arrived[mid] = s.arrived(frames)
    return rec
