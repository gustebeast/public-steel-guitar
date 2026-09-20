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
import json
import os
import re
import subprocess
import sys
import zipfile

KICAD_CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
KICAD_PY = r"C:\Program Files\KiCad\10.0\bin\python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
FAB_DIR = os.path.join(OUT_DIR, "fab")

# SIX boards: the power board merged into motor_ctrl, and the optical pickup landed
# (both 2026-09-15). This is now the whole instrument.
BOARDS = ("can_tee", "lever_sensor", "motor_ctrl", "output_panel",
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
    # ── the optical board, every line checked against the manufacturer's datasheet on
    # 2026-09-17 (pinout verified pin by pin, not just the package) ──────────────────
    "STM32H743IIT6": "C89597",      # LQFP176; pins re-derived from ST's CubeMX symbol
    "USB3343-CP": "C633347",        # ULPI PHY; pinout was INVENTED before this check
    "USBLC6-2SC6": "C7519",         # ESD array, SOT23-6L: 1 IO1 2 GND 3 IO2 4 IO2 5 VBUS 6 IO1
    "TLV9064IDR": "C388176",        # quad TIA, SOIC-14 (TI SBOS839 Table 5-5)
    "TLV9061IDBVR": "C398358",      # mid-rail buffer -- DBV, NOT the DCK part once ordered
    "AMS1117-3.3": "C6186",         # 3V3 digital LDO: 1 GND 2 VOUT/tab 3 VIN
    "SPX3819M5-L-3-3/TR": "C9055",  # 3V3 analog LDO: 1 IN 2 GND 3 EN 4 BYP 5 OUT
    "TPS560430XFDBVR": "C523980",   # 24->5 V sync buck, 1.1 MHz FPWM
    "IR17-21C/TR8": "C131250",      # 940 nm emitter, 65 mA max, VF 1.2 typ
    "VEMD4110X01": "C3211080",      # PIN photodiode -- ⚠ 95 in stock, 200 needed for ten
    "S4B-XH-SM4-TB": "C161861",     # the (LF)(SN) form, 20,992; the bare listing is 0
    # Crystals are specified by PART, not by frequency -- see the note beside Y1.
    # Inductors are specified by PART too -- see the note beside L1. Isat 1.35 A
    # worst case against the TPS560430's 1.4 A maximum current limit, which is the
    # number TI tells you to size against.
    "SWPA4020S150MT": "C36407",      # 15 uH, 4x4x2.0 shielded, DCR 0.299 ohm max
    # ⚠ "600" IS 60 OHM in Murata/Sunlord bead numbering. 601 is the 600 ohm part.
    "GZ1608D601TF": "C1002",         # 0603 bead, 600R@100MHz, 200 mA, DCR 450 mohm
    "TX322525M4LBDD2T": "C5308007",  # 25 MHz, CL 20 pF, ESR 30 ohm (MCU HSE)
    "K3A260002010": "C2835957",      # 26 MHz, CL 20 pF, ESR 30 ohm (the PHY's limits)
    # ── sourced 2026-09-17 from JLCPCB's own parts API, not from memory ──────────
    # Each line names the listing's exact model and the stock it showed, because a code
    # with no source is the thing this file exists to refuse. Picked by EXACT model and
    # genuine manufacturer; where a listing was the bare MPN at 0 stock and its (LF)(SN)
    # tin-plated form was stocked, the stocked form is the same part as ordered from JST.
    "B4B-XH-A": "C144395",          # JST B4B-XH-A(LF)(SN), stock 60,424
    "B2B-XH-A": "C158012",          # JST B2B-XH-A(LF)(SN), stock 381,008 -- sourced
                                    # 2026-09-19 by asking the catalogue, and it is the
                                    # (LF)(SN) trap again and not a preference: the BARE
                                    # "B2B-XH-A" listing is C19272845 with ONE piece in
                                    # stock. Same shape as S4B-XH-SM4-TB and B4B-XH-A.
    "S4B-XH-A": "C157925",          # JST S4B-XH-A(LF)(SN), stock 88,547
    "LMR33630ADDAR": "C841384",     # TI, ESOP-8 (= HSOIC-8 PowerPAD), stock 6,730
    "PJ-102AH": "C3096093",         # CUI PJ-102AH, stock 1,593
    "MX126-5.0-02P": "C5188434",    # MAX MX126-5.0-02P-GN01-Cu-S-A, stock 48,416
    # The two CLASS lines whose pinout the netlist actually writes out, so a part can be
    # checked against it pin for pin rather than chosen by name:
    "TLV9061IDBVR": "C398358",      # TI, SOT-23-5: 1 OUT 2 V- 3 IN+ 4 IN- 5 V+ -- exact
                                    # match to U7/U8. Stock 301,906. Same family as the
                                    # optical board's TIAs. RRIO, 5.5 V max on a 5 V rail.
    "AP2112K-3.3TRG1": "C51118",    # Diodes Inc, SOT-23-5: 1 IN 2 GND 3 EN 4 NC 5 OUT --
                                    # exact match to U6. 600 mA against a 300 mA class.
                                    # Stock 55,831.
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
    "NMJ4HCD2",            # 1/4 in jack. JLCPCB lists it (C18185363) at ZERO
                           # stock, 2026-09-17 -- a listing is not a source
    "USB1046-GF-0180",     # GCT USB-A. Not listed at JLCPCB (2026-09-17); the
                           # nearest is -0190-L-B-A at 5 in stock. ⚠ THE ONE THAT WENT WRONG -- if this
                           # string ever changes, that is the footprint moving
                           # under it, and the build should stop until someone
                           # confirms the two still agree
    # ⚠ THESE THREE ARE NOT SOURCING GAPS, THEY ARE PLACEHOLDER PINOUTS -- and the
    # routed board is therefore electrically wrong at all three, whatever DRC says.
    # U3 is modelled as 10 invented pins on a TSSOP-20 footprint; a real PCM5102A has
    # 20, and its pin 1 is CPVDD, not LRCK. U4 (hub) and K1 (relay) are numbered 1..N
    # with no datasheet behind them. DRC is clean because it checks the board against
    # the NETLIST, and the netlist is what is wrong. Choosing an LCSC code here would
    # order a real part for a board wired to an imaginary one.
    "FRT5-class 5V",       # true-bypass relay -- pinout is a placeholder
    "PCM5102A-class",      # DAC -- pinout is a placeholder (10 of 20 pins, invented)
    # ── the 2026-09-15 panel respin ──────────────────────────────────────────
    "PCM1808PWR",          # ⚠ THE PART IS REAL AND STOCKED (C55513, 463, 2026-09-17)
                           # AND IT STAYS OPEN, because the board around it is not:
                           # the netlist gives a 14-pin TSSOP 16 pins in an invented
                           # order and ties SCKI to BCK. Sourcing it would let the
                           # panel order the moment the other opens close. See the
                           # AUDIT note at the top of output_panel.py.
    "CH334-class HS hub",  # ⚠ MUST BE HIGH SPEED -- a full-speed hub puts BOTH
                           # devices behind a Transaction Translator and undoes
                           # the whole reason the panel carries a hub. Confirm the
                           # exact CH334 variant against that before ordering
})

# Generic passives are JLCPCB BASIC parts chosen at order time from the package and
# value, which is normal practice and not an omission -- an 0402 100nF is not a
# sourcing decision. They are reported separately from the real OPENs.
GENERIC = re.compile(r"^(R_|C_|Fuse_|Jumper:|Diode_SMD:D_SOD|Diode_SMD:D_SM[AB]|"
                     r"Inductor_SMD|Crystal:)")
# ⚠ ONLY PASSIVES ARE VALUE-CHOSEN. An 0402 is picked from its value; an LED in an 0805
# land is picked from its part number, and "IR17-21C/TR8" is a perfectly good value that
# simply does not start with a digit. The placeholder rule below applies to this subset.
PASSIVE = re.compile(r"^(R_|C_|L_|Inductor_SMD)")
# Footprint LIBRARIES that hold no orderable part -- see the BOM loop.
# ⚠ Jumper BELONGS HERE AND WAS MISSING. A SolderJumper is a BOARD FEATURE: two pads and
# a mask opening, closed with solder by whoever assembles it. There is nothing to buy and
# nothing to place. It was reaching the BOM as a line reading Comment "TERM", footprint
# "SolderJumper-2_P1.3mm_Open...", and NO part number -- an order asking a fab to source
# a part that does not exist. can_tee carried one, motor_ctrl two.
#
# It slipped past the placeholder guard because that guard only fires on PASSIVES, and a
# jumper is "generic" (the GENERIC pattern lists Jumper:) without being a passive. So
# "TERM" -- a value that cannot pick a part -- was accepted. The CPL was right all along
# and omitted them, which is how the discrepancy showed: BOM designators 4 against CPL 3.
COPPER_ONLY = re.compile(r"^(TestPoint|NetTie|Fiducial|SolderJumper|Jumper)")


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
        n = int(unrouted.group(1))
        tracks = sum(1 for ln in open(pcb, encoding="utf-8") if ln.lstrip().startswith("(segment"))
        # ⚠ SAY WHICH OF THE TWO FAILURES THIS IS. They need opposite responses and
        # the message used to assert the first one flatly: a board that was never routed
        # arrives as bare copper and wants route.py; a board that WAS routed and has
        # three nets left wants a look at those three nets, and being told to "run
        # route.py first" sends you to re-run a step that already ran. Track count is
        # what distinguishes them, and it costs one pass over a file already on disk.
        # ⚠ AND TAKE THE OLD PACKAGE WITH IT. Refusing to WRITE a zip leaves any
        # previous one sitting in fab/ looking exactly like a current one -- which is
        # the same "looks complete and arrives incomplete" failure this refusal exists
        # to prevent, arriving by the back door. lever_sensor.zip survived here from
        # 2026-09-17, two days and a BOOT0 rework out of date, describing a board that
        # no longer exists. A board that cannot be packaged must not appear packaged.
        _stale = os.path.join(FAB_DIR, "%s.zip" % board)
        if os.path.isfile(_stale):
            os.remove(_stale)
            print("  removed the previous %s.zip -- it describes an older board and "
                  "this one cannot be packaged" % board)
        raise SystemExit(
            "%s: %d unconnected item(s) -- %s. A fab package built from it would look "
            "complete and arrive incomplete."
            % (board, n,
               "this board has NO routing at all; run elec/route.py on it first"
               if tracks == 0 else
               "the board IS routed (%d segments) but the router could not finish "
               "these nets. Re-running route.py will not help -- it is deterministic "
               "now and will make the same choices. Look at the nets themselves"
               % tracks))

    # ⚠ AND DRC IS NOT THE WHOLE TEST EITHER. It answers "is this manufacturable",
    # not "is this correct": a router can hand back a DRC-perfect board on which the
    # USB pair is split across two layers and took two unrelated paths. elec/verify.py
    # is where the checks a PERSON would otherwise make by eye are written down, and
    # running it HERE is what stops it being a script nobody remembers to run. Boards
    # that declare no budgets pass it trivially, so this costs them nothing.
    v = subprocess.run([KICAD_PY, os.path.join(HERE, "verify.py"), stem],
                       capture_output=True, text=True)
    if v.returncode:
        # ⚠ AND THE STALE ZIP GOES HERE TOO. The unconnected-items refusal above
        # deletes it, on the principle that a board which cannot be packaged must not
        # appear packaged -- and this refusal, added later, did not. Found by making a
        # budget fail on purpose to check the gate bites: it does, and it left the
        # previous output_panel.zip in the fab directory, described by nothing. A
        # refusal that leaves the artefact behind is the weaker half of a gate.
        _stale = os.path.join(FAB_DIR, "%s.zip" % board)
        if os.path.isfile(_stale):
            os.remove(_stale)
            print("  removed the previous %s.zip -- it describes an older board and "
                  "this one cannot be packaged" % board)
        raise SystemExit("%s: FAILED its declared high-speed budgets --\n%s"
                         % (board, (v.stdout or "") + (v.stderr or "")[-400:]))

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
            # ⚠ BARE COPPER IS NOT A BOM LINE. Test points, net ties and fiducials are
            # footprints with no part behind them: nothing is placed, nothing is
            # soldered, and asking JLCPCB to source one would be asking for a part that
            # does not exist. The footprints carry exclude_from_bom themselves, but the
            # BOM here is built from the NETLIST rather than the board, so that
            # attribute never reaches it.
            if COPPER_ONLY.search(fp.split(":", 1)[0]):
                continue
            code = LCSC.get(val, "")
            if not code:
                generic = bool(GENERIC.search(fp.split(":", 1)[1]) or GENERIC.search(fp))
                # ⚠ A GENERIC PASSIVE STILL NEEDS A VALUE, and "generic" was letting
                # placeholders through. JLCPCB picks an 0402 100nF from the value field;
                # it cannot pick an 0402 "Rf". The optical board carried FIFTY-THREE
                # parts whose value was a note to self -- "Rf", "Cf C0G", "ballast",
                # "mid-rail top", "load C0G", "preset" -- and every one was counted as a
                # sourced generic and would have reached a quote as a blank line.
                # A real value starts with a digit. That is the whole rule, and it
                # accepts every value this project actually uses (100nF, 8k06 1%,
                # 22uF/16V, 600R@100MHz, 18uH) while rejecting every placeholder.
                if generic and PASSIVE.search(fp.split(":", 1)[1]) \
                        and not re.match(r"\d", val.strip()):
                    raise SystemExit(
                        "%s: %s (%s) has value %r, which is a placeholder rather than a "
                        "value -- the fab cannot choose a part from it. Give it a real "
                        "value, or if it is genuinely undecided put it in "
                        "fab.OPEN_VALUES so it is COUNTED as undecided."
                        % (board, ",".join(sorted(refs)), fp.split(":", 1)[1], val))
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

    # ⚠ WHAT THE GERBERS CANNOT SAY. Mask colour, board thickness, surface finish and
    # copper weight are chosen in the ORDER FORM, not in any generated file, so a board
    # whose design depends on one of them has no way to carry that to the person paying
    # -- and "I remember it should be black" is not a design record. A board declaring
    # order_options gets them written into its own zip, next to the gerbers, where
    # whoever opens it to place the order will see them.
    opts = json.load(open(stem + ".board.json", encoding="utf-8")).get("order_options")
    if opts:
        with open(os.path.join(d, "ORDER.txt"), "w", encoding="utf-8") as f:
            f.write("%s -- order form settings that are NOT in the gerbers\n\n" % board)
            for k in sorted(opts):
                f.write("  %-12s %s\n" % (k + ":", opts[k]))
    z = os.path.join(FAB_DIR, "%s.zip" % board)
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn in sorted(os.listdir(d)):
            zf.write(os.path.join(d, fn), fn)
    return n, len(groups), sorted(open_real), sorted(open_generic), z, opts or {}


def _sweep_stale(names):
    """Delete packages for boards that no longer exist, and warn on ones left behind.

    ⚠ THIS FILE REFUSES TO BUILD A PACKAGE FOR A BOARD THAT DOES NOT PASS, AND THAT IS
    ONLY HALF THE GUARANTEE. Refusing to write a new zip does nothing about the OLD one
    sitting beside it, and a stale zip is indistinguishable from a fresh one to whoever
    uploads it -- which is exactly the "looks complete and arrives incomplete" failure
    this file exists to prevent, arriving by the back door.

    Found by listing the directory rather than trusting it: trrs_adapter.zip from
    2026-09-16 and usb_panel.zip from 09-14, both for boards whose GENERATORS HAVE BEEN
    DELETED from the design, and lever_sensor.zip from 09-17, which predates that
    board's BOOT0 rework and describes a board that no longer exists either. All three
    were orderable-looking and none of them were current.

    A package whose generator is gone is deleted outright -- there is no board it could
    describe. A package for a board that still exists but was not rebuilt this run is
    left alone and NAMED, because it may simply not have been asked for.
    """
    import glob
    for z in sorted(glob.glob(os.path.join(FAB_DIR, "*.zip"))):
        board = os.path.splitext(os.path.basename(z))[0]
        gen = os.path.join(HERE, "%s.py" % board)
        if not os.path.isfile(gen):
            os.remove(z)
            print("  removed %s.zip -- no generator; that board is not in the design"
                  % board)
        elif board not in names:
            # ASCII only in PRINTED text: this console is cp1252 and a warning glyph
            # here raised UnicodeEncodeError, which took the whole tool down. The
            # comments in this file use the glyph freely because they are source, not
            # output.
            print("  !! %s.zip is from an earlier run and was NOT rebuilt now -- check "
                  "its date before ordering" % board)

    # ⚠ THE SAME ARGUMENT REACHES ONE DIRECTORY UP, and the sweep stopped at the zips.
    # Deleting usb_panel.zip left elec/out/usb_panel.kicad_pcb, .net, .dsn and eight more
    # files from 2026-09-14 -- a whole board's intermediates for a generator that is no
    # longer in the design. Nothing distinguishes them from a current board's: finish.py
    # will happily route that .kicad_pcb if somebody names the stem, and it would produce
    # a real-looking result for a board nobody can regenerate.
    #
    # NAMED, NOT DELETED, and the asymmetry with the zips is deliberate. A zip is derived
    # and can always be rebuilt from the board; these intermediates are the ONLY surviving
    # artefact of a design whose source has been removed, so throwing them away is not
    # reversible in the way deleting a package is. Whoever removed the generator gets to
    # decide, and now they get told there is something to decide about.
    # ⚠ ONLY THINGS THAT ARE ACTUALLY BOARDS. The first version of this asked "does
    # a generator exist for every stem in elec/out" and named FIFTY-SEVEN of them --
    # o2, rp7, z9, chk, skidl_REPL and the rest of years of scratch files. A warning
    # channel that cries wolf fifty-seven times is worse than no warning at all, which
    # is the same argument as the DRC warnings this session spent its time on. A board
    # is a stem with a .kicad_pcb; scratch is not.
    for f in sorted(glob.glob(os.path.join(OUT_DIR, "*.kicad_pcb"))):
        board = os.path.basename(f)[:-len(".kicad_pcb")]
        # A tagged snapshot is <board>.<tag>.kicad_pcb -- optical.baseline1,
        # optical.pre_incr, <board>.unrouted. Those belong to a board that DOES exist
        # and are kept on purpose for comparison; only an undotted stem is its own board.
        if "." in board:
            continue
        if not os.path.isfile(os.path.join(HERE, "%s.py" % board)):
            n = len(glob.glob(os.path.join(OUT_DIR, board + ".*")))
            print("  !! elec/out holds %d file(s) for '%s', which has no generator -- a "
                  "board that is not in the design any more. Delete them or restore it."
                  % (n, board))


def _check_bom_md(names):
    """Hold BOM.md against the packages just built, and say so here.

    ⚠ A CHECK NOTHING CALLS IS A CHECK THAT DOES NOT RUN. verify.py sat unrun for
    weeks behind a docstring insisting it existed to remove the human, because no step
    invoked it. bom_check.py and part_totals.py were written today and were in exactly
    that position. This is the step that turns boards into something orderable and
    BOM.md is what a person orders from, so this is where the two belong.

    ⚠ IT REPORTS, IT DOES NOT REFUSE, and the line is drawn at the artefact. A wrong
    part number in BOM.md does not corrupt the fab package -- JLC assembles from the CPL
    and BOM inside the zip, which are generated. Refusing to build the package over a
    documentation error would block the thing that is correct because the thing beside it
    is not. It fails where it actually bites: somebody hand-ordering, or reading the file
    to understand what the instrument is made of.

    Only runs on a FULL build. Against a partial one it would report parts as unnamed
    that are simply not in this run's packages.
    """
    if set(names) != set(BOARDS):
        return
    try:
        import bom_check
        import part_totals
        bad = bom_check.check()[0]
        per = part_totals.totals()[0]
        bom_txt = open(os.path.join(os.path.dirname(HERE), "BOM.md"),
                       encoding="utf-8").read()
        unlisted = [v for v in per if v in LCSC and v not in bom_txt]
    except Exception as exc:                # a check that breaks must not break the run
        print()
        print("  !! BOM.md checks did not run: %r" % (exc,))
        return
    if not bad and not unlisted:
        print()
        print("BOM.md agrees with the packages: every designator row names the part its "
              "board places,")
        print("  and every sourced part is named.")
        return
    print()
    print("!! BOM.md DISAGREES WITH THE BOARDS -- the packages are fine, the document "
          "is not:")
    for board, des, part, code, val, line in bad:
        print("   BOM.md:%-5d %-6s says %-20s %-10s but %s places %s"
              % (line, des, part, code, board, val))
    for val in sorted(unlisted):
        print("   %-20s is placed and SOURCED (%s) but named nowhere in BOM.md"
              % (val, LCSC[val]))


def main(names):
    os.makedirs(FAB_DIR, exist_ok=True)
    _sweep_stale(names)
    blocked, order = {}, {}
    for b in names:
        n, g, open_real, open_generic, z, opts = fab(b)
        if opts:
            order[b] = opts
        print("%-13s %3d placements, %2d BOM lines, %d generic + %d OPEN  -> %s"
              % (b, n, g, len(open_generic), len(open_real), os.path.basename(z)))
        if open_real:
            blocked[b] = open_real
    if blocked:
        print("\nSOURCING STILL OPEN -- these cannot be ordered assembled:")
        for b, vals in blocked.items():
            for v in vals:
                print("   %-13s %s" % (b, v))
    if order:
        print("\nORDER FORM SETTINGS (not in the gerbers -- see each zip's ORDER.txt):")
        for b, opts in order.items():
            for k in sorted(opts):
                print("   %-13s %-11s %s" % (b, k, opts[k].split(" -- ")[0]))
    _check_bom_md(names)
    # ASCII on purpose: this prints to a Windows console whose default
    # codepage is cp1252, and a warning that raises UnicodeEncodeError is
    # worse than no warning at all.
    print("\n!! CHECK EVERY ROTATION in JLCPCB's previewer before paying: the CPL "
          "carries\n  KiCad's convention, which differs per part from LCSC's.")


if __name__ == "__main__":
    main(sys.argv[1:] or list(BOARDS))
