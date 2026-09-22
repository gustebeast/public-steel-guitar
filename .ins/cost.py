import sys, csv, json, urllib.request
sys.path.insert(0, 'elec'); import lcsc_check as L
BUILD = 10          # instruments per order (the BOM convention)
def rec(code):
    req = urllib.request.Request(L.URL, data=json.dumps({'keyword': code, 'currentPage': 1, 'pageSize': 5}).encode(),
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    for c in (d.get('data') or {}).get('componentPageInfo', {}).get('list') or []:
        if c.get('componentCode') == code:
            return c
def price(c, qty):
    p = None
    for b in sorted(c.get('componentPrices') or [], key=lambda b: b['startNumber']):
        if qty >= b['startNumber']: p = b['productPrice']
    return p or c['componentPrices'][0]['productPrice']
PASSIVE = 0.004     # basic-library 0402/0603/0805 R or C, each (JLC typical)
def board(rows):
    tot = ext = 0.0; lines = []
    for name, code, n in rows:
        if code:
            c = rec(code); u = price(c, n * BUILD)
            lib = c.get('componentLibraryType')
            fee = 3.0 / BUILD if lib == 'expand' else 0.0
        else:
            u, lib, fee = PASSIVE, 'passive', 0.0
        tot += u * n; ext += fee
        lines.append((name, code, n, u, u * n, lib))
    return tot, ext, lines
rows = []
for r in csv.DictReader(open('elec/out/fab/optical/optical-bom.csv', encoding='utf-8')):
    rows.append((r['Comment'], r['LCSC Part #'].strip(), len(r['Designator'].split(','))))
now = board(rows)
new_rows = [r for r in rows if r[0] != 'VEMD4110X01']
new_rows += [('PD15-22B/TR8', 'C161211', 20), ('TLV320ADC3140IRTWT', 'C1852021', 5),
             ('ADC support caps (~10/chip)', '', 50)]
new = board(new_rows)
es = [r for r in new_rows if not r[0].startswith('TLV320')] + [('ES7210', 'C365743', 5)]
es = board(es)
for tag, (t, e, lines) in (('NOW', now), ('PD15+ADC3140', new), ('PD15+ES7210', es)):
    print('== %s  parts $%.2f  + extended-part fees $%.2f/board  = $%.2f' % (tag, t, e, t + e))
for l in now[2] + new[2][-3:] + es[2][-1:]:
    if l[4] > 0.2: print('  %-28s %-9s x%-3d $%.3f = $%.2f  %s' % l)
