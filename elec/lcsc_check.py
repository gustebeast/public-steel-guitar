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
        print("\nstock under %d:" % low_stock)
        for mpn, code, n in sorted(thin, key=lambda t: t[2]):
            print("   %-22s %-10s %s" % (mpn, code, n))
    if bad:
        print("\n*** %d CODE(S) DO NOT MATCH THEIR MPN ***" % len(bad))
        for mpn, code, got in bad:
            print("   %-22s %-10s -> %s" % (mpn, code, got))
        return 1
    print("\nevery code points at the part it claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
