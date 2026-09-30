"""Does BOM.md name the same part as the board, for every designator it lists?

    py -3.12 elec/bom_check.py

⚠ BOM.md IS THE ONLY DOCUMENT IN THIS PROJECT NOTHING CHECKED. The netlist is checked
against the schematic, the board against the netlist, the copper against DRC, the
budgets against verify.py -- and the table somebody ORDERS FROM was typed by hand and
compared to nothing. Run for the first time on 2026-09-19 it found, on the optical
board's table alone:

  * J2 `S6B-XH-SM4-TB` -- the connector from before the optical feed became TWO WIRES.
    The row still listed 2x5V, 2xPWR_GND, AUDIO and AUDIO_GND; the board wires PWR_GND
    and +24V and declares ways 3-4 no-connect. It is an S4B now.
  * U11 `TLV9061IDCKR` against C693480 -- a code THIS SAME FILE elsewhere records as
    having been caught being a P6KE39CA TVS DIODE. A known-bad part number left sitting
    in the parts table, which is the exact failure the note about it was written for.
  * FB1 `GZ2012D601TF` -- the 0805 body, where the board places a 0603.

A wrong part number in this table does not fail any gate: it fails at the bench, after
somebody has paid for the wrong part and waited for it.

⚠ A DESIGNATOR IS ONLY UNIQUE WITHIN ITS BOARD, AND THE FIRST VERSION OF THIS FORGOT.
It matched every row against every board, so optical's U1 (a TLV9064 TIA) was compared to
motor_ctrl's U1 (an LMR16006 buck) and reported as an error. Sixteen findings, all false,
and they looked exactly like the three real ones above. A table is now tied to the board
whose heading precedes it, and a row is only checked against that board.

⚠ IT COMPARES DESIGNATORS, WHICH IS WHAT MAKES IT CHEAP AND ALSO WHAT LIMITS IT. It only
looks at rows shaped "| DES | PART | Cxxxx | qty |", and only where that
designator exists on that board. A row for a part the boards do not place at all, or a
part placed with no row anywhere, is a different question -- elec/part_totals.py answers
that one, and it found six sourced parts with no row in this file.
"""
from __future__ import annotations

import csv
import glob
import io
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FAB_DIR = os.path.join(HERE, "out", "fab")
ROW = re.compile(r"\|\s*([A-Z]+[0-9]+[^|]*?)\s*\|\s*`([^`]+)`\s*\|\s*(C\d+)\s*\|\s*(\d+)\s*\|")


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def board_parts(zip_path):
    """{designator: value} from a built fab package."""
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if n.lower().endswith("bom.csv")]
    if not names:
        return {}
    out = {}
    for r in csv.DictReader(io.StringIO(z.read(names[0]).decode("utf-8-sig"))):
        val = (r.get("Comment") or "").strip()
        for d in (r.get("Designator") or "").split(","):
            if d.strip():
                out[d.strip()] = val
    return out


def check(bom_path=None):
    bom_path = bom_path or os.path.join(ROOT, "BOM.md")
    lines = io.open(bom_path, encoding="utf-8").read().split("\n")
    boards = [os.path.splitext(os.path.basename(z))[0]
              for z in sorted(glob.glob(os.path.join(FAB_DIR, "*.zip")))]
    # A row belongs to the board named by the nearest heading or generator path above it.
    rows, owner = {}, None
    for i, line in enumerate(lines, 1):
        hit = [b for b in boards
               if b in line or b.replace("_", " ") in line.lower()]
        if line.lstrip().startswith("#") or "elec/" in line:
            if hit:
                owner = hit[0]
        m = ROW.match(line)
        if m and owner:
            # "PD1A-PD10B" and "U1-U5" name a range; the first designator identifies it
            des = re.split(r"[–—-]", m.group(1))[0].strip()
            rows.setdefault(owner, {})[des] = (m.group(2), m.group(3), i)

    bad = []
    seen = 0
    for z in sorted(glob.glob(os.path.join(FAB_DIR, "*.zip"))):
        board = os.path.splitext(os.path.basename(z))[0]
        mine = rows.get(board, {})
        for des, val in board_parts(z).items():
            if des not in mine:
                continue
            seen += 1
            part, code, line = mine[des]
            a, b = _norm(part), _norm(val)
            if a not in b and b not in a:
                bad.append((board, des, part, code, val, line))
    return bad, seen, sum(len(v) for v in rows.values())


def main():
    bad, seen, nrows = check()
    print("BOM.md: %d designator row(s); %d matched against a built board" % (nrows, seen))
    if not bad:
        print("every row names the part its board actually places")
        return 0
    print("\n*** %d ROW(S) NAME A DIFFERENT PART THAN THE BOARD ***" % len(bad))
    for board, des, part, code, val, line in bad:
        print("   BOM.md:%-5d %-6s %-22s %-10s  but %s places %s"
              % (line, des, part, code, board, val))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
