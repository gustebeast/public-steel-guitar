"""frozen_check.py stops a stage that cuts a frozen band (lead 2026-11-21).

    KiCad-python cadkit/pcbflow/test_frozen_check.py UNROUTED ROUTED [GAIN_UN GAIN_RO [POUR_UN POUR_RO]]

UNROUTED / ROUTED: one placement before and after a route that cut a band (brain_board rPS_e3:
+5V_SW 42.2 -> 20.0 + 6.7 mm2, a +24V_RIB via on its edge). Cases, in a scratch copy:
  0  baseline then the same board again        -> rc 0, nothing LOST
  1  baseline then the routed board            -> rc 3, +5V_SW LOST, the +24V_RIB via named
  2  PCBFLOW_FROZEN_CHECK=warn                 -> rc 0, still says LOST
  3  PCBFLOW_FROZEN_CHECK=0                    -> rc 0, no output
GAIN_UN / GAIN_RO (rPS_fg1): the route widened VIN_CM5's own stub over U205.7 and an island
inside the package joined it -- 1 -> 2 filled pieces, but the second is copper the baseline
never had:
  4  -> rc 0, VIN_CM5 pieces 1 -> 1
POUR_UN / POUR_RO (rPS_fg2, laid before frozen bands outranked every pour): +24V's whole pour
(priority 11) filled over VIN_BRAIN's F.Cu band (9) once routed, no foreign track or via near:
  5  -> rc 3, VIN_BRAIN LOST, the +24V pour named
"""
import os, shutil, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__)); fc = os.path.join(here, "frozen_check.py")
import _testargs  # noqa: E402
_testargs.need(2, 'UNROUTED ROUTED: one placement before and after a route that cut a band (brain_board rPS_e3)')
un, ro = sys.argv[1], sys.argv[2]
extra = sys.argv[3:]
tmp = tempfile.mkdtemp(prefix="frozen_check_"); stem = os.path.join(tmp, "b"); ok = True


def run(src, stage, mode="1"):
    shutil.copy(src, stem + ".kicad_pcb")
    env = dict(os.environ, PCBFLOW_FROZEN_CHECK=mode)
    r = subprocess.run([sys.executable, fc, stem, stage], env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout


def say(c, good, msg):
    global ok
    ok &= good
    print("%s case %s: %s" % ("PASS" if good else "FAIL", c, msg))


run(un, "layout")
rc, out = run(un, "ownroute.py")
say(0, rc == 0 and "LOST" not in out, "same board -> rc %d" % rc)
rc, out = run(ro, "ownroute.py")
say(1, rc == 3 and "LOST at ownroute.py: +5V_SW" in out and "via +24V_RIB at (103.23, 125.30)" in out,
    "routed board -> rc %d, +5V_SW named %s, +24V_RIB via named %s"
    % (rc, "LOST at ownroute.py: +5V_SW" in out, "via +24V_RIB at (103.23, 125.30)" in out))
rc, out = run(ro, "ownroute.py", "warn")
say(2, rc == 0 and "LOST" in out, "warn -> rc %d" % rc)
rc, out = run(ro, "ownroute.py", "0")
say(3, rc == 0 and not out.strip(), "off -> rc %d" % rc)
if len(extra) >= 2:
    run(extra[0], "layout")
    rc, out = run(extra[1], "ownroute.py")
    say(4, rc == 0 and "VIN_CM5 F.Cu pieces 1 -> 1" in out, "copper gained -> rc %d, VIN_CM5 1 -> 1 %s"
        % (rc, "VIN_CM5 F.Cu pieces 1 -> 1" in out))
if len(extra) >= 4:
    run(extra[2], "layout")
    rc, out = run(extra[3], "ownroute.py")
    nm = "pour +24V 'whole' priority 11 over band priority 9" in out
    say(5, rc == 3 and "LOST at ownroute.py: VIN_BRAIN on F.Cu" in out and nm,
        "outranking pour -> rc %d, +24V pour named %s" % (rc, nm))
sys.stdout.flush()
os._exit(0 if ok else 1)
