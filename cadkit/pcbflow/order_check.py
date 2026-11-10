"""The order-day facts about a board's parts, read off the fab's own catalogue.

    py -3.12 cadkit/pcbflow/order_check.py elec/out/<board> [--builds N]

Writes <stem>.order.json: for every BOM row (the same rows fab_package writes), the code
ordered, the part the catalogue says that code IS, its stock today against what an order
needs, whether the assembly service will place it, and whether it is a basic or an
extended (extra-fee) part. quality.py reads it for M12, M30 and M42 -- the parts of those
rules a script can answer -- and holds a snapshot older than ORDER_MAX_AGE_DAYS (quality.py)
to be no answer at all: stock is a fact about one day.

⚠ A NETWORK STEP, AND DELIBERATELY NOT IN THE BUILD (2026-11-10). It asks JLCPCB's parts
API, the one elec/lcsc_check.py has used since 2026-09-17. A route or a finish must not
depend on a web service being up; an ORDER must, so this runs on order day, and the quality
pass says plainly when it has not been run.

THE PROJECT SUPPLIES THE CODES. The project's generator folder holds fab.py, which
configures fab_package with its tables when imported; this loads it (PCBFLOW_PROJECT, or
the folder above the stem's out/) and reads the rows through fab_package itself, so the
snapshot is of exactly the BOM that would be sent.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request

URL = ("https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/"
       "selectSmtComponentList")
BUILDS = 5                       # boards per order, default (--builds)


def _norm(s):
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def lookup(code):
    """The catalogue's record for `code`, or None."""
    req = urllib.request.Request(URL, data=json.dumps(
        {"keyword": code, "currentPage": 1, "pageSize": 3}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=30))
            break
        except Exception:                          # a flaky fetch is retried, then reported
            if attempt == 2:
                raise
            time.sleep(2.0)
    for c in (d.get("data") or {}).get("componentPageInfo", {}).get("list") or []:
        if c.get("componentCode") == code:
            return c
    return None


def _project_fab(stem):
    """fab_package, configured by the project's own fab.py."""
    proj = os.environ.get("PCBFLOW_PROJECT") or os.path.dirname(os.path.dirname(os.path.abspath(stem)))
    path = os.path.join(proj, "fab.py")
    if not os.path.isfile(path):
        raise SystemExit("order_check: no fab.py in %s -- the codes live there" % proj)
    sys.path.insert(0, proj)
    sys.path.insert(0, os.path.dirname(proj))
    spec = importlib.util.spec_from_file_location("project_fab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fabp = next((v for v in vars(mod).values()
                 if getattr(v, "__name__", "").endswith("fab_package")), None)
    if fabp is None:
        raise SystemExit("order_check: %s does not import fab_package" % path)
    return fabp


def check(stem, builds=BUILDS):
    fabp = _project_fab(stem)
    notes = json.load(open(stem + ".board.json", encoding="utf-8"))
    per = int(notes.get("qty_per_instrument", 1) or 1)
    groups = {}
    for ref, val, fp in fabp._parts(stem):
        groups.setdefault((val, fp), []).append(ref)
    rows = []
    for (val, fp), refs in sorted(groups.items()):
        code = fabp.code_for(val, fp)
        row = {"value": val, "footprint": fp, "refs": refs, "code": code,
               "need": len(refs) * per * builds}
        if code:
            c = lookup(code)
            if c is None:
                row["missing"] = True
            else:
                row.update(model=c.get("componentModelEn"), brand=c.get("componentBrandEn"),
                           stock=c.get("stockCount"), library=c.get("componentLibraryType"),
                           buyable=str(c.get("isBuyComponent")) == "1",
                           no_buy=c.get("noBuyReason"), describe=c.get("describe"),
                           generic=bool(fabp.GENERIC.match(fp) or fabp.GENERIC.match(fp.split(":", 1)[-1])))
            time.sleep(0.3)
        rows.append(row)
    out = {"board": os.path.basename(stem), "checked": datetime.date.today().isoformat(),
           "builds": builds, "per_build": per, "rows": rows}
    with open(stem + ".order.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return out


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    builds = BUILDS
    if "--builds" in argv:
        builds = int(argv[argv.index("--builds") + 1])
        args = [a for a in args if a != str(builds)]
    for stem in args:
        out = check(stem, builds)
        low = [r for r in out["rows"] if r.get("code") and (r.get("stock") or 0) < r["need"]]
        ext = [r for r in out["rows"] if r.get("library") == "expand"]
        print("%s: %d rows, %d extended, %d short of stock for %d build(s) -> %s.order.json"
              % (out["board"], len(out["rows"]), len(ext), len(low), builds, os.path.basename(stem)))
        for r in low:
            print("   SHORT %-10s %-24s stock %s, need %d" % (r["code"], r["value"][:24],
                                                            r.get("stock"), r["need"]))


if __name__ == "__main__":
    main(sys.argv[1:])
