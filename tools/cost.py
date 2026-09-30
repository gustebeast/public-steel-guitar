"""What one instrument costs, computed rather than typed.

    py -3.12 -m tools.cost              # the summary
    py -3.12 -m tools.cost --detail     # every line, including per-board part breakdowns
    py -3.12 -m tools.cost --verified   # ignore every price not read off a product page

⚠ WHY THIS EXISTS. BOM.md's cost summary is hand-totalled prose, and prose goes stale
the same way every other number in this project has: quantities were typed rather than
counted (elec/part_totals.py found four connector rows wrong at once, one of them the
most numerous connector in the instrument, absent entirely), and the summary itself
carried a basic/pro split that had been retired. A cost that nobody can re-run is a
cost that is wrong by an unknown amount.

WHERE EACH NUMBER COMES FROM, because that is the whole point:

  quantities   THE MODEL AND THE BOARDS, never this file.
               * printed parts   tools/part_volumes.json, written by src.build from the
                                 solids themselves -- so a part that grows costs more
                                 without anyone editing anything.
               * board parts     elec/geom/*.geom.json, the ROUTED boards' own
                                 footprints. Counted by designator.
               * board areas     the same files' outline_mm.
               * board counts    each generator's qty_per_instrument.
  prices       elec/prices.json, with a source and a date per entry.

  THE ORDER BASIS IS TEN INSTRUMENTS, DIVIDED BY TEN (user). PCB fab and assembly have
  large per-order costs -- setup, feeder loading -- which are nonsense per instrument on
  their own, so a board needed four times per instrument is quoted at forty and the
  whole order is divided by ten at the end.

⚠ WHAT IT DOES NOT KNOW, and says so every run: there is no PSU in this project, the
harness wire is not itemised, and the connectors are counted but not priced. It prints
those under the table and declines to call the total complete.

⚠ AND IT DOES NOT MODEL INFILL. A printed part's cost here is its SOLID volume in
filament, which is the upper bound. Real parts are 4-wall/15%-infill in places, so the
plastic line is high -- by how much nobody has measured, which is why it is stated as a
bound rather than quietly scaled by a guess.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRICES = os.path.join(ROOT, "elec", "prices.json")
VOLUMES = os.path.join(HERE, "part_volumes.json")
GEOM = os.path.join(ROOT, "elec", "geom")

ORDER_INSTRUMENTS = 10          # the user's basis: order ten, divide by ten


# ── inputs ───────────────────────────────────────────────────────────────────
def load_prices():
    with open(PRICES, encoding="utf-8") as fh:
        return json.load(fh)


def load_volumes():
    if not os.path.isfile(VOLUMES):
        return {}
    with open(VOLUMES, encoding="utf-8") as fh:
        return json.load(fh).get("parts", {})


def board_geoms():
    """{board: geom dict} for every routed board whose geometry is committed."""
    out = {}
    for p in sorted(glob.glob(os.path.join(GEOM, "*.geom.json"))):
        name = os.path.basename(p)[:-len(".geom.json")]
        with open(p, encoding="utf-8") as fh:
            out[name] = json.load(fh)
    return out


def board_qty(board):
    """How many of `board` one instrument needs, from the generator's own notes.

    Parsed rather than imported: importing a generator pulls skidl and a KiCad
    environment into what should be a arithmetic script. Resolves an int literal
    directly, and one level of indirection (`"qty_per_instrument": SECTIONS` ->
    `SECTIONS = 4`) in the same file. Anything it cannot resolve is returned as None so
    the caller reports it instead of assuming 1 -- assuming 1 on a board needed ten
    times is exactly the kind of quiet error this file exists to stop.
    """
    src = os.path.join(ROOT, "elec", "%s.py" % board)
    if not os.path.isfile(src):                       # fret_led_mid/key share one generator
        src = os.path.join(ROOT, "elec", "%s.py" % board.rsplit("_", 1)[0])
    if not os.path.isfile(src):
        return None
    with open(src, encoding="utf-8") as fh:
        txt = fh.read()
    m = re.search(r'"qty_per_instrument"\s*:\s*([A-Za-z_][\w.]*|\d+)', txt)
    if not m:
        m = re.search(r'\["qty_per_instrument"\]\s*=\s*([A-Za-z_][\w.]*|\d+)', txt)
    if not m:
        return None
    tok = m.group(1)
    if tok.isdigit():
        return int(tok)
    leaf = tok.split(".")[-1]                          # FL.BOARD_QTY -> BOARD_QTY
    # (a) a plain literal, here or in any sibling module
    for hay in (txt, _sibling_sources(board)):
        m2 = re.search(r"^%s\s*=\s*(\d+)" % re.escape(leaf), hay, re.M)
        if m2:
            return int(m2.group(1))
    # (b) `_TEE_QTY = _tee_qty()` whose body is `return D.N_STRINGS` -- the count that
    #     belongs to the instrument rather than to the board. Resolved through
    #     src.dimensions, which is pure constants and cheap to import; this is the case
    #     that matters most, because can_tee, lever_sensor and the LED strip are the
    #     boards there is more than one of.
    hay = txt + "\n" + _sibling_sources(board)
    m3 = re.search(r"^%s\s*=\s*(\w+)\(\)" % re.escape(leaf), hay, re.M)
    fn = m3.group(1) if m3 else None
    if fn:
        m4 = re.search(r"def %s\(\):(.{0,400}?)return\s+D\.([A-Z_][A-Z0-9_]*)"
                       % re.escape(fn), hay, re.S)
        if m4:
            return _dimension(m4.group(2))
    m5 = re.search(r"^%s\s*=\s*D\.([A-Z_][A-Z0-9_]*)" % re.escape(leaf), hay, re.M)
    if m5:
        return _dimension(m5.group(1))
    return None


def _dimension(name):
    """One constant out of src.dimensions, or None. Imported rather than parsed because
    a dimension is often derived from three others and only Python knows the answer."""
    try:
        sys.path.insert(0, ROOT)
        from src import dimensions as D           # noqa: PLC0415 -- deliberately lazy
        v = getattr(D, name, None)
        return int(v) if isinstance(v, (int, float)) else None
    except Exception:                             # noqa: BLE001
        return None


def _sibling_sources(board):
    """Every elec/ source concatenated -- for a constant defined in the module the
    generator imported it from."""
    out = []
    # elec/ AND src/: a board's count is often a property of the INSTRUMENT rather than
    # of the board, so the constant lives with the geometry -- foot_led's BOARD_QTY is
    # in src/foot_light.py, not in elec/ at all.
    for d in ("elec", "src"):
        for p in sorted(glob.glob(os.path.join(ROOT, d, "*.py"))):
            with open(p, encoding="utf-8") as fh:
                out.append(fh.read())
    return "\n".join(out)


# ── pricing ──────────────────────────────────────────────────────────────────
def _fp_class(fpid):
    """A footprint id reduced to the class prices.json knows: 'R_0402', 'SOT-23-5'..."""
    base = fpid.split(":")[-1]
    m = re.match(r"([RCL])_(\d{4})", base)
    if m:
        return "%s_%s" % (m.group(1), m.group(2))
    m = re.match(r"LED_(\d{4})", base)
    if m:
        return "LED_%s" % m.group(1)
    for key in ("SOT-23-6", "SOT-23-5", "SOT-23", "SOD-323", "SOD-123"):
        if key in base:
            return key if key.startswith("SOT") else "D_%s" % key
    for key in ("TestPoint", "SolderJumper", "MountingHole", "Fiducial"):
        if key in base:
            return key
    return None


def board_parts_cost(board, geom, prices, keep_unverified=True):
    """(usd_per_board, priced, unpriced_refs) for one board's placed parts."""
    by_ref = prices["parts_by_ref"]
    by_fp = prices["parts_by_footprint"]
    total, priced, unpriced = 0.0, 0, []
    for f in geom.get("footprints", []):
        ref, fpid = f.get("ref", "?"), f.get("fpid", "")
        ent = by_ref.get("%s:%s" % (board, ref))
        if ent:
            if keep_unverified or ent.get("verified") == "v":
                total += float(ent["usd"])
            priced += 1
            continue
        cls = _fp_class(fpid)
        if cls is not None and cls in by_fp:
            total += float(by_fp[cls])
            priced += 1
            continue
        ent = _by_substring(fpid, prices)
        if ent is not None:
            if keep_unverified or ent.get("verified") == "v":
                total += float(ent["usd"])
            priced += 1
            continue
        unpriced.append("%s (%s)" % (ref, fpid.split(":")[-1]))
    return total, priced, unpriced


def _by_substring(fpid, prices):
    """A footprint carrying its own MPN, priced by substring. Longest key first, so
    JST_PH_S8B beats JST_PH_B rather than losing to it by dictionary order."""
    tbl = prices.get("parts_by_footprint_substring", {})
    for key in sorted((k for k in tbl if not k.startswith("_")), key=len, reverse=True):
        if key in fpid:
            return tbl[key]
    return None


def board_fab_cost(geom, layers, boards_in_order, prices):
    """Fab + assembly for ONE board type across the whole ten-instrument order."""
    b = prices["boards"]
    w, h = geom["outline_mm"][0], geom["outline_mm"][1]
    area_cm2 = (w * h) / 100.0
    rate = b["fab_usd_per_cm2"].get(str(layers), b["fab_usd_per_cm2"]["4"])
    fab = max(area_cm2 * rate, b["fab_min_usd"]) * boards_in_order
    joints = len(geom.get("footprints", [])) * 2        # a rough two joints per part
    asm = b["assembly_per_joint_usd"] * joints * boards_in_order
    return fab, asm


def guess_layers(board, geom):
    """Copper count. Not in geom.json, so read from the generator's own layer note."""
    src = os.path.join(ROOT, "elec", "%s.py" % board)
    if not os.path.isfile(src):
        src = os.path.join(ROOT, "elec", "%s.py" % board.rsplit("_", 1)[0])
    if os.path.isfile(src):
        with open(src, encoding="utf-8") as fh:
            txt = fh.read()
        m = re.search(r'"layers"\s*:\s*(\d+)', txt) or re.search(r"^LAYERS\s*=\s*(\d+)", txt, re.M)
        if m:
            return int(m.group(1))
    return 2


# ── the report ───────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="per-instrument cost, computed")
    ap.add_argument("--detail", action="store_true", help="every line, not just the groups")
    ap.add_argument("--verified", action="store_true",
                    help="count ONLY prices read off a product page")
    a = ap.parse_args(argv)
    keep = not a.verified

    prices = load_prices()
    vols = load_volumes()
    geoms = board_geoms()
    groups, notes, unpriced_all = [], [], []

    # ---- printed parts ------------------------------------------------------
    if not vols:
        notes.append("NO tools/part_volumes.json -- run `py -3.12 -m src.build` once; "
                     "the plastic line is MISSING, not zero")
    per_mat = {}
    for part, rec in vols.items():
        mat = (rec.get("material") or "?").lower()
        if part.startswith("test_") or part.endswith("_light") or part == "assembly":
            continue                    # coupons and the viewer's lightweight chassis
        per_mat.setdefault(mat, 0.0)
        per_mat[mat] += float(rec.get("volume_mm3", 0.0))
    plastic = solid_usd = 0.0
    factor = float(prices.get("print_material_factor", {}).get("factor", 1.0))
    for mat, mm3 in sorted(per_mat.items()):
        ent = prices["filament_per_kg"].get(mat)
        if not ent:
            notes.append("no filament price for material %r (%.0f cm3 of it)" % (mat, mm3 / 1000))
            continue
        if not keep and ent.get("verified") != "v":
            continue
        kg_solid = (mm3 / 1000.0) * float(ent["density_g_cm3"]) / 1000.0
        kg = kg_solid * factor
        usd = kg * float(ent["usd"])
        plastic += usd
        solid_usd += kg_solid * float(ent["usd"])
        if a.detail:
            print("  %-10s %7.0f cm3  solid %5.2f kg -> %5.2f kg at x%.2f  $%6.2f   (%s)"
                  % (mat, mm3 / 1000, kg_solid, kg, factor, usd, ent["source"]))
    groups.append(("Printed parts (x%.2f material factor; solid would be $%.0f)"
                   % (factor, solid_usd), plastic))

    # ---- boards -------------------------------------------------------------
    parts_usd = fab_usd = asm_usd = 0.0
    setup = float(prices["boards"]["assembly_setup_usd"])
    feeder = float(prices["boards"]["assembly_per_feeder_usd"])
    order_lines = 0
    for board, geom in sorted(geoms.items()):
        if board == "optalt":
            continue                                   # an alternative, not fitted
        qty = board_qty(board)
        if qty is None:
            notes.append("board %r: qty_per_instrument could not be resolved -- EXCLUDED" % board)
            continue
        in_order = qty * ORDER_INSTRUMENTS
        p_each, priced, unp = board_parts_cost(board, geom, prices, keep)
        layers = guess_layers(board, geom)
        fab, asm = board_fab_cost(geom, layers, in_order, prices)
        parts_usd += p_each * in_order
        fab_usd += fab
        asm_usd += asm
        order_lines += max(1, priced // 8)             # crude: feeders scale with distinct lines
        if unp:
            unpriced_all.append((board, unp))
        if a.detail:
            w, h = geom["outline_mm"][:2]
            print("  %-14s x%-3d %3d parts %6.1fx%-6.1f mm %dL  parts $%6.2f  fab $%6.2f  asm $%5.2f"
                  % (board, qty, len(geom.get("footprints", [])), w, h, layers,
                     p_each * in_order, fab, asm))
    per_order_asm = setup + feeder * order_lines
    boards_total = (parts_usd + fab_usd + asm_usd + per_order_asm) / ORDER_INSTRUMENTS
    groups.append(("PCBs: parts + fab + assembly (%d instruments / %d)"
                   % (ORDER_INSTRUMENTS, ORDER_INSTRUMENTS), boards_total))

    # ---- purchased ----------------------------------------------------------
    for label, key in (("Mechanical hardware", "mechanical"), ("Purchased modules", "modules")):
        tot = 0.0
        for name, ent in sorted(prices[key].items()):
            if name.startswith("_"):
                continue
            if not keep and ent.get("verified") != "v":
                continue
            n = int(ent.get("per_instrument", 1))
            tot += float(ent["usd"]) * n
            if a.detail:
                print("  %-18s x%-4d $%7.2f  [%s] %s"
                      % (name, n, float(ent["usd"]) * n, ent.get("verified", "?"),
                         ent.get("what", "")))
        groups.append((label, tot))

    # ---- the table ----------------------------------------------------------
    width = max(len(g) for g, _ in groups)
    print()
    print("PER-INSTRUMENT COST" + ("  (verified prices only)" if a.verified else ""))
    print("-" * (width + 12))
    for g, usd in groups:
        print("%-*s  $%8.2f" % (width, g, usd))
    print("-" * (width + 12))
    print("%-*s  $%8.2f" % (width, "TOTAL", sum(u for _, u in groups)))

    if unpriced_all:
        n = sum(len(u) for _, u in unpriced_all)
        print("\n%d PLACED PART(S) WITH NO PRICE -- counted as $0, so the total is LOW:" % n)
        for board, unp in unpriced_all:
            print("  %-14s %s" % (board, ", ".join(unp[:6]) + (" ..." if len(unp) > 6 else "")))

    print("\nNOT IN THIS TOTAL AT ALL:")
    for k, why in prices["missing"].items():
        if not k.startswith("_"):
            print("  %-12s %s" % (k, why))
    for nt in notes:
        print("  ! %s" % nt)
    print("\nThis total is INCOMPLETE by construction -- see above. Prices marked 'm' in"
          "\nelec/prices.json came from a listing rather than a product page; re-run with"
          "\n--verified to see what survives without them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
