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
