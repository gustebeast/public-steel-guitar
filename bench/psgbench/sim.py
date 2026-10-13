"""A pretend motor and a pretend string, so the bench's own code can be run with no hardware.

SimServo answers servo.py's commands on a python-can "virtual" bus and moves along a
trapezoid; SimString turns the motor's recorded positions into the sound of a string whose
pitch follows them. They prove the plumbing (scheduling, timestamps, pitch tracking, the
numbers a test reports). They say NOTHING about the real motor, belt or string: both are
built from the same assumptions as the code they exercise.
"""
from __future__ import annotations

import math
import threading
import time

import numpy as np

from . import servo as S


class SimServo(threading.Thread):
    def __init__(self, can_id=1, channel="psg-sim", reply_delay=0.0005, accel_turns_s2=400.0):
        super().__init__(daemon=True)
        import can
        self._can = can
        self.bus = can.Bus(channel=channel, interface="virtual")
        self.id = can_id
        self.reply_delay = reply_delay
        self.accel = accel_turns_s2 * S.COUNTS_PER_TURN
        self.pos = 0.0
        self.vel = 0.0
        self.target = None
        self.vlim = 0.0
        self.code = 0
        self.enabled = False
        self.history: list[tuple[float, float]] = []    # (time.monotonic(), counts)
        self._run = True

    def _reply(self, body: bytes):
        self.bus.send(self._can.Message(arbitration_id=self.id, data=S.pack(self.id, body),
                                        is_extended_id=False))

    def _command(self, d: bytes):
        if not S.check(self.id, d):
            return
        code = d[0]
        if code == S.ENABLE:
            self.enabled = bool(d[1])
            self._reply(bytes([code, 1]))
        elif code == S.READ_ENCODER:
            self._reply(bytes([code]) + int(round(self.pos)).to_bytes(6, "big", signed=True))
        elif code in (S.MOVE_REL, S.MOVE_ABS):
            rpm = int.from_bytes(d[1:3], "big")
            counts = int.from_bytes(d[4:7], "big", signed=True)
            if not self.enabled or rpm == 0:
                self._reply(bytes([code, 0]))
                return
            self.target = counts if code == S.MOVE_ABS else round(self.pos) + counts
            self.vlim = rpm / 60.0 * S.COUNTS_PER_TURN
            self.code = code
            self._reply(bytes([code, S.STARTED]))

    def run(self):
        dt = 0.0005
        nxt = time.monotonic()
        while self._run:
            m = self.bus.recv(0)
            while m is not None:
                if m.arbitration_id == self.id:
                    time.sleep(self.reply_delay)
                    self._command(bytes(m.data))
                m = self.bus.recv(0)
            if self.target is not None:
                dist = self.target - self.pos
                want = math.copysign(min(self.vlim, math.sqrt(2 * self.accel * abs(dist))), dist)
                dv = max(-self.accel * dt, min(self.accel * dt, want - self.vel))
                self.vel += dv
                self.pos += self.vel * dt
                crossed = (self.target - self.pos) * dist <= 0      # a real loop does not overshoot by a tick
                if crossed or (abs(self.target - self.pos) < 2.0 and abs(self.vel) <= 2 * self.accel * dt):
                    self.pos, self.vel, self.target = float(self.target), 0.0, None
                    self._reply(bytes([self.code, S.ARRIVED]))
            self.history.append((time.monotonic(), self.pos))
            nxt += dt
            time.sleep(max(0.0, nxt - time.monotonic()))

    def stop(self):
        self._run = False
        self.join(1.0)
        self.bus.shutdown()


def string_audio(history, t0: float, t1: float, sr: float = 48000.0, f0: float = 220.0,
                 cents_per_turn: float = 200.0, noise: float = 0.01, seed: int = 1):
    """The sound, from t0 to t1, of a string at f0 whose pitch rises cents_per_turn for each
    turn of the motor in `history` ([(t, counts)])."""
    history = list(history)             # the motor's thread may still be adding to it
    ht = np.array([h[0] for h in history])
    hp = np.array([h[1] for h in history]) / S.COUNTS_PER_TURN
    t = t0 + np.arange(int((t1 - t0) * sr)) / sr
    turns = np.interp(t, ht, hp)
    f = f0 * 2.0 ** (cents_per_turn * (turns - hp[0]) / 1200.0)
    ph = 2 * np.pi * np.cumsum(f) / sr
    x = np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)
    return x + noise * np.random.default_rng(seed).standard_normal(len(x))
