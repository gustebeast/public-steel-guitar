import json, sys, urllib.request
sys.path.insert(0, 'elec')
import lcsc_check as L
def q(kw, n=12):
    req = urllib.request.Request(L.URL, data=json.dumps(
        {"keyword": kw, "currentPage": 1, "pageSize": n}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    print("==", kw)
    for c in d["data"]["componentPageInfo"]["list"] or []:
        print("  %-10s %-32s stock %-8s %s | %s" % (
            c.get("componentCode"), (c.get("componentModelEn") or "")[:32],
            c.get("stockCount"), (c.get("componentSpecificationEn") or "")[:22],
            (c.get("describe") or "")[:55]))
for kw in sys.argv[1:]:
    try: q(kw)
    except Exception as e: print("!!", kw, e)
