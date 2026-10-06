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
    stem = board                                      # fret_led_mid/key share one generator,
    while not os.path.isfile(src) and "_" in stem:    # and leg_pogo_female_top is two deep
        stem = stem.rsplit("_", 1)[0]
        src = os.path.join(ROOT, "elec", "%s.py" % stem)
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
    # of the board, so the constant lives with the geometry -- a board count can be
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


def tht_joints(geom, prices):
    """Through-hole PINS and PART COUNT on one board. JLCPCB bills both, separately:
    hand-soldering per pin, then Manual Assembly per part placed.

    Worth separating because the live quote form bills hand-soldering on its own line.
    Most of our JST parts are the -SM4-TB / -SRSS-TB surface-mount variants and do NOT
    count; what does is the XH A-series, the PH B*B-PH-K, headers, and the panel jacks."""
    b = prices["boards"]
    keys = b.get("tht_footprints", [])
    fallback = b.get("tht_pins_fallback", {})
    pins = parts = 0
    for fp in geom.get("footprints", []):
        fpid = str(fp.get("fpid", fp.get("footprint", "")))
        if not any(k in fpid for k in keys):
            continue
        m = re.search(r"(\d+)x(\d+)", fpid)
        if m:
            pins += int(m.group(1)) * int(m.group(2))
        else:
            pins += next((v for k, v in fallback.items() if k in fpid), 2)
        parts += 1
    return pins, parts


def board_fab_cost(geom, layers, boards_in_order, prices):
    """Fab + assembly for ONE board type across the whole ten-instrument order.

    Fab is fitted to MEASURED JLCPCB quotes (prices.json boards.fab_quotes), not to a
    per-board rate. The distinction is the whole correction: JLCPCB prices a BATCH. The
    first version of this charged a $2.00 minimum per board and came to $200 for a
    hundred tee boards that really quote $16.60."""
    b = prices["boards"]
    w, h = geom["outline_mm"][0], geom["outline_mm"][1]
    area_cm2 = (w * h) / 100.0
    m = b["fab_quotes"]["model"]
    if layers >= 4:
        k = m["4"]
    elif max(w, h) <= 100.0:
        k = m["2_small"]                 # inside JLCPCB's cheap bracket, and it shows
    else:
        k = m["2_long"]
    fab = k["base"] + k["area_rate"] * area_cm2
    if boards_in_order > 10:
        fab += k["per_extra_board"] * (boards_in_order - 10)
    n_parts = len(geom.get("footprints", []))
    tht_pins, tht_parts = tht_joints(geom, prices)
    smt_joints = (n_parts - tht_parts) * 2              # a rough two joints per SMT part
    asm = (b["assembly_per_joint_usd"] * smt_joints
           + b["hand_solder_per_joint_usd"] * tht_pins
           + b["manual_assembly_per_tht_part_usd"] * tht_parts) * boards_in_order
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
        if (part.startswith("test_") or part.startswith("coil_mandrel")
                or part.endswith("_light") or part == "assembly"):
            continue                    # coupons, the viewer's lightweight chassis, and
            # TOOLING. The mandrel and its sleeve are what you wind the knee-lever coils
            # ON, not anything that ships inside the instrument -- 47 cm3 of print that
            # was showing up under a material of "?" because it has no material folder.
            # Shop infrastructure is bought once and never weighed against a design
            # (user's standing rule), so it does not belong in a per-instrument cost.
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
    parts_usd = fab_usd = asm_usd = fees_usd = 0.0
    order_fees = prices["boards"].get("order_fees", {})
    setup = float(prices["boards"]["assembly_setup_usd"])
    stencil = float(prices["boards"]["assembly_stencil_usd"])
    designs = 0
    for board, geom in sorted(geoms.items()):
        if board in ("optalt", "led_strip"):
            # optalt is an alternative, not fitted. led_strip is SUPERSEDED (brenner,
            # 2026-10-01): one instrument carries the two foot boards + the two fret boards and
            # nothing else lights it. It was being priced at ~$29 an instrument for as
            # long as its geom file sat in elec/geom.
            continue
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
        designs += 1                                   # setup and stencil are PER DESIGN
        # fees read on the fab's quote that no rate produces: per design, per order
        fees = sum(float(f["usd"]) for f in order_fees.get(board, [])
                   if keep or f.get("verified") == "v")
        fees_usd += fees
        if unp:
            unpriced_all.append((board, unp))
        if a.detail:
            w, h = geom["outline_mm"][:2]
            print("  %-14s x%-3d %3d parts %6.1fx%-6.1f mm %dL  parts $%6.2f  fab $%6.2f  asm $%5.2f  fees $%6.2f"
                  % (board, qty, len(geom.get("footprints", [])), w, h, layers,
                     p_each * in_order, fab, asm, fees))
    per_order_asm = (setup + stencil) * designs
    boards_total = (parts_usd + fab_usd + asm_usd + per_order_asm + fees_usd) / ORDER_INSTRUMENTS
    notes.append("QUOTED FEES are $%.2f of the PCB line: extended-part fees, the Standard "
                 "assembly tier on three boards, one via charge -- boards.order_fees. "
                 "Boards with no entry there (%s) have not had theirs entered."
                 % (fees_usd / ORDER_INSTRUMENTS,
                    ", ".join(sorted(b for b in geoms if b not in order_fees
                                     and b not in ("optalt", "led_strip"))) or "none"))
    notes.append("ASSEMBLY is $%.2f of the $%.2f PCB line. The RATES are measured (one "
                 "real JLCPCB PCBA quote, can_tee, Economic, qty 50) and the model "
                 "reproduces that quote to 1%%. What is NOT modelled is the edge-rail "
                 "cliff on small boards at high quantity -- see boards.rails_note, it is "
                 "worth more than this whole line on can_tee and lever_sensor."
                 % ((asm_usd + per_order_asm) / ORDER_INSTRUMENTS, boards_total))
    groups.append(("PCBs: parts + fab + assembly (%d instruments / %d)"
                   % (ORDER_INSTRUMENTS, ORDER_INSTRUMENTS), boards_total))

    # ---- purchased ----------------------------------------------------------
    for label, key in (("Mechanical hardware", "mechanical"),
                       ("Purchased modules", "modules"),
                       ("Connectors: housings + crimps", "connectors")):
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

    # ---- landed: freight, sales tax, duty -----------------------------------
    # A price on a product page is not what the money costs. These are measured at
    # real checkouts with the real address (elec/prices.json "landed"), and they are
    # per ORDER, so they divide by the order like everything else. Anything already
    # folded into a unit price elsewhere is skipped -- see counted_in_unit_price.
    landed_usd, landed_seen, landed_partial = 0.0, [], []
    for vend, ent in sorted(prices.get("landed", {}).items()):
        if vend.startswith("_"):
            continue
        if ent.get("counted_in_unit_price"):
            continue
        got = [ent.get(k) for k in ("shipping_usd", "tax_usd", "tariff_usd")]
        if all(v is None for v in got):
            landed_partial.append(vend)
            continue
        if any(v is None for v in got[:2]):        # some of it measured, some not
            landed_partial.append(vend)
        landed_usd += sum(v for v in got if v is not None)
        landed_seen.append(vend)
    # Duty that a vendor does NOT collect at checkout is real money and an unknown
    # amount of it. It is kept OUT of the total -- a bound is not a measurement --
    # and printed as its own worst case underneath, so it cannot be quietly forgotten.
    exposure = sum(float(e["tariff_unpriced_upper_usd"])
                   for k, e in prices.get("landed", {}).items()
                   if not k.startswith("_") and e.get("tariff_unpriced_upper_usd"))
    exposure /= ORDER_INSTRUMENTS
    landed_usd /= ORDER_INSTRUMENTS
    groups.append(("Shipping + sales tax + duty (%d vendor%s measured)"
                   % (len(landed_seen), "" if len(landed_seen) == 1 else "s"), landed_usd))
    notes.append("The LANDED line is %d measured vendor checkout(s): %s. It is a FLOOR. "
                 "Nobody has measured freight or tax on the PCTG and TPU filament or on the listing-priced "
                 "mechanical hardware (~$213/instrument), most of which records no vendor "
                 "at all. The duty on the China-shipped motors is not in it either: it is "
                 "a BOUND, printed as the worst-case line under the total -- see "
                 "landed.makerbase_motors and missing.landed_gaps.%s"
                 % (len(landed_seen), ", ".join(landed_seen),
                    ("  PARTIAL: " + ", ".join(landed_partial)) if landed_partial else ""))

    # ---- the table ----------------------------------------------------------
    width = max(len(g) for g, _ in groups)
    print()
    print("PER-INSTRUMENT COST" + ("  (verified prices only)" if a.verified else ""))
    print("-" * (width + 12))
    for g, usd in groups:
        print("%-*s  $%8.2f" % (width, g, usd))
    print("-" * (width + 12))
    total = sum(u for _, u in groups)
    print("%-*s  $%8.2f" % (width, "TOTAL", total))
    if exposure:
        print("%-*s  $%8.2f" % (width, "  + worst-case uncollected duty (a BOUND, see below)",
                                exposure))
        print("%-*s  $%8.2f" % (width, "TOTAL, worst case", total + exposure))

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
