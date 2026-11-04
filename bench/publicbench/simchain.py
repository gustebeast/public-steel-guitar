"""Bus B as wired from motor_ctrl R2: two arms of chained lever boards, each powering the next,
motor_ctrl's arm and lane switching (arms.c through simarms.py) and the Pi's side of the flash
lane, all stepped on one simulated clock. leverisp.py drives it exactly as it drives the
hardware (SimBench stands in for PiBench).

Each board runs the real lever.c and ldr.c (simlever.Board). What is pretend here is main.c /
boot.c's hardware: the next board's 5 V, the BOOT0 detector and WCH's ROM loader. A board
that powers up while its arm's pair is on the flash lane comes up in the ROM (a USB host holds
the pair low); a board with an empty flash says nothing at all.
"""
from __future__ import annotations

import time

from .link import Frame, _Base
from .levers import K
from .simarms import Arms, K as AK
from .simlever import Board

STEP_US = 1000


class Node:
    """One board in a chain."""

    def __init__(self, uid: int, app: bytes | None, blank: bool = False, dead: bool = False):
        self.uid = uid
        self.board = Board(uid, app_image=app)
        self.blank = blank              # nothing in flash: not even the CAN loader
        self.dead = dead                # a board whose ROM never enumerates either
        self.powered = self.rom = self.parked = self.next_on = self.auto = False
        self.t_start = 0
        self.next_back_at = None
        self.isp_writes = 0
        self._watch()

    def _watch(self):
        """A restart (CMD 'B', the loader's 'G') drops the next board's 5 V, as main.c's and
        boot.c's start-up does, and starts the NEXT_AFTER_US clock again."""
        reset = self.board.reset

        def watched(now_us=0):
            reset(now_us)
            self.next_on, self.auto, self.t_start = False, False, now_us
        self.board.reset = watched

    def up(self, now, on_usb):
        self.powered, self.parked, self.next_on, self.auto = True, False, False, False
        self.next_back_at = None
        self.t_start = now
        self.rom = on_usb               # BOOT0 from the bus: a USB pair reads "not CAN"
        if not self.rom and not self.blank:
            self.board.reset(now)

    def down(self):
        self.powered = self.rom = self.parked = self.next_on = False

    @property
    def on_can(self):
        return self.powered and not self.rom and not self.parked and not self.blank


class SimLink(_Base):
    """The Pi's view of bus B through motor_ctrl, on the simulator's clock: wait() steps it."""

    def __init__(self, bench):
        super().__init__()
        self.bench = bench
        self.out: list[tuple[int, bytes]] = []
        self.down = False

    def send(self, can_id, data, at=None, bus=1):
        if self.down:
            raise RuntimeError("the link is down (a flash window is open)")
        self.out.append((can_id, bytes(data)))
        return self._next_seq()

    def wait(self, pred, timeout=1.0):
        end = self.bench.now + int(timeout * 1e6)
        while True:
            v = pred()
            if v:
                return v
            if self.bench.now >= end:
                return None
            self.bench.step()

    def close(self):
        pass


class SimBench:
    """Stands in for leverisp.PiBench."""

    off_s = AK["ARM_OFF_US"] / 1e6
    window_ms = 3000

    def __init__(self, arms: list[list[Node]]):
        self.now = 0
        self.chains = arms
        self.arms = Arms()
        self.link = SimLink(self)
        self.windows = []
        for a, chain in enumerate(self.chains):
            self._power_chain(a)

    # what motor_ctrl's lines do
    def power(self, arm, what):
        assert self.arms.power(arm, what, self.now), "motor_ctrl refused A %d %d" % (arm, what)

    def window(self, arm, cycle):
        assert self.arms.flash(arm, self.window_ms, cycle, self.now), "motor_ctrl refused U"
        self.windows.append((arm, cycle))
        self._until = self.now + AK["ARM_LEAD_US"] + self.window_ms * 1000
        self.link.down = True

    def isp(self, image: bytes):
        """wchisp: retry until exactly one ROM loader is on the lane, then write it."""
        end = self._until - 1000000
        while self.now < end:
            roms = [n for a, ch in enumerate(self.chains) for n in ch
                    if n.rom and n.powered and self.arms.usb(a) and self.arms.lane()]
            assert len(roms) <= 1, "two ROM loaders on the flash lane at once"
            if roms and not roms[0].dead:
                n = roms[0]
                n.blank = False         # the loader is in; its application area is erased
                n.board = Board(n.uid)
                n._watch()
                n.isp_writes += 1
                return
            for _ in range(500):
                self.step()
        raise SystemExit("no ROM loader answered on the flash lane inside the window")

    def after_window(self):
        while self.now < self._until + AK["ARM_OFF_US"] + 50000:
            self.step()
        self.link.down = False

    # the wiring
    def _power_chain(self, a):
        """Each board's 5 V from the one before it (the first from motor_ctrl)."""
        feed = self.arms.powered(a)
        for n in self.chains[a]:
            if feed and not n.powered:
                n.up(self.now, self.arms.usb(a))
            elif not feed and n.powered:
                n.down()
            feed = n.powered and n.next_on

    def step(self):
        self.now += STEP_US
        self.arms.poll(self.now)
        from_pi, self.link.out = self.link.out, []
        for a, chain in enumerate(self.chains):
            self._power_chain(a)
            can = not self.arms.usb(a)          # the arm's pair reaches U3
            for n in chain:
                if not n.on_can:
                    continue
                if can:
                    for can_id, d in from_pi:
                        if n.board.accepts(can_id, can_id > 0x7FF):
                            n.board.rx(can_id, d)
                for can_id, ext, d in n.board.poll(self.now):
                    if can:
                        self.link._got(Frame(time.monotonic(), 1, can_id, d))
                lv = n.board.lv
                rel = lv.take_release()
                if rel:
                    ms, cyc = rel
                    n.parked = True             # transceiver off, waiting for a power cycle
                    if cyc:
                        n.next_on = False
                        n.next_back_at = self.now + ms * 1000
                    continue
                w = lv.take_next()
                if w:
                    n.next_on = w == 1
                elif not lv.held() and not n.auto and self.now - n.t_start >= K["NEXT_AFTER_US"]:
                    n.next_on = n.auto = True
            for n in chain:                     # a parked board's one timed act
                if n.parked and n.next_back_at is not None and self.now >= n.next_back_at:
                    n.next_on, n.next_back_at = True, None
            self._power_chain(a)
