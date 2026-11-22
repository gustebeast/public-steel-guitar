"""frozen_check calls a band pierced by new foreign copper lost (lead 2026-11-22).

    KiCad-python cadkit/pcbflow/test_frozen_pierce.py <run dir: esc12 rPS_12a1>

rPS_12a1's router put a GND via at (96.28, 117.15) inside VIN_BRAIN's B.Cu trunk: the band stayed
one piece, lost under 2 % of its area, and frozen_check read it as kept. On a scratch copy:
  0  baseline (layout) then the same unrouted board -> rc 0, nothing LOST
  1  baseline then the routed board                 -> rc 3, VIN_BRAIN B.Cu LOST as pierced,
                                                        the GND via at (96.28, 117.15) named
Exit 0 = PASS.
"""
import os
import shutil
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
fc = os.path.join(here, "frozen_check.py")
run_dir = os.path.abspath(sys.argv[1])
tmp = tempfile.mkdtemp(prefix="frozen_pierce_")
stem = os.path.join(tmp, "b")
bad = []


def run(src, stage):
    shutil.copy(src, stem + ".kicad_pcb")
    r = subprocess.run([sys.executable, fc, stem, stage], env=dict(os.environ, PCBFLOW_FROZEN_CHECK="1"),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout


un = os.path.join(run_dir, "output_board.unrouted.kicad_pcb")
ro = os.path.join(run_dir, "output_board.kicad_pcb")
rc, out = run(un, "layout")
rc, out = run(un, "same")
print("case 0: rc %d" % rc)
if rc != 0 or "LOST" in out:
    bad.append("case 0: the unrouted board against its own baseline reads LOST")
rc, out = run(ro, "ownroute")
lines = [ln for ln in out.splitlines() if "FROZEN BAND LOST" in ln]
for ln in lines:
    print("case 1:", ln.strip()[:240])
hit = [ln for ln in lines if "VIN_BRAIN on B.Cu" in ln and "pierced" in ln and "GND at (96.28, 117.15)" in ln]
if rc != 3 or not hit:
    bad.append("case 1: rc %d; VIN_BRAIN B.Cu not called pierced by the GND via at (96.28, 117.15)" % rc)
for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.stdout.flush()
os._exit(1 if bad else 0)
