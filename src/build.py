"""Public Steel Guitar -- the main build: the direct-drive instrument.

  py -3.12 -m src.build              # build all printed parts + the viewer's model + the gates
  py -3.12 -m src.build --part NAME  # build one printed part (fast iteration)
  py -3.12 -m src.build --list       # list part names

The instrument is src.direct_bench's (user, 2026-11-13). Its printed parts come from there
(_direct_parts, below); PARTS here lists the rest: the UI station's printed parts and the
shop jigs, each built by its own module. Everything of the v1 belt-drive instrument is gone,
including the parts once kept to reuse -- the knee levers, the leg and its latches and the
pedal bar (user, 2026-11-17: they get redesigned for this body). It is all at the git tag
v1-instrument.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import json
import pathlib
import re
import sys
import time
from functools import partial

_T_IMPORT = time.perf_counter()         # the modules below BUILD GEOMETRY as they import

import cadquery as cq

# Shared CAD utilities, vendored at <project>/cadkit (git subtree).
from cadkit.step_export import export_print, export_print_parts
from cadkit.orientation import (PrintOrientation as PO,
                                require_declared, unconfirmed)
try:                                    # optional on-every-build face-count regression gate
    from tools.build_profile import (record_part, report_build_regressions,
                                     write_part_volumes)
except Exception:                       # a profiling hook must NEVER break a build
    def record_part(*a, **k): pass
    def report_build_regressions(): return 0
    def write_part_volumes(*a, **k): return 0

from .helpers import heal


def _m(name):
    """src.<name>, imported when a builder first runs and not before: a part's module is
    only paid for by a build that builds it (--part and --list import nothing else)."""
    return importlib.import_module("src." + name)


# ── PRINTED parts → each is exported as its own STEP. ────────────────────
# This is the ONLY set that gets STEP files; purchased parts and stand-ins appear only in
# the assembly. Values are (builder, path, note); the builder runs at export time, so
# importing this module builds nothing. Paths are MATERIAL FOLDERS -- slice a whole folder
# with one filament:
#   petg-gf/  stiffness/creep-critical (the sustained string-tension + ground-reaction paths)
#   pctg/     compliant, snap-fit, impact and fine-feature parts
#   tpu/      feet
#   steel/    laser-cut sheet (ordered, not printed)
#   tools/    shop jigs
PARTS = {
    "ui_clamp": (lambda: heal(_m("ui_panel").clamp()), "petg-gf/ui_clamp.step", "PETG-GF - the UI clamp plate. It lies against the BOARD'S UNDERSIDE (3.2 thick, a relief under each through-hole footprint for the tails) and one M4x10 pulls it up into the deck panel's own boss, gripping the board between its whole top face and the deck's bearings; two spigots off the deck locate it. It holds the display too: two arms step up past the board and run +Y under the module, either side of the display's ribbon, to a crossbar at its far mounting-hole row, and four columns -- two off that crossbar, two off tabs beside the board's ends -- press the module's PCB into the window ledge. The ribbon carries no load, so that is the screen's whole retention. GF because it is a stiffness part. Prints PLATE-DOWN, its own flat underside on the bed, so every rib, column and post grows straight up off it"),
    "ui_pwr_cap": (lambda: heal(_m("ui_panel").power_cap()), "pctg/ui_pwr_cap.step", "PCTG - the power button's cap: a plain O15.2 disc with a blind square socket, pressed onto the latching switch's 3.3 mm stem and guided by its hole in the deck. Prints TOP-FACE-DOWN, the socket opening upward, so the face the thumb meets is the bed's and the socket's floor is printed before its walls. The socket bottoms on the stem's end: a push goes through the cap's full thickness, not through the press fit. PCTG, the knob's resin and the deck's"),
    "ui_knob": (lambda: heal(_m("ui_panel").knob()), "pctg/ui_knob.step", "PCTG - the UI cap: a O8 shank up through the deck and a O17 disc over it, bored O2.6x1.8 for the Alps shaft's tip. Prints DISC-DOWN (its own flat face on the bed), so the shank and the bore are both vertical and the bore's ceiling is the last thing printed. PCTG because it is the one part of the instrument a player touches every time they change a setting, and the deck it sits on is the same resin"),
    "saw_jig": (
    lambda: heal(_m("saw_jig").body()),
    "tools/saw_jig.step",
    "TOOL — hacksaw jig for cutting the ten Tr8x2 leadscrews to SCREW_LEN by hand with one Quick-Grip and no vise: the rod rests on two crests in a 90 deg V tunnel, the saw slot (1.3, McMaster 6927A16) sits 5.6 past the clamped support, and the piece overhangs an OPEN fork to a fixed end stop at SCREW_LEN + 0.4, then drops out. The table-edge notch goes on the table edge so a slipped blade hits the jig. PETG, printed as drawn"),
    "motor_shaft_saw_jig": (
    lambda: heal(_m("motor_shaft_saw_jig").body()),
    "tools/motor_shaft_saw_jig.step",
    "TOOL — the leadscrew saw jig's sibling for cutting each SERVO42D's shaft to components.MOTOR_SHAFT_CUT_L, no screws: the motor drops into a copy of the v1 chassis bay (motor_shaft_saw_jig's own lift_prism + low_walls, the bay's boss slot), faceplate pushed home on a 1.6 lip, shaft on a cradle rib its full length to a 1.3 saw slot (McMaster 6927A16) at the cut plane with a 3.2 cheek each side, the motor-side cheek braced by two 45 deg gussets; 1.6 floor and bay walls to the shaft axis. NO CAP: the Quick-Grip pad goes straight on the motor. PETG-GF on the 0.8, printed as drawn"),
    "saw_jig_cap": (
    lambda: heal(_m("saw_jig").cap()),
    "tools/saw_jig_cap.step",
    "TOOL — the saw jig's cap: a plunger down the clamp channel whose 45 deg notch seats on the rod's upper crests, with a rimmed pocket on top for the Quick-Grip pad. The clamp squeezes cap, rod, jig and table in one stack. PETG, printed as drawn (notch on the bed)"),
    "screw_spin_jig": (
    lambda: heal(_m("direct_bench").screw_spinner()),
    "tools/screw_spin_jig.step",
    "TOOL — runs a leadscrew in fast at install: collar A's clamp body (formed thread, split, M3 x 10 into the insert used as a nut) clamped on the screw's motor end, on a 3/8 in hex shank (9.55 AF, 8 long: the hex_fit_38 coupon's best) for a driver's 3/8 in hex socket. A cap bridges the bore on the body's top, the screw bottoming on it from the bed side; the hex straight on the cap; the split runs through all. PETG-GF on the 0.8, printed as collar A, its -X face on the bed"),
    "pin_drill_jig": (
    lambda: heal(_m("pin_drill_jig").body()),
    "tools/pin_drill_jig.step",
    "TOOL — drill jig for the cross hole that pins a Tr8x2 leadscrew into the printed motor coupler: the saw jig's diamond tunnel and Quick-Grip cap (print a second saw_jig_cap), an end stop that puts the hole 6.0 from the screw's end, and a tower over the rod taking drop-in bushings (1/16 pilot, then 1/8 through for the belt clamp's M3 x 12), an exit hole under. PETG-GF, printed as drawn (table face on the bed)"),
    "pin_drill_bushing_pilot": (
    lambda: heal(_m("pin_drill_jig").bushing("pilot")),
    "tools/pin_drill_bushing_pilot.step",
    "TOOL — the pin drill jig's 1/16 in pilot bushing: Ø10 tube, 28 of guide, a Ø14 flange on the tower's top. PETG-GF, printed flange down"),
    "pin_drill_bushing_pin": (
    lambda: heal(_m("pin_drill_jig").bushing("pin")),
    "tools/pin_drill_bushing_pin.step",
    "TOOL — the pin drill jig's 1/8 in bushing: Ø10 tube, 28 of guide, a Ø14 flange on the tower's top. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_1": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_1"]),
    "tools/pin_drill_bushing_pilot_1.step",
    "TOOL -- trial 1/16 in pilot bushing 1 of 3 (bore = bit + PILOT_TRY[0], 1 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_2": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_2"]),
    "tools/pin_drill_bushing_pilot_2.step",
    "TOOL -- trial 1/16 in pilot bushing 2 of 3 (bore = bit + PILOT_TRY[1], 2 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "pin_drill_bushing_pilot_3": (
    lambda: heal(dict(_m("pin_drill_jig").pilot_trials())["pin_drill_bushing_pilot_3"]),
    "tools/pin_drill_bushing_pilot_3.step",
    "TOOL -- trial 1/16 in pilot bushing 3 of 3 (bore = bit + PILOT_TRY[2], 3 scallop(s) on the flange): keep the one that is tight but runs the bit through. PETG-GF, printed flange down"),
    "ream_jig": (
    lambda: heal(_m("ream_jig").jig()),
    "tools/ream_jig.step",
    "TOOL — reaming jig for one ear of the Tr8x2 H-flange nut (9/64\" reamer, McMaster 2995A116): the nut slides in from the side BOSS DOWN, its flats on the slot walls so it cannot turn, the ear on the floor; a 44.6 channel over the ear holds the reamer vertical. Every ceiling is a 45 deg gable. PETG-GF, printed as drawn (table face on the bed)"),
    "guide_rod_saw_jig": (
    lambda: heal(_m("guide_rod_saw_jig").body()),
    "tools/guide_rod_saw_jig.step",
    "TOOL — hacksaw jig for cutting each 2 ft length of 3/16 in stainless (McMaster 89535K84) into three guide rods of direct_bench.ROD_L (202.5), with one Quick-Grip and no vise: the whole jig sits on the table; the stock rests in a short diamond-tunnel guide -X of a 1.3 saw slot (McMaster 6927A16), and the piece lies in a supported 90 deg V trough out to an end stop at ROD_L from the slot's +X face, clamped next to the slot through the LEADSCREW JIG'S CAP (saw_jig_cap: no cap of its own). 217 x 41. PETG, printed as drawn (table face on the bed)"),
    "spring_saw_jig": (
    lambda: heal(_m("spring_saw_jig").body()),
    "tools/spring_saw_jig.step",
    "TOOL — hacksaw jig for cutting each 20 in length of the nut spring stock (McMaster 9665K36) into 42-coil pieces (direct_bench.SPRING_COILS, 97.0) with one Quick-Grip and no vise or screws: one straight cut square to the axis parts the close-wound spring along one turn, its flat end butting the stop for the next piece. The guide rod jig's sibling: the stock rests in a diamond-tunnel guide -X of a 1.3 saw slot (McMaster 6927A16), the piece in a supported 90 deg V trough out to an end stop at 97.0 from the slot's +X face, clamped next to the slot through the LEADSCREW JIG'S CAP (saw_jig_cap, riding the spring on its notch's edges). PETG-GF, printed as drawn (table face on the bed)"),
    "key_seat_plate": (lambda: _m("direct_bench").key_seat_plate(), "steel/key_seat_plate.step", "LASER-CUT 304 STAINLESS, 4 mm, x10 (JLCCNC, no finish): under the keyhole plate, on the yoke -- the same outline, hole, slit and screw holes, and a Ø4.3 hole round the slit's top that the ball sinks right into under tension (its whole 3 mm length and 1 over), so it cannot tip or slide back to its hole. Not printed"),
    "keyhole_plate": (lambda: _m("direct_bench").keyhole_plate(layer="plate"), "steel/keyhole_plate.step", "LASER-CUT 304 STAINLESS, 3 mm, x10 (JLCCNC, no finish): the direct-drive yoke's roof, over the 4 mm key_seat_plate (3 + 4 = 7; the ball's seat is the lower sheet, 4 deep). The ball pulls on this one. The string's ball end bears on it; two EARS past the nut's flange, each with a Ø3.4 CLEAR hole (no tapping): the stack's M3 x 40s go in from +X, heads on this plate, through the yoke's ears beside the flange into inserts used as nuts in the collar's ears. Not printed"),
}
# ONE PRINT, TWO FILAMENTS, ONE FILE (user, 2026-11-03). A part named here is a body of
# the part it maps to: the two share a STEP, each its own named product, so Bambu loads
# the file as one object with one part per filament (cadkit export_print_parts). Each
# keeps its own PARTS row -- its own volume, its own material in part_volumes.json, its
# own checks -- but its "path" is the file it is written INTO, and FILAMENT_OF says what
# it is made of, since its folder is the bulk's. The file goes where the bulk is.
PRINTS_WITH: dict = {}
# THE DIRECT DRIVE'S PER-STRING PRINTS (user, 2026-11-16: "why does each part have 10 copies? Are
# they all identical?"): a family's leader -> (file stem, material, its members). Its export
# writes ONE STEP PER DISTINCT SHAPE (_export_family), named for the strings that print it.
STRING_FAMILIES: dict = {}
FILAMENT_OF: dict = {}


# Anchor ALL outputs to the project folder (never the cwd)
OUT = pathlib.Path(__file__).resolve().parents[1]


# ── PRINT ORIENTATION — one declaration per printed part ─────────────────────
# cadkit requires it and export_print refuses a part without it, because a MISSING bed face
# used to be indistinguishable from a deliberate "models as printed". Each module declares
# its parts' build DIRECTION as a module-level constant (PRINT_UP, LEVER_UP, BAR_UP ...),
# with its reasoning beside it; this collects them, and PrintOrientation.from_build_dir
# turns each into the pose the STEP is written in. A part no module declares exports as
# modelled and is marked confirmed=False; the build names those on every run.
def _declared():
    UI = _m("ui_panel")
    SJG, MSJ, RJG = _m("saw_jig"), _m("motor_shaft_saw_jig"), _m("ream_jig")
    out = {}
    for _names, _up, _why in (
        (["ui_knob"], UI.KNOB_UP,
         "ui_panel.KNOB_UP — DISC-DOWN, on the flat top face it presents to the player. Every "
         "other way up puts the shaft bore blind end over air"),
        (["ui_clamp"], UI.CLAMP_UP,
         "ui_panel.CLAMP_UP — flat underside on the bed, every pad, rib and post growing "
         "straight up off it"),
        (["saw_jig"], SJG.BODY_UP,
         "saw_jig.BODY_UP — as drawn, table face on the bed: the V and roof of the rod tunnel "
         "and the fork's arch are all 45 deg"),
        (["ream_jig"], RJG.PRINT_UP,
         "ream_jig.PRINT_UP — standing as it is used, table face on the bed: the nut slot and "
         "the reamer channel both print round their own axis, every ceiling a 45 deg gable"),
        (["motor_shaft_saw_jig"], MSJ.BODY_UP,
         "motor_shaft_saw_jig.BODY_UP — as drawn, table face on the bed: the bay, the boss "
         "slot, the shaft channel and the saw slot all open upward; the gussets rise at 45 deg"),
        (["screw_spin_jig"], _m("direct_bench").COLLAR_A_UP,
         "direct_bench.COLLAR_A_UP — as collar A, its -X face on the bed: the flat cap bridges the bore, "
         "the hex stands on it, the pockets peaked +X as the collar's"),
        (["saw_jig_cap"], SJG.CAP_UP,
         "saw_jig.CAP_UP — as drawn: the rod notch's two 45 deg faces rise off the bed, the "
         "pad pocket opens up"),
    ):
        for _n in _names:
            out[_n] = PO.from_build_dir(_up, _why)
    # Declared by its module, but NOT YET CONFIRMED by the user (2026-10-12).
    out["ui_pwr_cap"] = PO.from_build_dir(
        UI.PWR_CAP_UP,
        "ui_panel.PWR_CAP_UP — top face on the bed, the stem's socket opening upward. Measured "
        "that way up: no ceiling and no curved overhang. Chosen, not yet confirmed",
        confirmed=False)
    return {k: v for k, v in out.items() if k in PARTS}


PRINT_ORIENTATION = _declared()
for _n, (_b, _path, _note) in PARTS.items():
    if _n in PRINT_ORIENTATION:
        continue
    # NOT a decision -- a RECORD of what this part's STEP has always exported as.
    PRINT_ORIENTATION[_n] = PO(
        None,
        "as modelled — what this part's STEP has always exported as. UNSTUDIED. The part "
        "note says: " + " ".join((_note or "(nothing about printing)").split())[:300],
        confirmed=False)


# The instrument's materials, and there are THREE (user, 2026-09-30): PETG-GF for the
# body, PCTG for the deck and fine-feature parts, TPU for the feet. Plain PETG was here
# for exactly three parts -- v1's chassis light windows -- and buying a fourth spool for
# three translucent strips is the opposite of what this instrument is for.
MATERIALS = ("petg-gf", "pctg", "tpu")


def _material_of(path):
    """The material folder a part exports into, or None.

    ⚠ NOT path.split("/")[0]. Test coupons were written at the root and shop tools into
    tools/, so that returned "test_cover_plate.step" and "tools" as materials and
    tools/cost.py then had no filament price for either (lead, 2026-09-30). A part
    outside the material folders has no filament cost to attribute, and saying None is
    how cost.py knows to leave it out rather than guess."""
    head = path.split("/")[0]
    return head if head in MATERIALS else None


# ── WHERE A BUILD'S TIME GOES ────────────────────────────────────────────────────────
# One line per stage at the end of every build (lead, 2026-10-09: the log timed two
# gates and nothing else, so nobody could say what a ten-minute build spent its ten
# minutes on). Cut where this says the time is, not where it is assumed to be.
_STAGES: list = []


@contextlib.contextmanager
def _stage(label):
    t = time.perf_counter()
    try:
        yield
    finally:
        _STAGES.append((label, time.perf_counter() - t))


def _stage_add(label, seconds):
    for i, (k, s) in enumerate(_STAGES):
        if k == label:
            _STAGES[i] = (k, s + seconds)
            return
    _STAGES.append((label, seconds))


def _report_stages():
    total = sum(s for _, s in _STAGES)
    print("BUILD TIME by stage (%.0f s):" % total)
    for label, s in _STAGES:
        print("  %7.1f s  %4.1f %%  %s" % (s, 100.0 * s / total if total else 0.0, label))
    sys.stdout.flush()


def _shape_sig(shape):
    """A rigid-motion-free signature: volume, area and the principal radii of gyration^2."""
    import numpy as np
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    w = getattr(shape, "wrapped", shape)
    g, a = GProp_GProps(), GProp_GProps()
    BRepGProp.VolumeProperties_s(w, g)
    BRepGProp.SurfaceProperties_s(w, a)
    m = g.MatrixOfInertia()
    eig = np.linalg.eigvalsh(np.array([[m.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]))
    v = g.Mass()
    return v, a.Mass(), tuple(float(e) / v for e in eig)


def _same_shape(p, q) -> bool:
    return (abs(p[0] - q[0]) <= 1e-6 * max(abs(p[0]), 1.0) + 1e-3
            and abs(p[1] - q[1]) <= 1e-6 * max(abs(p[1]), 1.0) + 1e-3
            and all(abs(x - y) <= 1e-3 for x, y in zip(p[2], q[2])))


def _string_no(n: str) -> int:
    return int(n.rsplit("_", 1)[1]) + 1


PRINT_LIST = OUT / "PRINT_LIST.md"


def _print_list_update(paths_gone, rows):
    """PRINT_LIST.md: one row per direct-drive STEP (path, quantity, strings), rewritten in place."""
    keep = {}
    if PRINT_LIST.exists():
        for ln in PRINT_LIST.read_text(encoding="utf-8").splitlines():
            if ln.startswith("| `") and (OUT / ln.split("`")[1]).exists():   # a part no longer
                keep[ln.split("`")[1]] = ln                                       # built drops out
    for p in paths_gone:
        keep.pop(p, None)
    for p, n, what in rows:
        keep[p] = f"| `{p}` | {n} | {what} |"
    PRINT_LIST.write_text(
        "# Direct drive: what to print\n\nGenerated by `src.build` (one STEP per distinct shape; "
        "the quantity is how many to print).\n\n| file | qty | strings |\n|---|---|---|\n"
        + "\n".join(keep[k] for k in sorted(keep, key=_natural)) + "\n", encoding="utf-8")


def _natural(k: str):
    """housing_s2 before housing_s10."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", k)]


# ── A STEP IS WRITTEN ONLY WHEN WHAT IS IN IT CHANGED (user, 2026-11-16: "changing parts should
# automatically use cached data as much as possible") ─────────────────────────────────────────
# Each file's key: the content names of the bodies in it (cadkit.kept tags every result with its
# content's sha1; anything else is hashed from its BREP), their names, and the print pose. The
# file is skipped when it exists and its key is the one it was written with (.step_keys.json).
_STEP_KEYS_FILE = OUT / ".step_keys.json"
_STEP_KEYS: dict = {}
_STEP_KEY_V = 1
_PRODUCED: set = set()          # every STEP this run wrote or found current (rel to OUT)


def _sweep_stale_steps():
    """After a FULL build: delete every .step in a folder the build writes into that this run
    did not produce (user, 2026-11-17: a part that leaves the build takes its file with it).
    Only the folders PARTS' paths name, and only their own *.step, not subfolders."""
    dirs = {(OUT / path).parent for _b, path, _n in PARTS.values()}
    gone = sorted(f for d in dirs for f in d.glob("*.step")
                  if f.resolve().relative_to(OUT.resolve()).as_posix() not in _PRODUCED)
    for f in gone:
        f.unlink()
        _STEP_KEYS.pop(f.resolve().relative_to(OUT.resolve()).as_posix(), None)
        print(f"  removed stale {f.resolve().relative_to(OUT.resolve()).as_posix()}")
    if gone:
        _STEP_KEYS_FILE.write_text(json.dumps(_STEP_KEYS, indent=0, sort_keys=True), encoding="utf-8")


def _content_token(o) -> str:
    from cadkit.kept import _shape_token
    tag = getattr(o, "_cadkit_kept", None)
    if tag:
        return "kept:" + tag
    shapes = o.vals() if hasattr(o, "vals") else [o]
    return "|".join(_shape_token(x) if isinstance(x, cq.Shape) else repr(x) for x in shapes)


def _write_print(dest: pathlib.Path, bodies, orientation) -> bool:
    """export_print / export_print_parts of [(name, obj)] to `dest`, unless it is already that.
    True if it was written."""
    import hashlib
    if not _STEP_KEYS and _STEP_KEYS_FILE.exists():
        try:
            _STEP_KEYS.update(json.loads(_STEP_KEYS_FILE.read_text(encoding="utf-8")))
        except ValueError:
            pass
    rel = dest.resolve().relative_to(OUT.resolve()).as_posix()
    key = hashlib.sha1(json.dumps([_STEP_KEY_V, [(n, _content_token(o)) for n, o in bodies],
                                   repr(orientation.rot)]).encode()).hexdigest()
    _PRODUCED.add(rel)
    if dest.exists() and _STEP_KEYS.get(rel) == key:
        return False
    if len(bodies) == 1:
        export_print(bodies[0][1], orientation, str(dest))
    else:
        export_print_parts(bodies, orientation, str(dest))
    _STEP_KEYS[rel] = key
    _STEP_KEYS_FILE.write_text(json.dumps(_STEP_KEYS, indent=0, sort_keys=True), encoding="utf-8")
    return True


def _export_family(leader):
    """Every member of `leader`'s family built (kept: cached), grouped by shape, ONE STEP per
    distinct shape. One shape: `stem.step`. Several: the most common (if one is) keeps `stem`,
    the rest `stem_s<strings>`. Stale files of the family (a merged name, a shape gone) go."""
    stem, mat, members = STRING_FAMILIES[leader]
    built, groups = {}, []
    for n in members:
        t = time.perf_counter(); wp = PARTS[n][0](); built[n] = (wp, time.perf_counter() - t)
        sig = _shape_sig(wp.val() if hasattr(wp, "val") else wp)
        for g in groups:
            if _same_shape(g[0], sig):
                g[1].append(n)
                break
        else:
            groups.append((sig, [n]))
    sizes = sorted((len(g[1]) for g in groups), reverse=True)
    main = None
    if len(groups) == 1 or (sizes[0] > 1 and sizes[0] > sizes[1]):
        main = max(groups, key=lambda g: len(g[1]))
    d = OUT / mat
    d.mkdir(parents=True, exist_ok=True)
    written, rows = [], []
    for g in groups:
        ms = g[1]
        nos = sorted({_string_no(n) for n in ms})
        fn = stem if g is main else stem + "_" + "_".join(f"s{k}" for k in nos)
        rep_ = ms[0]
        t = time.perf_counter()
        wrote = _write_print(d / f"{fn}.step", [(rep_, built[rep_][0])], PRINT_ORIENTATION[rep_])
        export_s = time.perf_counter() - t
        _stage_add("printed parts: STEP export", export_s)
        names = sorted({n.rsplit("_", 1)[0] for n in ms})
        by = "; ".join(f"{nm} " + ",".join(f"S{_string_no(n)}" for n in ms if n.rsplit("_", 1)[0] == nm)
                       for nm in names) if len(names) > 1 else ",".join(f"S{k}" for k in nos)
        written.append(f"{fn}.step")
        rows.append((f"{mat}/{fn}.step", len(ms), by))
        for n in ms:
            wp, build_s = built[n]
            record_part(n, build_s, export_s if n == rep_ else 0.0,
                        wp.val() if hasattr(wp, "val") else wp, material=mat)
            _stage_add("printed parts: build", build_s)
        print(f"{'Wrote' if wrote else 'Unchanged'} {mat}/{fn}.step  x{len(ms)}  ({by})")
    olds = {f"{stem}.step"} | {p.name for p in d.glob(f"{stem}_s*.step")} \
        | {f"{n.rsplit('_', 1)[0]}.step" for n in members}
    gone = [f"{mat}/{f}" for f in sorted(olds) if f not in written and (d / f).exists()]
    for f in gone:
        (OUT / f).unlink()
        print(f"  removed stale {f}")
    _print_list_update(gone + [f"{mat}/{f}" for f in sorted(olds) if f not in written], rows)


def _export(name):
    """Build `name` and write its print STEP, with every body that prints with it
    (PRINTS_WITH) in the same file. A body that prints with another is written by that
    one's export, so on its own it is passed over."""
    if name in PRINTS_WITH:
        return
    if name in STRING_FAMILIES:
        return _export_family(name)
    builder, path, note = PARTS[name]
    dest = OUT / path
    dest.parent.mkdir(parents=True, exist_ok=True)   # material folder (petg-gf/pctg/tpu)
    bodies = [name] + [n for n, into in PRINTS_WITH.items() if into == name]
    built = {}
    for n in bodies:
        t = time.perf_counter(); wp = PARTS[n][0](); built[n] = (wp, time.perf_counter() - t)
    t = time.perf_counter()
    wrote = _write_print(dest, [(n, built[n][0]) for n in bodies], PRINT_ORIENTATION[name])
    export_s = time.perf_counter() - t
    for n in bodies[1:]:
        (OUT / FILAMENT_OF[n] / f"{n}.step").unlink(missing_ok=True)   # its own file, from before
    for n in bodies:
        wp, build_s = built[n]
        record_part(n, build_s, export_s if n == name else 0.0,
                    wp.val() if hasattr(wp, "val") else wp,
                    material=FILAMENT_OF.get(n) or _material_of(path))   # ~free profiling + volume hook
        _stage_add("printed parts: build", build_s)
    _stage_add("printed parts: STEP export", export_s)
    print(f"{'Wrote' if wrote else 'Unchanged'} {path}" + (f"  ({' + '.join(bodies)})" if len(bodies) > 1 else "")
          + (f"  ({note})" if note else ""))


_BUILD_COUNTER_FILE = pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_counter.txt"


def _bump_build_counter() -> int:
    try:
        n = int(_BUILD_COUNTER_FILE.read_text().strip()) + 1
    except (OSError, ValueError):
        n = 1
    try:
        _BUILD_COUNTER_FILE.write_text(f"{n}\n")
    except OSError:
        pass
    return n


def collect_components(t=None):
    """EVERY placed thing in the instrument: [(name, cq.Workplane), ...].

    THE DIRECT-DRIVE INSTRUMENT (user, 2026-11-13: the main build is src.direct_bench's
    instrument; v1 is at the git tag v1-instrument). Each part is drawn where it sits at
    T_OPEN, every one its own kept() entry; the pickup is still its stand-in (ghost_pickup).
    The levers, the legs and the pedal bar get redesigned for this body (user, 2026-11-17).

    The one entry point the whole tool chain is built on -- the overlap and sweep gates, the
    GLB exporter, scratch_view and the build profiler all take their model from here, so a
    part that is not in this list is invisible to every check in the project. Names matter
    beyond display: the gates key their allow-lists on them (its pairs are judged by
    direct_bench.is_intended)."""
    from . import direct_bench as DB
    from . import new_boards_view as NB
    # THE ROUTED BOARDS ARE GATED (lead, 2026-11-19): the brain board's CM5 sat 2-3 mm from the
    # UI station with nothing checking it, because only branner's ob_board stand-in (the parts
    # that reach the endplate) was in this list. new_boards_view draws bronner's boards from
    # their geom exports; ob_board keeps only what they do not have (courtyards and unclipped
    # tails, the endplate pocket's sizes), so nothing is gated twice.
    # t: the drive's travel (the drive-travel gate redraws the instrument at each end); the
    # boards stand still, but they are in the model at every t -- that gate printed 662 of 676
    # when it drew DB.assembly(t) alone (lead, 2026-11-19)
    return DB.assembly(DB.T_OPEN if t is None else t) + NB.boards()


from . import board_geom as _BG  # noqa: E402
from . import servo42d as _SV    # noqa: E402

# THE COLOUR TABLE: every name the direct assembly resolves through it (measured over the
# assembly at T_OPEN and at both ends of the travel, lead 2026-11-17; the v1 instrument's
# 258 other entries went with it). direct_bench.color_of aliases its own parts into these
# keys (the body draws as `chassis`, a spring as
# `leg_latch_spring`), which is why some names here are not parts of this instrument.
_COLORS = {
    "bridge_bearings": (0.69, 0.77, 0.87),
    "chassis": (0.46, 0.52, 0.55),
    "guide_rod": (0.35, 0.35, 0.38),
    "leadscrew": (0.75, 0.75, 0.78),
    "leg_latch_spring": (0.62, 0.64, 0.67),
    "nut": (0.82, 0.60, 0.20),
    "nut_plate": (0.80, 0.81, 0.83),
    "pickup": (0.10, 0.10, 0.12),
    "pickup_jack_insert": (0.80, 0.60, 0.35),
    "pickup_jack_screw": (0.55, 0.55, 0.58),
    "screw_bearing": (0.69, 0.77, 0.87),
    "set_screw": (0.55, 0.55, 0.58),
    "string": (0.85, 0.85, 0.85),
    "string_nut": (0.82, 0.60, 0.20),
    "wall_bar": (0.55, 0.58, 0.62),                  # steel flat bar
    # the UI station (src/ui_panel.py)
    "ui_clamp": (0.36, 0.30, 0.42),
    "ui_disp_ffc_socket": (0.90, 0.86, 0.72),
    "ui_display": (0.16, 0.16, 0.18),
    "ui_ffc": (0.93, 0.93, 0.90),
    "ui_ffc_contacts": (0.78, 0.79, 0.80),
    "ui_ffc_stiffener": (0.12, 0.35, 0.80),
    "ui_insert": (0.72, 0.60, 0.38),
    "ui_knob": (0.15, 0.15, 0.17),
    "ui_pcb": _BG.mask("ui_board"),
    # the new boards' view (src.new_boards_view): its board names, gone with the v1 table in
    # round 3 and needed by bronner's tab (a board must be a solder-mask colour)
    "brain_board_pcb": _BG.mask("brain_board"),
    "connector_board_pcb": _BG.mask("connector_board"),
    "brain_board_cm5": _BG.mask_rgb("green"),        # the CM5's own board, as Raspberry Pi make it
    "ui_pcb_silk": (0.95, 0.95, 0.93),
    "ui_pwr_cap": (0.15, 0.15, 0.17),
    "ui_pwr_stem": (0.94, 0.94, 0.92),
    "ui_screen": (0.004, 0.004, 0.005),
    "ui_screen_lit": (0.93, 0.96, 1.0),
    "ui_screw": (0.62, 0.64, 0.67),
    "ui_shaft": (0.62, 0.64, 0.67),                  # the encoder's steel shaft
}
# the SERVO42D's parts take the colours it was measured in (src/servo42d.py LOOK)
_COLORS.update({("motor_" + _k) if _k else "motor": _rgb for _k, (_rgb, _) in _SV.LOOK.items()})
_TPU_BLACK = (0.03, 0.03, 0.03)                  # ALL TPU parts render black (user rule)
# every part whose output path is tpu/... -> black, regardless of instance prefix/suffix
_TPU_BASES = tuple(sorted((k for k, v in PARTS.items() if v[1].startswith("tpu/")), key=len, reverse=True))


def _color_for(name):
    # STRIP EVERY TRAILING INDEX GROUP, not just the last one -- the same lesson
    # tools.check_overlaps.base() records, and this resolver had not learned it. A part
    # numbered twice (`wire_canb_gnd_0_0`: net, segment, half) kept one index after a
    # single strip, matched nothing in _COLORS, and came out the default white. The
    # overlap gate had already been bitten by exactly this and fixed; colours had not.
    base = re.sub(r"(_\d+)+$", "", name)
    if base in _TPU_BASES or any(base.endswith(k) for k in _TPU_BASES):
        return cq.Color(*_TPU_BLACK)             # TPU is always black
    if base in _COLORS:
        return cq.Color(*_COLORS[base])
    from . import direct_bench as _DB            # the instrument's own table (src.direct_bench)
    if _DB.owns(base):
        _c = _DB.color_of(base, _COLORS)
        if _c is not None:
            return cq.Color(*_c)
    # ⚠ NO DEFAULT COLOUR (user, 2026-11-14). A name nothing here knows used to come out
    # _DEFAULT_COLOR, white -- a new board read as a white-mask PCB and nothing said so. It
    # fails the build instead: add the part to _COLORS (or its module's own table).
    raise KeyError("build: no colour for part %r (base %r) -- add it to src/build.py _COLORS "
                   "or its module's colour table; there is no default" % (name, base))


def _export_assembly(publish=True, gate=True, gate_full=True):
    build_n = _bump_build_counter()
    with _stage("assembly: collect_components"):
        comps = collect_components()
    print(f"Assembled {len(comps)} components  [build #{build_n}]", flush=True)
    # THE ASSEMBLY IS THIS LIST, NOT A FILE. Nothing read the one-file STEP of it but a
    # viewer, and the viewer is given the list. The printed parts' own STEPs are above.
    # Each component is left behind on its own instead, where every worktree's scratch
    # view takes its surroundings from (cadkit.scratch): only the lead's build writes it.
    with _stage("shared cache for the scratch views"):
        from cadkit.scratch import publish_cache
        publish_cache(comps, OUT, build=build_n)
    rc = _web_view(comps, build_n, publish)
    # LAST: the gate spawns a worker pool, so run it once the viewer is refreshed — a
    # gate hiccup can never cost the build.
    if gate:
        # every gate always runs, so one RED doesn't hide another's result
        for label, fn in (("gate: overlaps", lambda: _report_overlaps(comps, full=gate_full)),
                          ("gate: sweep", lambda: _report_sweep(comps)),
                          ("gate: drive travel", lambda: _report_drive_travel(comps)),
                          ("gate: world pose", lambda: _report_world_pose(comps)),
                          ("gate: dead code", _report_dead)):
            with _stage(label):
                rc |= fn()
    _report_stages()
    return rc


# The overlap gate's ACCEPTED baseline: the count of REAL defects tracked
# elsewhere. The build fails ABOVE it, so a NEW overlap still stops it, and it must
# always equal the count you can NAME -- a baseline kept above the real number is
# just a licence for the next fault to arrive unnoticed.
# NOTHING IS ACCEPTED: every unintended pair is a regression and stops the build, which is
# what the rule above is for.
OVERLAP_BASELINE = 0


def _report_overlaps(comps, full=False) -> int:
    """Run the overlap gate on the model we JUST built, and return 1 on regression.

    This is the whole point of folding the gate into the build: the scan is seconds
    on a warm pair cache, but ``tools.check_overlaps`` run standalone spends MINUTES
    rebuilding the model first. Reusing ``comps`` makes a full-tree gate essentially
    free, so the lead never has to choose between gating and building.
    """
    try:
        from tools.check_overlaps import gate
        n = gate([(name, wp.val()) for name, wp in comps], full=full)
    except Exception as e:               # noqa: BLE001 — a gate crash must not eat the geometry
        print(f"overlap gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    if n > OVERLAP_BASELINE:
        print(f"OVERLAP GATE: RED — {n} unintended pairs "
              f"({n - OVERLAP_BASELINE} NEW above the accepted {OVERLAP_BASELINE})",
              flush=True)
        return 1
    print(f"OVERLAP GATE: green — {n} unintended pair(s), "
          f"accepted baseline {OVERLAP_BASELINE}", flush=True)
    return 0


def _report_world_pose(comps) -> int:
    """A printed part drawn ONCE must be authored where it sits, not rotated or mirrored into
    place (user, 2026-10-22) -- tools/check_world_pose. The PARTS solids are the ones the
    export above already built, so this costs the vertex fits only."""
    try:
        from tools.check_world_pose import gate
        parts = {n: (lambda s: s.val() if hasattr(s, "val") else s)(PARTS[n][0]()) for n in PARTS}
        return 1 if gate(parts, [(name, wp.val()) for name, wp in comps]) else 0
    except Exception as e:               # noqa: BLE001 — a gate crash must not eat the geometry
        print(f"world-pose gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0


def _report_sweep(comps) -> int:
    """Swept-envelope gate on the model we JUST built (see _report_overlaps for why
    reusing ``comps`` matters). This catches the class ``check_overlaps`` is
    STRUCTURALLY blind to: a part that clears everything at rest and fouls once it
    turns. Baseline is 0 — unlike the overlap gate there is no inherited debt."""
    try:
        from tools.check_sweep import gate
        n = gate([(name, wp.val()) for name, wp in comps])
    except Exception as e:               # noqa: BLE001 — never let a gate eat the geometry
        print(f"sweep gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    print(f"SWEEP GATE: {'green' if n == 0 else f'RED — {n} swept collision(s)'}", flush=True)
    return 1 if n else 0


def _report_drive_travel(comps) -> int:
    """THE DRIVE OVER ITS TRAVEL (replaces v1's carriage-travel gate, 2026-11-13): the overlap
    gate sees every string at T_OPEN, so this redraws the instrument with every string at
    each end of its travel (t 0 and 1) and gates that. Only the parts that move are new
    pairs; the rest come from the pair cache. Baseline is 0."""
    try:
        from tools.check_overlaps import gate
        n = 0
        for t in (0.0, 1.0):
            print(f"drive travel: every string at t = {t:.0f}", flush=True)
            n += gate([(name, wp.val()) for name, wp in collect_components(t)], full=True)
    except Exception as e:               # noqa: BLE001 -- never let a gate eat the geometry
        print(f"drive travel gate: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    print(f"DRIVE TRAVEL GATE: {'green' if n == 0 else f'RED -- {n} pair(s) meet at an end of the travel'}",
          flush=True)
    return 1 if n else 0


def _report_dead() -> int:
    """Source drift, not geometry: module-level definitions nothing in the repo names
    any more. REPORT ONLY -- it never fails the build. Retired parts leave their
    builders behind (the electronics tray left nine), and the cost of that is a reader
    believing dead code is live, which is worth a line of output and not worth blocking
    an agent's merge over. See tools/check_dead.py for what counts as a use."""
    try:
        from tools.check_dead import scan, KNOWN
        dead = [d for d in scan() if d[2] not in KNOWN]
    except Exception as e:               # noqa: BLE001 -- never let a report eat a build
        print(f"dead-code report: SKIPPED ({type(e).__name__}: {e})", flush=True)
        return 0
    if dead:
        print(f"dead code: {len(dead)} unreferenced definition(s) -- "
              f"py -3.12 -m tools.check_dead", flush=True)
        for path, lineno, name in dead:
            print(f"    {path}:{lineno}  {name}()", flush=True)
    return 0


def _web_view(comps, build_n, publish=True):
    """The viewer's model, from the just-built components (reused — no second geometry
    pass, and every mesh is of a COPY): written to docs/, shown in the local page, and
    force-pushed to the gh-pages branch. Viewer or publish trouble (offline, not on main,
    auth) never fails an otherwise-good geometry build, WITH ONE EXCEPTION: boards whose
    components could not be drawn. That model is written with every board as its boxes,
    and it is neither shown nor published: the build is RED (returns 1), because a page
    of green boxes looks like a finished build to everyone but the person who knows the
    boards. The push itself is a no-op off the main branch (so agent worktrees don't
    publish) — see tools/publish_preview.py. Returns the build's exit code."""
    from cadkit.web import BoardsSkipped
    try:
        from cadkit.web import show_exported
        from tools.export_glb import build_glb
        from tools.export_rig import build_rig
        from tools.publish_preview import push_gh_pages
        with _stage("viewer: rig"):
            build_rig(build_n)                  # animation manifest (pivots + copedent)
        with _stage("viewer: mesh + write"):
            glb = build_glb(comps, build_n=build_n)   # full instrument, numbered
        with _stage("viewer: local page"):
            show_exported(glb.parent, root=OUT)
        if publish:
            with _stage("viewer: publish"):
                published = push_gh_pages(build_n)
            if published is False:               # it has said why; say it LAST as well
                print(f"⚠ web view: build #{build_n} is NOT on the public preview "
                      "(tools.publish_preview said why, above)", flush=True)
    except BoardsSkipped as e:
        print(f"🔴 web view: BOARDS NOT DRAWN — not shown, not published. {e}", flush=True)
        return 1
    except Exception as e:               # noqa: BLE001 — never let the viewer break a build
        print(f"web view: skipped ({type(e).__name__}: {e})", flush=True)
    return 0

# ── THE DIRECT INSTRUMENT'S PARTS (user, 2026-11-13: the main build is the direct instrument) ──
# ── THE DIRECT INSTRUMENT'S OWN PARTS (user, 2026-11-13: the main build is the direct instrument) ──
# families printed from one file under another name: collar A and B are ONE part (turned end for end)
_FAMILY_STEM = {"collar_a": "clamp_collar", "collar_b": "clamp_collar"}


def _direct_parts():
    """The direct instrument's own parts: each per-string printed part, one per string that has
    it, as drawn at T_OPEN; a family's members print from ONE STEP PER DISTINCT SHAPE
    (STRING_FAMILIES, _export_family); the body and the endplate; the anchor tray (laser cut, bent)."""
    from . import direct_bench as DB
    from cadkit.kept import kept
    out, with_ = {}, {}
    lead = {}                                         # (stem, material) -> the family's leader
    for nm, make, moves in DB._STRING_PARTS:
        mat = DB.MATERIAL.get(nm)
        if mat not in MATERIALS:
            continue
        stem = _FAMILY_STEM.get(nm, nm)
        for i in range(DB.N):
            if nm == "collar_a" and DB.coupler_is_collar(i):
                continue                              # the coupler is its collar A
            key = f"{nm}_{i}"
            args = (i, DB.T_OPEN) if moves else (i,)
            out[key] = (partial(kept, make, *args), f"{mat}/{stem}.step",
                        f"{mat.upper()} -- direct drive {nm}, string {i + 1} (PRINT_LIST.md: one "
                        f"STEP per distinct shape). src.direct_bench")
            ld = lead.setdefault((stem, mat), key)
            if ld == key:
                STRING_FAMILIES[key] = (stem, mat, [key])
            else:
                STRING_FAMILIES[ld][2].append(key)
                with_[key] = ld
    out["body"] = (partial(kept, DB._body), "petg-gf/body.step",
                      "PETG-GF -- the direct instrument's BODY: walls and floor to the endplate "
                      "joint, the bars' channels, the anchor's bosses and the brain board's "
                      "grooves. src.direct_bench._body")
    out["endplate"] = (DB.endplate_full, "petg-gf/endplate.step",
                          "PETG-GF -- the +X ENDPLATE (rod plate, axles, lanes, the bars' ends). "
                          "PRINTED +X -> -X. src.direct_bench._endplate")
    out["anchor"] = (partial(kept, DB._anchor), "steel/anchor.step",
                        "STAINLESS SHEET, laser cut and bent -- the spring anchor tray, on 8 "
                        "M4 x 10 into the wall bars. Not printed")
    # THE BODY ADAPTERS (user, 2026-11-17), one a corner, each its own STEP
    from . import body_adapter_v2 as BA
    for k, ex, ey in BA.corners():
        out[f"adapter_{k}"] = (partial(kept, BA.adapter, k), f"petg-gf/adapter_{k}.step",
                               f"PETG-GF -- body adapter, {'+X' if ex > 0 else '-X'}/{'+Y' if ey > 0 else '-Y'} "
                               "corner: the v1 leg half (blind mortise, latch pocket) under two X "
                               "tenons that slide into the body and the endplate. src.body_adapter_v2")
    return out, with_


_DP, _DW = _direct_parts()
from . import direct_bench as DB_
PARTS.update(_DP)
PRINTS_WITH.update(_DW)
FILAMENT_OF.update({k: v[1].split("/")[0] for k, v in _DP.items()})
PRINT_ORIENTATION = {k: v for k, v in PRINT_ORIENTATION.items() if k in PARTS}
PRINT_ORIENTATION["endplate"] = PO.from_build_dir(
    (-1, 0, 0), "direct_bench: the endplate PRINTS +X -> -X (user, 2026-11-13: a clean exterior, "
                "round holes along X); the axle bores peak -X, the lanes reach EP_DROOP into the "
                "rod plate for the bridge's sag")
for _n in [n for n in PARTS if n.startswith("collar_") and n[7:].isdigit()]:
    PRINT_ORIENTATION[_n] = PO.from_build_dir(
        DB_.COLLAR_UP, "direct_bench.COLLAR_UP: the collar PRINTS +X -> -X, its +X face on the bed (user, "
                    "2026-11-12, back to the original orientation); insert pockets under cone roofs")
# the rest of the drive's printed parts (user, 2026-11-14), each direction its module's constant
for _base, _up, _why in (
        ("collar_a", DB_.COLLAR_A_UP, "direct_bench.COLLAR_A_UP -- prints -X -> +X (0.8 nozzle; walls 0.8 at least round its "
                                       "holes and the boss); split through, the clamp insert from the bottom flat"),
        ("plug", DB_.PLUG_UP, "direct_bench.PLUG_UP -- prints -X -> +X; cones under the stop "
                              "flange and the insert pocket, the screw holes cut through the teeth"),
        ("yoke", DB_.YOKE_UP, "direct_bench.YOKE_UP -- prints +X -> -X, the plate's face on the bed: "
                              "the ears' feet grow up last, the nut-rim register widens going up"),
        ("collar_b", DB_.COLLAR_B_UP, "direct_bench.COLLAR_B_UP -- collar A's part turned end for "
                                      "end: the same print, boss last"),
        ("housing", DB_.HOUSE_UP, "direct_bench.HOUSE_UP -- prints +X -> -X: the lip on the bed, the "
                                  "pocket (half the bearing) and the bayonet's groove open on top; the lips "
                                  "over the teeth overhang 26 deg off vertical"),
        ("coupler", DB_.COLLAR_A_UP, "direct_bench._collar_local -- the coupler is the collar plus a "
                                     "shaft section: prints -X -> +X standing on its motor end, the 45 deg "
                                     "cone up to the clamp body, its pockets peaked +X as the collar's"),
        ("mplate", (1.0, 0.0, 0.0), "direct_bench._mplate -- flat, its motor face on the bed: every "
                                    "hole along the build, round"),
        ("lid", DB_.LID_UP,"direct_bench.LID_UP -- prints -X -> +X: the ties' heads' face on the bed, "
                            "its half of the bearing pocket and the bayonet's teeth on top (their slant "
                            "26 deg off vertical)")):
    for _n in [n for n in PARTS if n.startswith(_base + "_") and n[len(_base) + 1:].isdigit()]:
        PRINT_ORIENTATION[_n] = PO.from_build_dir(_up, _why)
from . import body_adapter_v2 as _BA
for _k, _, _ in _BA.corners():
    PRINT_ORIENTATION[f"adapter_{_k}"] = PO.from_build_dir(
        _BA.adapter_up(_k), "body_adapter_v2.adapter_up -- builds along X from its outer end face: the "
                            "X tenons' profile in the layers (N), their outer ends ramped 1.5:1")
for _n, (_b, _path, _note) in PARTS.items():
    if _n not in PRINT_ORIENTATION:
        PRINT_ORIENTATION[_n] = PO(
            None, "as modelled -- a direct-bench part with no declared print yet. UNSTUDIED. "
                  "The part note says: " + " ".join((_note or "").split())[:300], confirmed=False)
require_declared(set(PARTS), PRINT_ORIENTATION)


def _once(builder):
    """`builder`, built at most once a process: the export builds every part, and the world-pose
    gate wants the same solids (it re-read every kept part, 2026-11-16)."""
    box = []

    def built():
        if not box:
            box.append(builder())
        return box[0]
    return built


PARTS.update({_k: (_once(_b), _p, _nt) for _k, (_b, _p, _nt) in PARTS.items()})


_T_MAIN = time.perf_counter()           # everything above has been imported and built


def main() -> None:
    # Part notes carry Unicode (→, Ø, …); a cp1252 Windows console/pipe raises
    # UnicodeEncodeError mid-export and aborts the build. Force UTF-8 so a print
    # can never kill a good geometry build (replace = never crash on any glyph).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    # 🚩 an UNCONFIRMED bed face is a RECORD of how a part has been exported,
    # not a decision anyone checked. The bed face decides which faces are
    # overhangs, which slots bridge and which way every joint on the part
    # prints, so settle it with the user before working on one of these
    # (cadkit AGENTS.md). 41 of 63 parts here are in that state: the
    # instrument declares PRINT_UP per module, and these are the parts no
    # module covers.
    flagged = unconfirmed(PRINT_ORIENTATION)
    if flagged:
        print("UNCONFIRMED print orientation (%d of %d parts) — confirm with "
              "the user BEFORE working on one of these:\n  %s"
              % (len(flagged), len(PRINT_ORIENTATION), ", ".join(flagged)),
              flush=True)

    p = argparse.ArgumentParser(prog="src.build")
    p.add_argument("--part", help="Build only this printed part (skips assembly).")
    p.add_argument("--list", action="store_true", help="List part names and exit.")
    p.add_argument("--no-gate", action="store_true",
                   help="Skip the overlap gate (normally ~13 s on the built model).")
    # Belts are gated BY DEFAULT on the lead's build. It is the one authoritative
    # whole-tree check, and skipping belts is how far-row belts clipping near-row
    # pulley flanges (up to 9.8 mm^3) went out under a green gate. It costs ~225 s of
    # pairwise scan against ~15 s -- the price of the check meaning what it says.
    # Agents iterate with `view --gate`, which is where speed belongs.
    p.add_argument("--gate-fast", action="store_true",
                   help="Skip belts in the gate (~15 s scan vs ~225 s). Inner-loop only.")
    p.add_argument("--gate-full", action="store_true",
                   help="(default now; accepted for compatibility)")
    args = p.parse_args()
    _STAGES.insert(0, ("import (module-level geometry)", _T_MAIN - _T_IMPORT))

    if args.list:
        print("assembly")
        for name in PARTS:
            print(name)
        return
    gate, gate_full = not args.no_gate, not args.gate_fast
    if args.part:
        if args.part == "assembly":
            sys.exit(_export_assembly(gate=gate, gate_full=gate_full))
        if args.part not in PARTS:
            print(f"unknown part: {args.part!r}. Use --list.", file=sys.stderr)
            sys.exit(2)
        _export(PRINTS_WITH.get(args.part, args.part))
        return

    for name in PARTS:
        _export(name)
    _sweep_stale_steps()
    # ⚠ VOLUMES FIRST. report_build_regressions() ends by CLEARING the record list, so
    # writing the volumes after it wrote an empty file (found by the file being 100
    # bytes, lead 2026-09-30). Order matters here and nothing else would have said so.
    _n = write_part_volumes()           # what the plastic costs, for tools/cost.py
    if _n:
        print(f"wrote tools/part_volumes.json  ({_n} parts)")
    report_build_regressions()          # ~free: flags any part whose face count grew vs baseline
    sys.exit(_export_assembly(gate=gate, gate_full=gate_full))


if __name__ == "__main__":
    main()
