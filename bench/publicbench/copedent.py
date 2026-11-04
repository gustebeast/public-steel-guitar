"""The copedent, on the Pi: the music (copedent.json) and every string's calibration, compiled into
the table motor_ctrl plays from (firmware/motor_ctrl/play.h). docs/control-path.md says why the
split falls there.

    python3 -m publicbench.copedent              the default copedent, as the board will play it
    python3 -m publicbench.copedent --out t.bin  ...and the table, ready to write down
    python3 -m publicbench.copedent --write      ...written to motor_ctrl, which plays from it

A curve is a string's motor counts from open pitch at each knot (KNOT_LO, every KNOT_CENTS).
model_curve() is the placeholder until tuning measures one: the pitch-range model of
src/dimensions.py (stretch DL_OPEN at open pitch, tension as pitch squared, so travel =
DL_OPEN * (2^(cents/600) - 1)) through the 2 mm screw and the 1:1 belt. The same DL_OPEN for every
string is a guess; the measured curve replaces it string by string.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import zlib

from . import servo

PLAY_H = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "motor_ctrl", "play.h")
DEFAULT = os.path.join(os.path.dirname(__file__), "copedent.json")

DL_OPEN_MM = 4.0                                    # src/dimensions.py DL_OPEN
SCREW_LEAD_MM = 2.0                                 # src/dimensions.py SCREW_PITCH, single start
COUNTS_PER_MM = servo.COUNTS_PER_TURN / SCREW_LEAD_MM   # PULLEY_TEETH on both: 1:1


def constants(path: str = PLAY_H) -> dict[str, int]:
    out = {}
    for m in re.finditer(r"#define\s+(\w+)\s+\(?(-?(?:0x[0-9A-Fa-f]+|\d+))u?\)?", open(path).read()):
        out[m.group(1)] = int(m.group(2), 0)
    return out


K = constants()
STRINGS, SLOTS, KNOTS = K["PLAY_STRINGS"], K["PLAY_SLOTS"], K["PLAY_KNOTS"]
KNOT_CENTS = [K["KNOT_LO"] + k * K["KNOT_CENTS"] for k in range(KNOTS)]
_HEAD = "<IHHB3xI%dB2x" % STRINGS
SIZE = struct.calcsize(_HEAD) + 2 * SLOTS * STRINGS + 4 * STRINGS * KNOTS + 4


def load(path: str = DEFAULT) -> dict:
    c = json.load(open(path))
    slots = [k["slot"] for k in c["controls"]]
    assert len(set(slots)) == len(slots) and all(0 <= s < SLOTS for s in slots), slots
    assert len(c["open"]) == STRINGS
    for k in c["controls"]:
        assert all(1 <= int(n) <= STRINGS for n in k["moves"]), k
    return c


def cents_table(cop: dict) -> list[list[int]]:
    """[slot][string index]: cents at full travel."""
    t = [[0] * STRINGS for _ in range(SLOTS)]
    for k in cop["controls"]:
        for n, st in k["moves"].items():
            t[k["slot"]][int(n) - 1] = round(100 * st)      # string N = index + 1
    return t


def model_curve(dl_open_mm: float = DL_OPEN_MM) -> list[int]:
    return [round(dl_open_mm * (2 ** (c / 600.0) - 1) * COUNTS_PER_MM) for c in KNOT_CENTS]


def compile_table(cop: dict, curves=None, motors=None, rpm: int = 3000, acc: int = 0,
                  min_us: int = 4000) -> bytes:
    """play_table_t, as motor_ctrl keeps it. motors[i]: string i+1's CAN id (default i+1)."""
    curves = curves or [model_curve()] * STRINGS
    motors = motors or list(range(1, STRINGS + 1))
    assert len(curves) == STRINGS and all(len(c) == KNOTS for c in curves)
    assert all(c[KNOT_CENTS.index(0)] == 0 for c in curves), "a curve is 0 at open pitch"
    body = struct.pack(_HEAD, K["PLAY_MAGIC"], K["PLAY_VERSION"], rpm, acc, min_us, *motors)
    body += struct.pack("<%dh" % (SLOTS * STRINGS), *sum(cents_table(cop), []))
    body += struct.pack("<%di" % (STRINGS * KNOTS), *sum((list(c) for c in curves), []))
    body += struct.pack("<I", zlib.crc32(body))
    assert len(body) == SIZE
    return body


def _tdiv(a: int, b: int) -> int:
    """C's integer division: toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


# ---- what the board will do with it: play.c, again, for tests and for the tuning UI ----------
def pitch(cents_t, pos: dict[int, float], s: int) -> int:
    """Cents above open for string index s with the controls at pos {slot: 0..1}: the largest
    raise plus the largest lower (play.h)."""
    full = K["PLAY_POS_FULL"]
    vs = [int(round(pos.get(c, 0.0) * full)) * cents_t[c][s] for c in range(SLOTS)]
    vs = [_tdiv(v, full) for v in vs]
    return max([0] + vs) + min([0] + vs)


def counts(curve, cents: int) -> int:
    x = cents - K["KNOT_LO"]
    if x <= 0:
        return curve[0]
    k = x // K["KNOT_CENTS"]
    if k >= KNOTS - 1:
        return curve[-1]
    return curve[k] + _tdiv((curve[k + 1] - curve[k]) * (x % K["KNOT_CENTS"]), K["KNOT_CENTS"])


def write(link, table: bytes, chunk: int = 32) -> list[str]:
    """Into motor_ctrl's flash through its line protocol (main.c 'P W', 'P S'); it plays from
    the new table at once and keeps every string's base. Returns its 'P' status line."""
    assert len(table) == SIZE
    for off in range(0, SIZE, chunk):
        r = link.ask("P W %d %s" % (off, table[off:off + chunk].hex()))
        if r[:2] != ["OK", "P"]:
            raise RuntimeError("table write refused at %d: %s" % (off, " ".join(r)))
    r = link.ask("P S", timeout=2.0)
    if r != ["OK", "P", "S"]:
        raise RuntimeError("the board did not keep the table: %s" % " ".join(r))
    st = link.ask("P")
    if int(st[5], 16) != zlib.crc32(table[:-4]):
        raise RuntimeError("the board plays a different table: %s" % " ".join(st))
    return st


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("copedent", nargs="?", default=DEFAULT)
    a.add_argument("--out")
    a.add_argument("--write", action="store_true", help="to motor_ctrl, through its serial link")
    o = a.parse_args(argv)
    cop = load(o.copedent)
    t = cents_table(cop)
    print(cop["name"])
    print("      " + " ".join("%5s" % ("s%d" % (i + 1)) for i in range(STRINGS)))
    for k in cop["controls"]:
        print("%-5s " % k["name"] + " ".join("%+5d" % v if v else "    ." for v in t[k["slot"]]))
    print("open  " + " ".join("%5s" % n for n in cop["open"]))
    print("curve (model, every string): " + ", ".join("%+d c %+d" % (c, n) for c, n in
                                                      zip(KNOT_CENTS[::4], model_curve()[::4])))
    if o.out:
        open(o.out, "wb").write(compile_table(cop))
        print("wrote %s, %d bytes" % (o.out, SIZE))
    if o.write:
        from .link import MotorCtrlLink
        link = MotorCtrlLink()
        try:
            st = write(link, compile_table(cop))
            print("motor_ctrl: table %s, playing %s, strings %s" % (st[5], st[2], st[4]))
        finally:
            link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
