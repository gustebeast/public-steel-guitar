"""frozen_check names the cut, not the crowd (lead 2026-11-22).

    "C:/Program Files/KiCad/10.0/bin/python.exe" test_frozen_blame.py <dir holding rPS_11a4's routed board as
        b.kicad_pcb / b.kicad_pro and its layout baseline b.frozen_base.json>

rPS_11a4 (brain board, esc11 seed 4): the post-route island repair laid GND 0.25 mm tracks through +24V_LED's
F.Cu band and split it. Inside the band's grown outline there are also +24V_RIB tracks and five vias (router
copper) that a refill-bisect (splitwho / splitcat) showed do not cut it. The LOST line must name GND 0.25
tracks and nothing else; the +24V_RIB copper and the vias go on the "also inside" line. Exit 0 = PASS.
Works on a copy (the check reads the board, never writes it).
"""
from __future__ import annotations
import contextlib, io, os, re, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import wx as _wx
    _wx.DisableAsserts()
except Exception:
    pass
import frozen_check  # noqa: E402

src = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp(prefix="fzb-")
for ext in (".kicad_pcb", ".kicad_pro", ".frozen_base.json"):
    shutil.copyfile(os.path.join(src, "b" + ext), os.path.join(tmp, "b" + ext))
os.environ["PCBFLOW_FROZEN_CHECK"] = "warn"
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    frozen_check.main(os.path.join(tmp, "b"), "ownroute.py")
out = buf.getvalue()
sys.stdout.write("\n".join(l for l in out.splitlines() if "LOST at" in l or "also inside" in l)[:3000] + "\n")
line = next((l for l in out.splitlines() if "FROZEN BAND LOST" in l and "+24V_LED" in l), "")
cut = line.split("; cut by ", 1)[1] if "; cut by " in line else ""
named = [x.strip() for x in cut.split(";") if x.strip()]
ok = (bool(named) and all(re.match(r"track GND w 0\.25 ", x) for x in named)
      and "+24V_RIB" not in cut and "via" not in cut)
print("PASS" if ok else "FAIL", "-- +24V_LED cut named:", named)
shutil.rmtree(tmp, ignore_errors=True)
sys.stdout.flush()
os._exit(0 if ok else 1)
