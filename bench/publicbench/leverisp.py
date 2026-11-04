"""Flash every lever and pedal board from the Pi, blank ones included (docs/lever-usb-flash.md).

    python3 -m publicbench.leverisp levers --slots 0,1,2,3,4,5 --loader build/boot.bin --app build/lever.bin
    python3 -m publicbench.leverisp pedals --slots 6,7,8,9,10 ...
    python3 -m publicbench.leverisp levers --walk          the arm's boards in chain order, and where it stops

One arm at a time, the other held dark. Walk the chain (ALL 'H', then CMD 'N' one board at a
time); the first board that stays silent is blank or broken. Hand it its loader over USB:
ALL 'U' parks every board and has the one before it cycle it onto the pair, motor_ctrl's 'U'
puts the arm's pair and J4 on the flash lane for a window, WCH's ROM loader enumerates and
the ISP tool writes the loader. When the window closes motor_ctrl power-cycles the arms; the
board comes back in its own CAN loader with no slot, takes the slot its place in the chain is
given (--slots, chain order) and its application over CAN (leverflash.py). Walk again, until
every place answers with an application.

The link to motor_ctrl is down for the whole window (J4 goes with the lane), so the window is
fixed when it is opened and the Pi waits it out.

The ISP tool is wchisp (https://github.com/ch32-rs/wchisp). It is NOT installed on the Pi:
installing it is the user's call. Without it, `--walk` still works and the flash stops at the
first blank board with what to do.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time

from . import leverflash
from .levers import K, Hello, Levers

ARM = {"pedals": 0, "levers": 1}
LEVER_OFF_MS = 300          # ALL 'U': the board before the target holds it dark this long, past
                            # motor_ctrl's ARM_LEAD_US switch-over (firmware/motor_ctrl/arms.h)
STEP_WAIT = 0.4             # a board's HELLO after its power comes on


class FlashError(SystemExit):
    pass


def _quiet(link, s: float):
    """Let s seconds pass on the link's clock (a simulator steps its own)."""
    link.wait(lambda: None, s)


def _hellos_since(lv: Levers, t0: float) -> list[Hello]:
    lv.update()
    return sorted((h for h in lv.hello.values() if h.t >= t0), key=lambda h: h.t)


def walk(bench, arm: int, plan: list[int], log=print) -> tuple[list[Hello], bool]:
    """The arm's boards in chain order, each given its planned slot if it had none, and whether
    the walk stopped at a silent place (True) or at the end of the plan (False)."""
    bench.power(1 - arm, 0)
    bench.power(arm, 2)
    lv = Levers(bench.link, bus=1)
    _quiet(bench.link, bench.off_s + 0.05)
    lv._send(K["ID_ALL"], bytes([K["LC_HOLD"]]))
    _quiet(bench.link, 0.05)
    t0 = time.monotonic()
    lv._send(K["ID_ALL"], bytes([K["LC_HELLO"]]))
    _quiet(bench.link, STEP_WAIT)
    first = _hellos_since(lv, t0)
    if len(first) > 1:
        raise FlashError("%d boards answered with the chain held: the other arm is not dark" % len(first))
    order: list[Hello] = []
    nxt = first[0] if first else None
    while nxt is not None:
        i = len(order)
        if i >= len(plan):
            raise FlashError("more boards on the arm than --slots names (%d)" % len(plan))
        if nxt.slot != plan[i]:
            if not lv.assign(nxt.uid, plan[i], timeout=1.0):
                raise FlashError("board %08x at place %d did not take slot %d" % (nxt.uid, i, plan[i]))
            log("place %d: board %08x given slot %d" % (i, nxt.uid, plan[i]))
            nxt = lv.hello[nxt.uid]
        order.append(nxt)
        if len(order) == len(plan):
            return order, False
        t0 = time.monotonic()
        if not lv.command(nxt.slot, chr(K["LC_NEXT"]), b"\x01", timeout=1.0):
            raise FlashError("slot %d refused to power the next board" % nxt.slot)
        seen = {h.uid for h in order}

        def new():
            return next((h for h in _hellos_since(lv, t0) if h.uid not in seen), None)
        nxt = bench.link.wait(new, STEP_WAIT)
        # ⚠ HOLD IT AT ONCE. It was dark when the first ALL 'H' went out, so it never heard it,
        # and NEXT_AFTER_US after its start it powers the board after it: that board's HELLO
        # would come before the 'N' meant to bring it, and the walk would call it silent.
        lv._send(K["ID_ALL"], bytes([K["LC_HOLD"]]))
    return order, True


def give_loader(bench, arm: int, before: int | None, loader: bytes, log=print):
    """The silent board after slot `before` (None: the arm's first) gets its loader over USB."""
    lv = Levers(bench.link, bus=1)
    slot = K["SLOT_NONE"] if before is None else before
    lv._send(K["ID_ALL"], bytes([K["LC_RELEASE"]]) + LEVER_OFF_MS.to_bytes(2, "little") + bytes([slot]))
    bench.window(arm, cycle=before is None)
    try:
        bench.isp(loader)
    finally:
        bench.after_window()
    log("loader written to the board after %s" % ("the arm's start" if before is None else "slot %d" % before))


def flash_arm(bench, arm: int, plan: list[int], loader: bytes | None, app: bytes, log=print):
    """Every place on the arm running `app`. Boards with a loader take it over CAN; blank or
    broken ones get their loader over USB first."""
    tried: set[int | None] = set()
    while True:
        order, silent = walk(bench, arm, plan, log)
        lv = Levers(bench.link, bus=1)
        stale = [h for h in order if h.mode == 1]
        for h in stale:
            log("slot %d in its loader: writing the application" % h.slot)
            leverflash.write(lv, h.slot, app, log)
        if stale:
            continue                # a board restarted into its application: walk again
        if not silent:
            log("%d boards, all answering" % len(order))
            return order
        before = order[-1].slot if order else None
        if before in tried:
            raise FlashError("the board after %s is still silent after its loader was written: "
                             "check it by hand" % ("the arm's start" if before is None else "slot %d" % before))
        if loader is None:
            raise FlashError("place %d is silent (blank or broken) and no --loader was given" % len(order))
        tried.add(before)
        give_loader(bench, arm, before, loader, log)


# ---- the real thing: motor_ctrl R2 over its link, wchisp ---------------------------------------
class PiBench:
    """motor_ctrl's arms through its link; the ISP tool on the Pi's USB."""

    off_s = 0.2                     # firmware/motor_ctrl/arms.h ARM_OFF_US
    window_ms = 15000

    def __init__(self, isp_cmd=("wchisp", "flash")):
        from .link import MotorCtrlLink
        self._open = MotorCtrlLink
        self.link = MotorCtrlLink()
        self.isp_cmd = list(isp_cmd)
        self._until = 0.0

    def power(self, arm, what):
        r = self.link.ask("A %d %d" % (arm, what))
        if r[:2] != ["OK", "A"]:
            raise FlashError("motor_ctrl refused A %d %d: %s" % (arm, what, " ".join(r)))

    def window(self, arm, cycle):
        r = self.link.ask("U %d %d %d" % (arm, self.window_ms, int(cycle)))
        if r[:2] != ["OK", "U"]:
            raise FlashError("motor_ctrl refused the flash window: %s" % " ".join(r))
        self._until = time.monotonic() + self.window_ms / 1000.0 + self.off_s + 0.5
        self.link.close()           # J4 is the lane now: the port is going away

    def isp(self, image: bytes):
        exe = shutil.which(self.isp_cmd[0])
        if not exe:
            raise FlashError("%s is not installed (installing it is the user's call)" % self.isp_cmd[0])
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
            f.write(image)
        while time.monotonic() < self._until - 1.0:
            if subprocess.run(self.isp_cmd + [f.name]).returncode == 0:
                return
            time.sleep(0.5)          # the ROM loader not enumerated yet
        raise FlashError("no ROM loader answered on the flash lane inside the window")

    def after_window(self):
        time.sleep(max(0.0, self._until - time.monotonic()))
        end = time.monotonic() + 10.0
        while True:
            try:
                self.link = self._open()
                return
            except Exception:
                if time.monotonic() > end:
                    raise
                time.sleep(0.5)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("arm", choices=sorted(ARM))
    a.add_argument("--slots", required=True, help="the arm's slots in chain order, e.g. 0,1,2,3,4,5")
    a.add_argument("--loader", help="the CAN loader (firmware/lever_sensor build/boot.bin), for blank boards")
    a.add_argument("--app", help="the application (build/lever.bin)")
    a.add_argument("--walk", action="store_true", help="only walk the chain and report")
    o = a.parse_args(argv)
    plan = [int(s) for s in o.slots.split(",")]
    bench = PiBench()
    try:
        if o.walk:
            order, silent = walk(bench, ARM[o.arm], plan)
            for i, h in enumerate(order):
                print("place %d  slot %-3s uid %08x  %s" % (i, h.slot, h.uid, "loader" if h.mode else "app"))
            print("stops at place %d: silent" % len(order) if silent else "every place answers")
        else:
            if not o.app:
                a.error("--app is needed to flash")
            flash_arm(bench, ARM[o.arm], plan, open(o.loader, "rb").read() if o.loader else None,
                      open(o.app, "rb").read())
    finally:
        bench.link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
