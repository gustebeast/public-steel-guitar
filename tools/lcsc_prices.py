"""Real JLCPCB component prices, at the quantity we would actually order.

    py -3.12 tools/lcsc_prices.py            # refresh elec/prices.json
    py -3.12 tools/lcsc_prices.py --dry      # show what would change, write nothing

WHY THIS EXISTS. elec/prices.json used to price a part by its FOOTPRINT CLASS -- a
WQFN-24 cost $1.90 because WQFN-24s cost about that. Measured against the catalogue
the error was not a rounding one: the TLV320ADC3140 in that package is $3.64 at our
quantity, so that single line was 92% low. A footprint is a shape, and shape does not
set price. The part number does, and we already record part numbers.

WHERE THE NUMBERS COME FROM. The same JLCPCB parts API that elec/lcsc_check.py uses to
check stock also returns the quantity-break table, which is the price that lands in a
PCBA quote. This asks for the break covering the quantity a TEN-INSTRUMENT ORDER needs
(tools/cost.py's basis), so a part used 11 times per instrument is priced at 110, not
at one. That matters: the breaks move 30-40% across the range.

WHAT IT CANNOT PRICE. Anything with no LCSC code in elec/fab.py -- generic passives,
mostly, where a shape really does set the price. Those stay on the footprint table and
are counted and reported rather than silently left stale.
"""
from __future__ import annotations

import argparse
import collections
import glob
import importlib.util
import io
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = ("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/"
       "selectSmtComponentList")
ORDER_INSTRUMENTS = 10


def lcsc_map():
    """{value string -> LCSC code}, read from elec/fab.py's own table."""
    src = io.open(os.path.join(ROOT, "elec", "fab.py"), encoding="utf-8").read()
    body = re.search(r"^LCSC = \{(.*?)^\}", src, re.S | re.M).group(1)
    return dict(re.findall(r'"([^"]+)":\s*"(C\d+)"', body))


def netlist_parts(path):
    """[(ref, value, footprint)] out of a KiCad netlist, without KiCad."""
    txt = io.open(path, encoding="utf-8", errors="replace").read()
    body = txt[txt.find("(components"):]
    out = []
    for blk in body.split("(comp\n")[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk)
        val = re.search(r'\(value "([^"]*)"\)', blk)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        desc = re.search(r'\(description "([^"]*)"\)', blk)
        # The description often carries the code outright ("... (LCSC C157914)"), which
        # is a second way in for a part whose value string is not fab.py's key.
        code = re.search(r"LCSC\s+(C\d+)", desc.group(1)) if desc else None
        out.append((ref.group(1) if ref else "?",
                    (val.group(1) if val else "").strip(),
                    (fp.group(1) if fp else "").strip(),
                    code.group(1) if code else None))
    return out


_COST = None


def board_qty(board):
    """Boards of this design in a ten-instrument order. Reuses cost.py's resolver."""
    global _COST
    if _COST is None:
        spec = importlib.util.spec_from_file_location(
            "cost", os.path.join(ROOT, "tools", "cost.py"))
        _COST = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_COST)
    q = _COST.board_qty(board)
    return None if q is None else q * ORDER_INSTRUMENTS


def price_at(code, qty, cache):
    """(unit price at qty, stock, model). The break table is inclusive on both ends."""
    if code not in cache:
        req = urllib.request.Request(API, data=json.dumps(
            {"keyword": code, "currentPage": 1, "pageSize": 3}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=30))
        rec = None
        for c in d["data"]["componentPageInfo"]["list"] or []:
            if c["componentCode"] == code:
                rec = {"breaks": c.get("componentPrices") or [],
                       "stock": c.get("stockCount"),
                       "model": c.get("componentModelEn")}
                break
        cache[code] = rec
        time.sleep(0.15)
    rec = cache[code]
    if not rec or not rec["breaks"]:
        return None, None, None
    best = None
    for b in sorted(rec["breaks"], key=lambda x: x["startNumber"]):
        end = b["endNumber"]
        if b["startNumber"] <= qty and (end == -1 or qty <= end):
            best = b["productPrice"]
    if best is None:                       # below the smallest break: pay the top rate
        best = max(b["productPrice"] for b in rec["breaks"])
    return float(best), rec["stock"], rec["model"]


# A board header implies its MATING HALF, and no netlist contains one -- a harness is
# not a schematic. So they are DERIVED: every JST header needs one housing plus one crimp
# contact per way. That is why "connectors" sat in cost.py's not-counted-at-all list.
#
# Housings are picked by stock as well as by name: the genuine JST SHR-04V-S-B had ONE
# piece in the catalogue on 2026-09-30, so the SH row is the stocked HC-1.0-4Y instead.
HOUSING = {("XH", 2): "C144401", ("XH", 4): "C493083", ("XH", 8): "C144407",
           ("PH", 6): "C157952", ("PH", 8): "C157950", ("SH", 4): "C2962275",
           # VH: not on any board yet. Listed ahead of bronner's proposed 2-way power tap
           # on the CAN tee (docs/can-tee-power-tap.md) so that the day the header lands,
           # its mating half is priced instead of silently missing.
           ("VH", 2): "C595405"}
CRIMP = {"XH": "C140573", "PH": "C111515", "SH": "C263995", "VH": "C160350"}


def mating_halves():
    """{LCSC code -> pieces in a ten-instrument order} for housings and crimps."""
    need = collections.Counter()
    for path in sorted(glob.glob(os.path.join(ROOT, "elec", "out", "*.net"))):
        board = os.path.basename(path)[:-4]
        n = board_qty(board)
        if n is None:
            continue
        for ref, val, fp, code in netlist_parts(path):
            m = re.search(r"JST_(XH|PH|SH|VH)_.*?(\d+)x(\d+)", fp)
            if not m:
                continue
            fam, ways = m.group(1), int(m.group(2)) * int(m.group(3))
            key = HOUSING.get((fam, ways))
            if key is None:                    # a way-count with no housing chosen yet
                continue
            need[key] += n
            need[CRIMP[fam]] += n * ways
    return need


def collect():
    """(demand, used, unpriceable) across every netlist in elec/out."""
    codes = lcsc_map()
    demand = collections.Counter()
    used = collections.defaultdict(list)
    unpriceable = collections.Counter()
    for path in sorted(glob.glob(os.path.join(ROOT, "elec", "out", "*.net"))):
        board = os.path.basename(path)[:-4]
        n = board_qty(board)
        if n is None:
            continue
        for ref, val, fp, inline in netlist_parts(path):
            code = codes.get(val) or inline
            if code is None:
                unpriceable[val or fp.split(":")[-1]] += n
                continue
            demand[code] += n
            used[code].append((board, ref, val))
    return demand, used, unpriceable


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="report, write nothing")
    a = ap.parse_args(argv)

    demand, used, unpriceable = collect()
    print("%d distinct LCSC part(s) across the order\n" % len(demand))

    cache, rows, dead = {}, [], []
    for code, qty in demand.most_common():
        try:
            usd, stock, model = price_at(code, qty, cache)
        except Exception as e:                      # the API is not ours; say so
            print("  %-10s lookup failed: %r" % (code, e))
            continue
        if usd is None:
            dead.append((code, used[code][0][2]))
            continue
        rows.append((usd * qty, code, qty, usd, stock, model, used[code]))

    rows.sort(reverse=True)
    print("  %-10s %-26s %6s %9s %10s %9s" % ("LCSC", "MODEL", "QTY", "EACH", "LINE", "STOCK"))
    for line, code, qty, usd, stock, model, where in rows:
        short = stock is not None and stock < qty
        print("  %-10s %-26s %6d %9.4f %10.2f %9s%s"
              % (code, (model or "?")[:26], qty, usd, line,
                 "-" if stock is None else stock, "  << SHORT" if short else ""))
    print("\n  order total for coded parts: $%.2f" % sum(r[0] for r in rows))
    if dead:
        print("\n  NOT IN THE CATALOGUE (%d): %s"
              % (len(dead), ", ".join("%s=%s" % (c, v) for c, v in dead)))
    if unpriceable:
        print("\n  no LCSC code, still priced by footprint (%d value(s), %d pieces):"
              % (len(unpriceable), sum(unpriceable.values())))
        for v, n in unpriceable.most_common(8):
            print("     x%-6d %s" % (n, v[:60]))

    conn, conn_rows = mating_halves(), []
    for code, qty in conn.most_common():
        try:
            usd, stock, model = price_at(code, qty, cache)
        except Exception as e:
            print("  %-10s lookup failed: %r" % (code, e))
            continue
        if usd is not None:
            conn_rows.append((usd * qty, code, qty, usd, stock, model))
    conn_rows.sort(reverse=True)
    print("\nMATING HALVES -- housings and crimps, derived from the headers:")
    for line, code, qty, usd, stock, model in conn_rows:
        print("  %-10s %-24s %6d %9.4f %10.2f %9s%s"
              % (code, (model or "?")[:24], qty, usd, line, stock,
                 "  << SHORT" if stock is not None and stock < qty else ""))
    print("  order total $%.2f -> $%.2f per instrument"
          % (sum(r[0] for r in conn_rows), sum(r[0] for r in conn_rows) / ORDER_INSTRUMENTS))

    if a.dry:
        print("\n--dry: nothing written")
        return 0

    path = os.path.join(ROOT, "elec", "prices.json")
    prices = json.load(io.open(path, encoding="utf-8"),
                       object_pairs_hook=collections.OrderedDict)
    by_ref = prices["parts_by_ref"]
    prices["connectors"] = collections.OrderedDict([("_note", [
        "Housings and crimp contacts, DERIVED from the board headers by",
        "tools/lcsc_prices.py -- one housing per header, one contact per way -- and",
        "priced at the order quantity. No netlist holds these: a harness is not a",
        "schematic, which is why this category used to be reported as not counted.",
    ])])
    for line, code, qty, usd, stock, model in conn_rows:
        prices["connectors"][code] = collections.OrderedDict([
            ("usd", round(usd, 4)), ("verified", "v"),
            ("per_instrument", qty / float(ORDER_INSTRUMENTS)),
            ("what", "%s -- JLCPCB parts API at qty %d" % (model, qty))])
    by_ref["_note"] = [
        "Every 'v' line here is written by tools/lcsc_prices.py from JLCPCB's parts",
        "API at the quantity a ten-instrument order needs. Re-run it rather than",
        "editing by hand: the breaks move and so does stock.",
    ]
    for line, code, qty, usd, stock, model, where in rows:
        for board, ref, val in where:
            by_ref["%s:%s" % (board, ref)] = collections.OrderedDict([
                ("usd", round(usd, 4)), ("verified", "v"),
                ("what", "%s %s -- JLCPCB parts API at qty %d" % (val, code, qty))])
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump(prices, fh, indent=2)
        fh.write("\n")
    print("\n  wrote %d ref price(s) into elec/prices.json" % sum(len(r[6]) for r in rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
