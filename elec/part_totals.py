"""How many of each part does ONE INSTRUMENT need? Derived from the fab packages.

    py -3.12 elec/part_totals.py            -- every part, most numerous first
    py -3.12 elec/part_totals.py XH         -- only parts whose value matches XH

⚠ WHY THIS EXISTS. BOM.md is the document somebody orders from, and its quantities are
typed by hand. Checked against the packages on 2026-09-19, its connector rows were wrong
in four different ways at once:

  * S8B-XH-A -- the single most numerous connector in the instrument at 21 (10 CAN tees
    + 11 sensor boards) -- DOES NOT APPEAR IN BOM.md AT ALL. It is also the second
    tightest part in the catalogue by stock-over-demand.
  * S4B-XH-A, 10 per instrument, likewise absent.
  * "XH header, SMT side-entry ... 8 ... Sensor boards only" -- the sensor board stopped
    using that part when its connector became an S8B; the only user now is the OPTICAL
    board, and it needs ONE.
  * "XH headers, THT top-entry, B2B/B4B/B6B-XH-A, ~30" -- actually 6 B4B and 1 B2B, and
    there is no B6B anywhere in the design.

None of that is visible from inside BOM.md, and nothing compared it to the boards. A
quantity in prose has the same problem as a status in prose: it reads as current.

⚠ THE PACKAGES ARE THE SOURCE, NOT THE GENERATORS. It counts DESIGNATORS in each built
fab BOM and multiplies by that board's qty_per_instrument, so what it reports is what
would actually be ordered. A board whose package has not been rebuilt is reported as
stale rather than counted, because counting it would be a claim about a board that no
longer exists.
"""
from __future__ import annotations

import collections
import csv
import glob
import io
import json
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
FAB_DIR = os.path.join(OUT_DIR, "fab")


def totals():
    """{value: (per_instrument, {board: on_that_board})}, plus a list of complaints."""
    per = collections.defaultdict(int)
    where = collections.defaultdict(dict)
    notes = []
    for z in sorted(glob.glob(os.path.join(FAB_DIR, "*.zip"))):
        board = os.path.splitext(os.path.basename(z))[0]
        bj = os.path.join(OUT_DIR, "%s.board.json" % board)
        if not os.path.isfile(bj):
            notes.append("%s.zip has no board.json -- not counted" % board)
            continue
        qty = json.load(open(bj, encoding="utf-8")).get("qty_per_instrument")
        if not qty:
            notes.append("%s declares no qty_per_instrument -- not counted" % board)
            continue
        if os.path.getmtime(z) < os.path.getmtime(bj):
            notes.append("%s.zip is OLDER than its board.json -- rebuild before "
                         "trusting these numbers" % board)
        zf = zipfile.ZipFile(z)
        names = [n for n in zf.namelist() if n.lower().endswith("bom.csv")]
        if not names:
            notes.append("%s.zip carries no BOM csv -- not counted" % board)
            continue
        rows = csv.DictReader(io.StringIO(zf.read(names[0]).decode("utf-8-sig")))
        for r in rows:
            val = (r.get("Comment") or "").strip()
            n = len([d for d in (r.get("Designator") or "").split(",") if d.strip()])
            if not val or not n:
                continue
            per[val] += n * qty
            where[val][board] = n
    return per, where, notes


def main(argv):
    pat = argv[1].upper() if len(argv) > 1 else None
    per, where, notes = totals()
    for n in notes:
        print("  !! %s" % n)
    rows = [(v, k) for k, v in per.items() if not pat or pat in k.upper()]
    if not rows:
        print("no parts match %r" % pat)
        return 1
    print("\n%-34s %5s   on which boards" % ("PART", "QTY"))
    for v, k in sorted(rows, reverse=True):
        src = ", ".join("%s x%d" % (b, n) for b, n in sorted(where[k].items()))
        print("%-34s %5d   %s" % (k[:34], v, src))
    print("\n%d distinct part value(s); quantities are PER INSTRUMENT" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
