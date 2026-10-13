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
    counts: int         # 16384 per turn, relative
    rpm: int = 600
    acc: int = 0


@dataclass
class Recording:
    t_start: float                                  # time.monotonic() of the run's zero
    t_end: float
    moves: list[Move]
    sent: list[float]                               # when each move's command left; nan if never
    frames: list[Frame]
    positions: dict[int, list[tuple[float, int]]] = field(default_factory=dict)
    arrived: dict[int, list[float]] = field(default_factory=dict)


def run(link, moves: list[Move], poll_hz: float = 500.0, lead: float = 0.2, tail: float = 0.5,
        bus: int = 0) -> Recording:
    moves = sorted(moves, key=lambda m: m.t)
    servos = {m.motor: Servo(link, m.motor, bus) for m in moves}
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
            seqs[x] = servos[m.motor].move_rel(m.counts, m.rpm, m.acc, at=at)
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
