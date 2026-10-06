"""Order-day BOM and placement files, as JLCPCB's order page needs them.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/order_files.py ui_board foot_led_a ...

Writes elec/out/fab/<board>/<board>-bom-order.csv and <board>-cpl-order.csv beside the
package elec/fab.py built. UPLOAD THESE TWO, not the -bom.csv / -cpl.csv in the zip.

WHY (found walking the five lighting / UI boards through the order page, 2026-10-06):

1. A BLANK PART NUMBER IS NOT SAFE. The package leaves generic passives uncoded, to be
   "chosen at order time". JLCPCB's matcher reads the footprint name C_0402_1005Metric as
   01005: 100nF came up as C161362 (01005, 6.3 V) and 10k as C364373 (01005). Both are
   Standard-only, so on an Economic order the rows arrive UNSELECTED with quantity 0 and
   the board would be built without them. PASSIVE below gives every (value, footprint)
   on these boards a code read from JLCPCB's parts API. It is keyed on BOTH because the
   same value is on two footprints across the project (100nF: 0402 and 0805).
2. THE PLACEMENT FILE CARRIES KiCad's ANGLE AND ORIGIN, and the fab's library footprint
   has its own of each. A through-hole header's KiCad origin is pin 1; the fab's is the
   centre, so the 1x20 header previewed 24 mm off its holes. This file fits the fab's
   pads (LIB, read from easyeda.com/api/products/<code>/components) onto ours and writes
   the angle and the position of THEIR origin.
3. PAD NUMBERS CANNOT ORIENT A SYMMETRIC HEADER. The 2x8 right-angle header's hole grid
   is the same turned half round; the fab's footprint has the body beside the odd row,
   KiCad's beside the even row. Fitted by pad number it previewed with its pins pointing
   INTO the board over SW2. The body goes where OUR footprint draws it: half a turn more.

Still to do by hand on the order page: the seam pogo pins (C5203987) arrive UNSELECTED
(a "difficult" part, 0.08 USD each extra) -- tick the row. SW2's library pads do not fit
ours under any rotation, so it is left as KiCad wrote it; it previewed inside its outline.
"""
import pcbnew, sys, math, re
PASSIVE = {
    ("100nF", "C_0402_1005Metric"): "C307331", ("100nF/50V", "C_0402_1005Metric"): "C307331",
    ("10k", "R_0402_1005Metric"): "C25744", ("10k 1%", "R_0402_1005Metric"): "C25744",
    ("100k 1%", "R_0402_1005Metric"): "C25741", ("1k 1%", "R_0402_1005Metric"): "C11702",
    ("200k 1%", "R_0402_1005Metric"): "C25764", ("3k3", "R_0402_1005Metric"): "C25890",
    ("7k68 1%", "R_0402_1005Metric"): "C25919", ("1uF/25V", "C_0402_1005Metric"): "C52923",
    ("10uF/50V", "C_1206_3216Metric"): "C13585", ("4.7uF/25V", "C_0805_2012Metric"): "C1779",
    ("4.7uF/50V", "C_0805_2012Metric"): "C98192", ("10uF/25V", "C_0805_2012Metric"): "C15850",
}
LIB = {
 "C116842": [["21",0,0],["11",2.925,2.87],["12",2.275,2.87],["13",1.625,2.87],["14",0.975,2.87],["15",0.325,2.87],["16",-0.325,2.87],["17",-0.975,2.87],["18",-1.625,2.87],["19",-2.275,2.87],["20",-2.925,2.87],["10",2.925,-2.87],["9",2.275,-2.87],["8",1.625,-2.87],["7",0.975,-2.87],["6",0.325,-2.87],["5",-0.325,-2.87],["4",-0.975,-2.87],["3",-1.625,-2.87],["2",-2.275,-2.87],["1",-2.925,-2.87]],
 "C2071783": [["12",-0.925,0],["11",-1.263,0.9],["10",-0.613,0.9],["9",0.037,0.9],["8",0.538,0.9],["7",1.263,0.5],["6",1.263,0],["5",1.263,-0.5],["4",0.538,-0.9],["3",0.037,-0.9],["2",-0.613,-0.9],["1",-1.263,-0.9]],
 "C2071384": [["12",-0.812,0],["11",-1.263,0.9],["10",-0.613,0.9],["9",0.037,0.9],["8",0.538,0.9],["7",1.263,0.5],["6",1.263,0],["5",1.263,-0.5],["4",0.538,-0.9],["3",0.037,-0.9],["2",-0.613,-0.9],["1",-1.263,-0.9]],
 "C7371891": [["1",-2.165,1.98],["2",-2.165,0.66],["8",2.165,-1.98],["7",2.165,-0.66],["6",2.165,0.66],["3",-2.165,-0.66],["4",-2.165,-1.98],["5",2.165,1.98]],
 "C161861": [["1",-3.75,3.5],["2",-1.25,3.5],["3",1.25,3.5],["4",3.75,3.5]],
 "C160841": [["A",-1.5,-7.8],["5",1,-6.98],["B",7.8,-1.5],["7",7.8,1.5],["C",1.5,7.8],["9",-1.5,7.8],["6",-1,5.78],["D",-7.8,1.5],["8",-7.8,-1.5],["10",6.86,-3.75]],
 "C22462024": [["6",2.5,2.75],["5",0,2.75],["4",-2.5,2.75],["3",2.5,-2.75],["2",0,-2.75],["1",-2.5,-2.75]],
 "C22438114": [[str(2*i+1+j), -4.445+1.27*i, -0.635+1.27*j] for i in range(8) for j in range(2)],
 "C2905493": [[str(n), -24.13+2.54*(n-1), 0] for n in range(1, 21)],
}
BY_VALUE = {"TLC59711PWPR": "C116842", "LMR33630CRNXR": "C2071783", "LMR33630BRNXR": "C2071384", "XL-5050RGBW": "C7371891",
            "S4B-XH-SM4-TB": "C161861", "RKJXT1F42001": "C160841", "PB-22E85-S-5.7C-C-W": "C22462024",
            "PZ1.27-2x8P": "C22438114", "KH-2.54PH180-1X20P-L11.5": "C2905493"}
import csv, os
mm = 1e-6
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
for name in sys.argv[1:]:
    b = pcbnew.LoadBoard(os.path.join(OUT, name + ".kicad_pcb"))
    d = os.path.join(OUT, "fab", name)
    bom = list(csv.reader(open(os.path.join(d, name + "-bom.csv"), encoding="utf-8")))
    for r in bom[1:]:
        if not r[3]:
            if (r[0], r[2]) not in PASSIVE:
                raise SystemExit("%s: %s on %s has no part code -- add it to PASSIVE" % (name, r[0], r[2]))
            r[3] = PASSIVE[(r[0], r[2])]
    csv.writer(open(os.path.join(d, name + "-bom-order.csv"), "w", newline="", encoding="utf-8")).writerows(bom)
    rows = list(csv.reader(open(os.path.join(d, name + "-cpl.csv"), encoding="utf-8")))
    fix = {}
    for f in b.GetFootprints():
        code = BY_VALUE.get(f.GetValue())
        if not code: continue
        k = f.GetOrientationDegrees(); th = math.radians(k); o = f.GetPosition()
        ours = {}
        for p in f.Pads():
            n = p.GetNumber()
            if not n: continue
            dx, dy = (p.GetPosition().x - o.x) * mm, -(p.GetPosition().y - o.y) * mm
            ours.setdefault(n, []).append((dx * math.cos(-th) - dy * math.sin(-th), dx * math.sin(-th) + dy * math.cos(-th)))
        ours = {n: (sum(q[0] for q in v) / len(v), sum(q[1] for q in v) / len(v)) for n, v in ours.items()}
        lib = {n: (x, y) for n, x, y in LIB[code]}; common = [n for n in lib if n in ours]
        best = None
        for R in (0, 90, 180, 270):
            c, s_ = math.cos(math.radians(R)), math.sin(math.radians(R))
            rot = {n: (lib[n][0] * c - lib[n][1] * s_, lib[n][0] * s_ + lib[n][1] * c) for n in common}
            tx = sum(ours[n][0] - rot[n][0] for n in common) / len(common)
            ty = sum(ours[n][1] - rot[n][1] for n in common) / len(common)
            err = max(math.hypot(ours[n][0] - rot[n][0] - tx, ours[n][1] - rot[n][1] - ty) for n in common)
            if best is None or err < best[0]: best = (err, R, tx, ty)
        err, R, tx, ty = best
        if err > 0.45: print("  SKIP", f.GetReference(), f.GetValue(), "pads do not match (%.2f)" % err); continue
        wx = o.x * mm + tx * math.cos(th) - ty * math.sin(th)
        wy = -o.y * mm + tx * math.sin(th) + ty * math.cos(th)
        # the 2-row right-angle header: its hole grid is symmetric, so pad NUMBERS cannot say
        # which side the body goes. The fab's footprint has the body beside its odd row, KiCad's
        # beside the even row; the body must go where OUR footprint draws it, so half a turn more.
        if f.GetValue() == "PZ1.27-2x8P": R += 180
        fix[f.GetReference()] = (wx, wy, (k + R) % 360)
    moved = 0
    for r in rows[1:]:
        if r[0] in fix:
            wx, wy, a = fix[r[0]]
            if math.hypot(wx - float(r[1]), wy - float(r[2])) > 0.05: moved += 1
            r[1], r[2], r[4] = "%.6f" % wx, "%.6f" % wy, "%.6f" % a
    csv.writer(open(os.path.join(d, name + "-cpl-order.csv"), "w", newline="", encoding="utf-8")).writerows(rows)
    print(name, "rows", len(rows) - 1, "re-angled/re-centred", len(fix), "moved", moved)
