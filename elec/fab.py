"""Fab outputs — gerbers, drill, BOM and CPL, one zip per board.

    py -3.12 elec/fab.py                # every board
    py -3.12 elec/fab.py lever_sensor   # just one

RUNS UNDER py -3.12, not KiCad's Python: everything here shells out to kicad-cli
or reads text, so it needs neither pcbnew nor cadquery.

WHAT THIS IS FOR. The board files are the design; THIS is the handoff. Until it
existed the project had five routed, DRC-clean boards and no way to order any of
them -- which is a pipeline that looks finished and is not. It is deliberately
run BEFORE the last board is designed, so that a problem here (a layer name JLCPCB
rejects, a rotation convention, a missing sourcing decision) is found once rather
than once per board.

⚠ ROTATION IS THE CLASSIC WAY TO LOSE A BOARD, and it is NOT fully solvable here.
KiCad's position file gives the footprint's rotation in the KiCad footprint's own
frame; JLCPCB's placement machine wants it in the LCSC part's frame, and for many
parts those differ by 90/180/270. There is no general rule -- it is per part, and
the honest workflow is to CHECK EVERY PART in JLCPCB's online previewer before
paying. This file emits the KiCad convention unmodified and says so in the CPL
header, rather than applying guessed corrections that would be invisible later.

WHAT IS MISSING AND WHY IT IS BLANK RATHER THAN GUESSED: LCSC part numbers exist
here only where the repo already recorded one. Everything else emits an EMPTY
cell and is counted in the summary as OPEN. A wrong part number is worse than a
missing one -- the missing one stops the order, the wrong one ships.
"""
from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import zipfile

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
FAB_DIR = os.path.join(OUT_DIR, "fab")

# SIX boards: the power board merged into motor_ctrl, and the optical pickup landed
# (both 2026-09-15). This is now the whole instrument.
BOARDS = ("can_tee", "trrs_adapter", "lever_sensor", "motor_ctrl", "output_panel",
          "optical")

# Layer sets by copper count. JLCPCB takes the KiCad extensions directly.
L2 = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
L4 = ("F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
      "F.Mask,B.Mask,Edge.Cuts")

# ── SOURCING ─────────────────────────────────────────────────────────────────
# ONLY codes the repo already recorded, keyed by the part VALUE as the netlist
# carries it. Nothing is inferred: an entry here means a human wrote that number
# down somewhere in elec/ or BOM.md, and a blank means the decision has not been
# made. See the module docstring on why blank beats a guess.
LCSC = {
    "S8B-XH-A": "C157914",          # 8-way side-entry XH, motor tee trunk
    "S8B-PH-SM4-TB": "C265121",     # 8-way side-entry PH, lever board trunk
    "PJ-320D-4A": "C95562",         # TRRS 4-pole socket
    "SN65HVD230DR": "C12084",       # CAN transceiver, both boards
    "LMR16006XDDCR": "C87080",      # 60 V 0.6 A buck, lever + motor controller
    "TYPE-C-31-M-12": "C165948",    # USB-C receptacle, motor controller + panel
    "CH32V203G6U6": "C5142280",     # lever board MCU
    "CH32V307WCU6": "C5142795",     # motor controller MCU
    "MT6701QT-STD": "C2913974",     # the angle sensor
    "AO3400A": "C20917",            # logic-level N-ch FET; the optical board's Q1 too
}
# ⚠ EVERY VALUE STRING MUST BE ACCOUNTED FOR -- IN LCSC, GENERIC, OR HERE.
# branner's catch, and it is the right shape for the bug that happened: usb_panel's
# J2 kept its OLD part number in `value` after its footprint moved to a different
# connector, and the BOM reads `value`. NOTHING ELSE IN THE PIPELINE DOES -- not
# the netlist, not the layout, not DRC -- so a stale part number is invisible
# right up until a box of nine-contact USB 3.0 shells arrives for a four-pad
# footprint. Only running fab.py caught it, and only because I happened to read
# the output.
#
# Reporting unknowns was not enough: a changed value simply joined the OPEN pile
# and looked like every other undecided part. So unknowns are now DECLARED. A
# value that is neither sourced nor generic nor listed below FAILS THE BUILD,
# which means changing a part number forces you to come here and say so.
OPEN_VALUES = frozenset({
    "B4B-XH-A",            # the project's standard 4-way XH, still unsourced
    "S4B-XH-A",            # its side-entry sibling, the motor tee's drop
    "LMR33630ADDAR",       # power board buck -- confirm LCSC stock at order time
    "NMJ4HCD2",            # 1/4 in jack; BOM.md prices it, no LCSC line yet
    "PJ-102AH",            # 24 V barrel inlet, ditto
    "USB1046-GF-0180",     # GCT USB-A. ⚠ THE ONE THAT WENT WRONG -- if this
                           # string ever changes, that is the footprint moving
                           # under it, and the build should stop until someone
                           # confirms the two still agree
    "FRT5-class 5V",       # true-bypass relay -- a class, not a part, on purpose
    "PCM5102A-class",      # DAC -- ditto
    "single RRO op-amp",   # output buffer AND pickup buffer -- ditto
    # ── the 2026-09-15 panel respin ──────────────────────────────────────────
    "PCM1808PWR",          # 24-bit 99 dB ADC. ⚠ I had written an LCSC code into
                           # its description from memory and took it back out:
                           # this file's own rule is that a WRONG part number is
                           # worse than a missing one, and a number I cannot point
                           # at a source for is a guess wearing a number's clothes
    "CH334-class HS hub",  # ⚠ MUST BE HIGH SPEED -- a full-speed hub puts BOTH
                           # devices behind a Transaction Translator and undoes
                           # the whole reason the panel carries a hub. Confirm the
                           # exact CH334 variant against that before ordering
    "3V3 LDO 300mA",       # a class, not a part
    "MX126-5.0-02P",       # 2-way screw terminal, the pickup input
})

# Generic passives are JLCPCB BASIC parts chosen at order time from the package and
# value, which is normal practice and not an omission -- an 0402 100nF is not a
# sourcing decision. They are reported separately from the real OPENs.
GENERIC = re.compile(r"^(R_|C_|Fuse_|Jumper:|Diode_SMD:D_SOD|Diode_SMD:D_SM[AB]|"
                     r"Inductor_SMD|Crystal:)")


def _run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("kicad-cli failed:\n  %s\n%s" % (" ".join(args), r.stderr[-800:]))
    return r.stdout


def _parts(stem):
    """[(ref, value, footprint)] from the netlist -- the same file the board was
    laid out from, so the BOM cannot describe a different build than the gerbers."""
    t = open(stem + ".net", encoding="utf-8").read()
    out = []
    for m in re.finditer(r'\(comp\s*\(ref "([^"]+)"\)\s*\(value "([^"]*)"\).*?'
                         r'\(footprint "([^"]+)"\)', t, re.S):
        out.append(m.groups())
    return sorted(out)


def _layers(stem):
    import json
    return L4 if json.load(open(stem + ".board.json", encoding="utf-8"))["layers"] == 4 else L2


def fab(board):
    stem = os.path.join(OUT_DIR, board)
    pcb = stem + ".kicad_pcb"
    if not os.path.isfile(pcb):
        raise SystemExit("no routed board at %s -- run layout.py and route.py first" % pcb)
    # ⚠ A PLACED BOARD IS NOT A FINISHED BOARD, and gerbers do not say so. The board
    # file exists as soon as layout.py runs; export it before route.py has been through
    # and you get a clean-looking package with no tracks in it -- which is precisely the
    # "pipeline that looks finished and is not" this file was written against. DRC is
    # what knows the difference, so ask it rather than trusting that the step was run.
    r = subprocess.run([KICAD_CLI, "pcb", "drc", "--exit-code-violations", pcb],
                       capture_output=True, text=True)
    unrouted = re.search(r"Found (\d+) unconnected", r.stdout or "")
    if unrouted and int(unrouted.group(1)):
        raise SystemExit(
            "%s: %s unconnected items -- this board is PLACED but not ROUTED, and a fab "
            "package built from it would look complete and arrive as bare copper. Run "
            "elec/route.py on it first." % (board, unrouted.group(1)))

    d = os.path.join(FAB_DIR, board)
    os.makedirs(d, exist_ok=True)

    _run([KICAD_CLI, "pcb", "export", "gerbers", "-o", d + os.sep,
          "--layers", _layers(stem), "--no-x2", "--subtract-soldermask", pcb])
    # Excellon, mm, 2:4, PTH and NPTH in ONE file: JLCPCB accepts merged and it
    # removes the commonest upload mistake, which is forgetting the NPTH file and
    # getting a board with no mounting holes.
    _run([KICAD_CLI, "pcb", "export", "drill", "-o", d + os.sep, "--format", "excellon",
          "--drill-origin", "absolute", "--excellon-units", "mm", pcb])
    # (--excellon-separate-th and --generate-map are FLAGS, not options taking a
    #  value; passing "false" makes kicad-cli read it as the input file and fail.
    #  Omitting them is what gives one merged drill file and no map.)

    # ---- CPL, converted to JLCPCB's column names ----
    raw = os.path.join(d, "_pos.csv")
    _run([KICAD_CLI, "pcb", "export", "pos", "-o", raw, "--format", "csv",
          "--units", "mm", "--side", "both", pcb])
    cpl = os.path.join(d, "%s-cpl.csv" % board)
    with open(raw, newline="", encoding="utf-8") as f, \
            open(cpl, "w", newline="", encoding="utf-8") as g:
        r = csv.DictReader(f)
        w = csv.writer(g)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        n = 0
        for row in r:
            w.writerow([row["Ref"], row["PosX"], row["PosY"],
                        "top" if row["Side"].lower() == "top" else "bottom", row["Rot"]])
            n += 1
    os.remove(raw)

    # ---- BOM, grouped by (value, footprint) the way JLCPCB reads it ----
    groups, open_real, open_generic = {}, set(), set()
    for ref, val, fp in _parts(stem):
        groups.setdefault((val, fp), []).append(ref)
    bom = os.path.join(d, "%s-bom.csv" % board)
    with open(bom, "w", newline="", encoding="utf-8") as g:
        w = csv.writer(g)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, fp), refs in sorted(groups.items()):
            code = LCSC.get(val, "")
            if not code:
                generic = bool(GENERIC.search(fp.split(":", 1)[1]) or GENERIC.search(fp))
                if not generic and val not in OPEN_VALUES:
                    raise SystemExit(
                        "%s: value %r (%s) is neither sourced, generic, nor "
                        "declared OPEN. Nothing but the BOM reads the value "
                        "field, so an unrecognised one is how a wrong part "
                        "gets ordered. Add it to fab.LCSC if you know the "
                        "part number, or to fab.OPEN_VALUES if you do not."
                        % (board, val, fp.split(":", 1)[1]))
                (open_generic if generic else open_real).add(val)
            w.writerow([val, ",".join(sorted(refs)), fp.split(":", 1)[1], code])

    z = os.path.join(FAB_DIR, "%s.zip" % board)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(d)):
            zf.write(os.path.join(d, fn), fn)
    return n, len(groups), sorted(open_real), sorted(open_generic), z


def main(names):
    os.makedirs(FAB_DIR, exist_ok=True)
    blocked = {}
    for b in names:
        n, g, open_real, open_generic, z = fab(b)
        print("%-13s %3d placements, %2d BOM lines, %d generic + %d OPEN  -> %s"
              % (b, n, g, len(open_generic), len(open_real), os.path.basename(z)))
        if open_real:
            blocked[b] = open_real
    if blocked:
        print("\nSOURCING STILL OPEN -- these cannot be ordered assembled:")
        for b, vals in blocked.items():
            for v in vals:
                print("   %-13s %s" % (b, v))
    # ASCII on purpose: this prints to a Windows console whose default
    # codepage is cp1252, and a warning that raises UnicodeEncodeError is
    # worse than no warning at all.
    print("\n!! CHECK EVERY ROTATION in JLCPCB's previewer before paying: the CPL "
          "carries\n  KiCad's convention, which differs per part from LCSC's.")


if __name__ == "__main__":
    main(sys.argv[1:] or list(BOARDS))
