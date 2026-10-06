"""Does every LCSC code in fab.LCSC still point at the part it claims?

⚠ A WRONG LCSC CODE IS THE ONE MISTAKE NOTHING ELSE IN THIS PIPELINE CAN CATCH. The
netlist, the CAD, DRC and the router all work in terms of the MPN string; the code is
the only field the fab actually reads, and it is a bare number that no check compares
against anything. Get it wrong and a correct board arrives populated with the wrong
part -- and this project has already written one bad code by hand (`S4B-XH-SM4-TB:
C157960`), caught only because somebody re-checked it before the edit was applied.

So this asks LCSC's own catalogue. It is a network check and deliberately NOT wired into
the build: it runs at checkpoints, before ordering, and whenever a code changes.

    py -3.12 elec/lcsc_check.py

⚠ A SUFFIX IS NOT A MISMATCH. JST parts list as `S4B-XH-A(LF)(SN)` -- the lead-free
tin-plated form, which is the one actually stocked (the bare listing is often zero), and
which this project already sources deliberately. Connectors and terminals also carry
colour/plating variant tails such as `-GN01-Cu-S-A`. The comparison therefore accepts a
catalogue name that STARTS with the MPN once punctuation is normalised, and reports
anything else.

Verified clean across all 32 codes on 2026-09-17, with the six suffix cases listed.

⚠ RE-RUN 2026-09-18: all 31 codes still point at the part they claim, and the stock
report is the part worth reading. Three sit under the 200 threshold, and only one of them
is a constraint, because what matters is stock DIVIDED BY THE PER-INSTRUMENT COUNT:

    VEMD4110X01    20 per instrument (2 detectors x 10 strings)   95 ->  4.8 instruments
    USB3343-CP      1 per instrument                              98 -> 98
    K3A260002010    1 per instrument                             108 -> 108

So the photodiode is the only sourcing risk and it is HALF the ten-instrument basis, not
a warning about the other two. The PHY reads as low next to a flat threshold and covers
ninety-eight builds; a threshold that does not know the BOM quantity cannot tell those
apart, which is why the number to act on is the rightmost column.

⚠ RE-RUN 2026-09-19: 32 codes (B2B-XH-A closed, C158012), all still matching. The
report changed shape, and not because a supplier moved -- because THIS BOARD SET DID.
S8B-XH-A appeared under the threshold at 160, and read per instrument it is now the
second-tightest part in the BOM:

    VEMD4110X01    20 per instrument                             95 ->  4.8 instruments
    S8B-XH-A       21 per instrument (10 tees + 11 sensor boards) 160 ->  7.6
    USB3343-CP      1 per instrument                              92 -> 92
    K3A260002010    1 per instrument                             108 -> 108

It was a 10-per-instrument part until lever_sensor's J1 moved onto the same connector on
2026-09-18, which doubled the demand without anything in the pipeline noticing: a part
count per instrument is not a quantity any DRC, netlist or gate reads. That is the check
this file is for, and it only caught it because the per-instrument divisor is applied by
hand -- so apply it by hand, every time, and do not read the stock column alone.

⚠ RE-RUN 2026-09-19, AND THE DIVISION IS NOW DONE BY THE TOOL. Everything above argued
that the number to act on is stock DIVIDED BY the per-instrument count, and then printed
a bare stock figure and left the division to whoever read it -- which is how S8B-XH-A at
160 looked like the PHY at 92 when one covers 7.6 builds and the other 92.
part_totals.py derives demand from the built packages, so the report computes it:

    VEMD4110X01     C3211080    95 / 20 per instrument =   4.8 builds
    S8B-XH-A        C157914    160 / 21               =   7.6
    USB3343-CP      C633347     92 /  1               =  92
    K3A260002010    C2835957   108 /  1               = 108
    SPX3819M5       C9055      171 /  1               = 171

Only the first two are constraints. The other three are under a flat 200 threshold and
cover a hundred builds each, which is exactly the confusion the flat threshold creates
and the reason this column exists.

The PHY is still worth watching for a different reason: this same file recorded it OUT OF
STOCK on 2026-08-04, so 98 is a recovery rather than a floor, and it has no second source
in the catalogue.
"""
import io
import json
import os
import re
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = ("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/"
       "selectSmtComponentList")


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def lookup(code):
    req = urllib.request.Request(URL, data=json.dumps(
        {"keyword": code, "currentPage": 1, "pageSize": 3}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    for c in d["data"]["componentPageInfo"]["list"] or []:
        if c["componentCode"] == code:
            return c["componentModelEn"], c["stockCount"]
    return None, None


# ── THE PASSIVES: a code keyed on (value, footprint) has no part number to compare ────
# So what is compared is what the row ASKS for against what the catalogue says the code
# IS: the package, the value, and -- where the row states them -- the voltage (at least),
# the dielectric and the tolerance (at most).
_MULT = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "R": 1.0, "k": 1e3, "M": 1e6}


def _ask(value):
    """A row's value string -> (number in F or ohm, min volts, dielectric, max tol %)."""
    head = value.split()[0].split("/")[0]
    m = re.match(r"^(\d+(?:\.\d+)?)(p|n|u)F$", head)
    if m:
        num = float(m.group(1)) * _MULT[m.group(2)]
    else:
        m = re.match(r"^(\d+)([RkM])(\d*)$", head)
        if not m:
            return None
        num = float(m.group(1) + ("." + m.group(3) if m.group(3) else "")) * _MULT[m.group(2)]
    volts = re.search(r"/(\d+)V", value)
    diel = re.search(r"\b(C0G|X7R|X5R)\b", value)
    tol = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
    return (num, float(volts.group(1)) if volts else None, diel.group(1) if diel else None,
            float(tol.group(1)) if tol else None)


def _says(describe):
    """The catalogue's description -> (number, volts, dielectric, tol %)."""
    d = describe.replace("NP0", "C0G")
    num = None
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)(p|n|u)F\b", d)
    if m:
        num = float(m.group(1)) * _MULT[m.group(2)]
    else:
        m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)(k|M|m)?\u03a9", d)
        if m:
            num = float(m.group(1)) * {"k": 1e3, "M": 1e6, "m": 1e-3, None: 1.0}[m.group(2)]
    volts = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)V\b", d)
    diel = re.search(r"\b(C0G|X7R|X5R|X6S|X7S|Y5V)\b", d)
    tol = re.search(r"\u00b1(\d+(?:\.\d+)?)%", d)
    return (num, float(volts.group(1)) if volts else None, diel.group(1) if diel else None,
            float(tol.group(1)) if tol else None)


def lookup_full(code):
    req = urllib.request.Request(URL, data=json.dumps(
        {"keyword": code, "currentPage": 1, "pageSize": 3}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    for c in d["data"]["componentPageInfo"]["list"] or []:
        if c["componentCode"] == code:
            return c
    return None


def check_passives(low_stock=2000):
    """Every fab.PASSIVES row against the catalogue. Returns the list of disagreements."""
    src = io.open(os.path.join(HERE, "fab.py"), encoding="utf-8").read()
    body = re.search(r"^PASSIVES = \{(.*?)^\}", src, re.S | re.M).group(1)
    rows = re.findall(r'\("([^"]+)",\s*"([^"]+)"\):\s*"(C\d+)"', body)
    bad, seen = [], {}
    for value, fp, code in rows:
        want_pkg = re.match(r"^[A-Z]_(\d{4})_", fp).group(1)
        if code not in seen:
            try:
                seen[code] = lookup_full(code)
            except Exception as e:
                print("  %-12s %-6s %-10s -> lookup failed: %r" % (value, want_pkg, code, e))
                continue
            time.sleep(0.15)
        c = seen[code]
        if c is None:
            bad.append((value, fp, code, "NOT IN THE CATALOGUE"))
            continue
        ask, got = _ask(value), _says(c.get("describe") or "")
        why = []
        if (c.get("componentSpecificationEn") or "") != want_pkg:
            why.append("package is %s" % c.get("componentSpecificationEn"))
        if ask is None:
            why.append("cannot read the row's value")
        else:
            if got[0] is None or abs(got[0] - ask[0]) > 1e-6 * max(ask[0], 1e-15) + 1e-18:
                if not (ask[0] == 0 and got[0] == 0):
                    why.append("value is %r" % (got[0],))
            if ask[1] is not None and fp.startswith("C_") and (got[1] is None or got[1] < ask[1]):
                why.append("rated %s V, the row asks %g" % (got[1], ask[1]))
            if ask[2] and got[2] != ask[2]:
                why.append("dielectric is %s" % got[2])
            if ask[3] is not None and (got[3] is None or got[3] > ask[3]):
                why.append("tolerance is %s %%, the row asks %g" % (got[3], ask[3]))
        if (c.get("stockCount") or 0) < low_stock:
            why.append("stock %s" % c.get("stockCount"))
        if why:
            bad.append((value, fp, code, "; ".join(why) + "  [" + (c.get("describe") or "")[:60] + "]"))
    print("%d passive row(s) checked against %d code(s)" % (len(rows), len(seen)))
    for value, fp, code, why in bad:
        print("  !! %-12s %-20s %-10s %s" % (value, fp, code, why))
    if not bad:
        print("  every one is the package, value, voltage, dielectric and tolerance its row asks for")
    return bad


def main(low_stock=200):
    src = io.open(os.path.join(HERE, "fab.py"), encoding="utf-8").read()
    body = re.search(r"^LCSC = \{(.*?)^\}", src, re.S | re.M).group(1)
    pairs = sorted(set(re.findall(r'"([^"]+)":\s*"(C\d+)"', body)))
    bad, thin = [], []
    for mpn, code in pairs:
        try:
            got, stock = lookup(code)
        except Exception as e:                      # the API is not ours; say so
            print("  %-22s %-10s -> lookup failed: %r" % (mpn, code, e))
            continue
        if got is None:
            bad.append((mpn, code, "NOT IN THE CATALOGUE"))
        elif not _norm(got).startswith(_norm(mpn)):
            bad.append((mpn, code, got))
        if stock is not None and stock < low_stock:
            thin.append((mpn, code, stock))
        time.sleep(0.15)
    print("%d code(s) checked" % len(pairs))
    bad += [(v + " @ " + f, c, why) for v, f, c, why in check_passives()]
    if thin:
        # ⚠ DIVIDE BY THE PER-INSTRUMENT COUNT, WHICH THIS FILE USED TO ASK A HUMAN TO
        # DO. Its own note says "a threshold that does not know the BOM quantity cannot
        # tell those apart, which is why the number to act on is the rightmost column"
        # -- and then printed a bare stock figure and left the division to whoever read
        # it. That is how S8B-XH-A sat at 160 looking like the PHY at 92, when one
        # covers 7.6 instruments and the other 92. part_totals.py derives the demand
        # from the built packages, so the column can just be computed.
        demand = {}
        try:
            import part_totals
            demand = part_totals.totals()[0]
        except Exception as exc:
            print("\n  (per-instrument demand unavailable: %r)" % (exc,))
        print("\nstock under %d, worst coverage first:" % low_stock)
        rows = []
        for mpn, code, n in thin:
            per = demand.get(mpn)
            rows.append((n / per if per else float("inf"), mpn, code, n, per))
        for cover, mpn, code, n, per in sorted(rows):
            if per:
                print("   %-22s %-10s %6d in stock / %2d per instrument = %5.1f builds"
                      % (mpn, code, n, per, cover))
            else:
                print("   %-22s %-10s %6d in stock / not placed by any built package"
                      % (mpn, code, n))
    if bad:
        print("\n*** %d CODE(S) DO NOT MATCH THEIR MPN ***" % len(bad))
        for mpn, code, got in bad:
            print("   %-22s %-10s -> %s" % (mpn, code, got))
        return 1
    print("\nevery code points at the part it claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
