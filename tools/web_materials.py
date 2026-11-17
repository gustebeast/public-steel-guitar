"""What each part of the assembly is made of, for the viewer.

    material_of("ui_clamp")              ->  "petg-gf"    the filament it is printed in
    material_of("screw_bearing_3")       ->  "polished"   bought: its finish
    material_of("ui_insert_1")           ->  "brass"

The instrument's own parts (src.direct_bench) say their material themselves; the build's
PARTS table (src/build.py) says it for the rest: the folder of each STEP file,
"petg-gf/ui_clamp.step". An assembly instance is named after its part with index groups
after it (deck_white_3), so the name is reduced the way the build's own colour lookup
reduces it.

The viewer shows every part of one filament in that filament's colour and finish, the
instrument as it will come off the printer.

A part that is NOT printed gets a FINISH instead (cadkit/web/finishes.py: steel, brass,
rubber...), by what its name says it is, so a bearing does not look moulded. It keeps
its colour from the build; only the surface changes. A new bought part whose name fits
no rule below simply stays plain, and is listed by `py -3.12 -m tools.web_materials -v`.
"""

from __future__ import annotations

import functools
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
MATERIALS = ("petg-gf", "pctg", "tpu")
_PRINTED = ("nut_slide_insert", "belt_tensioner_half_a", "belt_tensioner_half_b")


@functools.lru_cache(maxsize=1)
def _table():
    """{part key: material} from src.build.PARTS: each part's material is the folder its STEP
    is written into (a body printed inside another part's file says its own, FILAMENT_OF).
    Read off the table itself, not parsed out of build.py's source: a regex over the source
    broke the moment the table's quoting changed (lead, 2026-11-17)."""
    from src import build as B
    exact = {k: path.split("/")[0] for k, (_b, path, _n) in B.PARTS.items()
             if path.split("/")[0] in MATERIALS}
    exact.update({k: m for k, m in B.FILAMENT_OF.items() if m in MATERIALS})
    return exact, []


# WHAT A BOUGHT PART IS, FROM ITS NAME. First match wins; searched in the name with its
# index groups off (screw_bearing, ui_insert).
def _motor_rules():
    """The SERVO42D's parts, each its own material (src/servo42d.py LOOK says which)."""
    from src.servo42d import LOOK
    return tuple((r"^motor_%s$" % k, fin) for k, (_, fin) in LOOK.items() if k)


_FINISH = [(re.compile(rx), finish) for rx, finish in _motor_rules() + (
    (r"_shim$", None),                   # printed, though named after the board it packs
    (r"(^|_)wire_|_pigtail$|_cable_", "pvc"),
    (r"_silk(_|$)", "ink"),
    (r"insert|^nut$|^string_nut$", "brass"),      # the leadscrew nuts, the string ends
    (r"pogo_.*(pins|pads)|_pogo_pins$", "gold"),
    (r"bearing|magnet$|^string$", "polished"),
    (r"screw$|screw_(top|bottom)$|washer$|spring$|_dowel$|_rod$|^leadscrew$|_m4_(key|mid)$"
     r"|^ui_shaft$|^ui_display$", "steel"),
    (r"^output_panel_term_metal$", "steel"),      # J8's screws and pins
    (r"^nut_plate$", "steel"),                    # laser-cut 304 (its PARTS row is steel/, not a filament)
    (r"^wall_bar$", "steel"),                     # the side walls' A-36 flat bars (zinc-sprayed)
    (r"^output_panel_term$", "nylon"),            # J8's PA66 housing (src/screw_terminal.py)
    (r"^belt$", "rubber"),
    (r"^pickup$", "aluminium"),
    (r"^motor$", "painted"),
    (r"_ph_(top|bottom)$|_plug_|^ui_pwr_stem$|^ui_disp_ffc_socket$", "nylon"),
    (r"^ui_ffc(_stiffener)?$", "pvc"),            # the display's flat cable: films
    (r"^ui_ffc_contacts$", "steel"),              # ...and its bared tinned conductors
    (r"^ui_ribbon_socket$", "nylon"),             # the Pi ribbon's IDC sockets (PBT)
    (r"^ui_screen$", "screen"),
    (r"^ui_screen_lit$", "ink"),                  # light, not a surface: flat and bright
    (r"^pi4_(shells|lids|sd)$", "steel"),            # the Pi's parts (src/pi4b.py GROUPS)
    (r"^pi4_pins$", "gold"),
    (r"^pi4_(black|ffc|usb3|card)$", "nylon"),
    (r"^pi_riser$", "nylon"),                     # Adafruit 4079 socket riser: black housing
    (r"^pi4_passives$", "painted"),
    (r"^brain_board_cm5$", "board"),            # the Compute Module 5 (src/new_boards_view.py)
    (r"^brain_board_cm5_soc$", "polished"),     # ...its SoC's metal lid
    (r"^brain_board_cm5_plug$", "nylon"),       # ...the DF40 plugs on its underside (LCP)
    (r"^brain_board_df40_leads$", "gold"),      # J201 / J202's contact leads on their pads
    (r"^connector_board_tb_plug$", "nylon"),      # J11-J20's MX15EDGK plugs (src/pluggable_terminal.py)
    (r"^connector_board_tb_screws$", "steel"),    # ...their M2 slotted screws
    (r"^(brain|connector)_board_idc$", "nylon"),           # IDC sockets (src/ribbon_socket.py)
    (r"^(brain|connector)_board_idc_ribbon$", "pvc"),      # ...a stub of each ribbon
    (r"(^|_)pcb(_[a-z]+)?$|_board_(top|bottom)$|^(motor_ctrl|output_panel|pi_cap|pi4)$", "board"),
)]


def finish_of(base: str):
    """The finish of a part that is not printed, from its name; None if no rule fits."""
    for rx, finish in _FINISH:
        if rx.search(base):
            return finish
    return None


# TWO PARTS IN THE BUILD, ONE OBJECT in the hand (a print in two filaments, a screen
# and what it shows), so the viewer hides, selects and lists them as one
# (cadkit.web.export units=).
_ONE_PRINT = (
              # the direct body's top panel and its white windows: one two-filament print
              # (user, 2026-11-14: select and hide/show them as one part)
              (re.compile(r"^deck_white_(\d+)$"), r"deck_\1"),
              # one bought motor, drawn one solid per material (src/servo42d.py)
              (re.compile(r"^motor_(?:face|stack|shaft|coil_plug|driver|terminal|coil_terminal"
                          r"|screws|term_screws|buttons|lead_[a-z]+)_(\d+)$"), r"motor_\1"),
              (re.compile(r"^pi4_[a-z0-9]+$"), "pi4"),            # one bought board
              # one bought display module: its bezel, its glass and what the glass shows
              # (user, 2026-11-11: hide, show and select them as one part)
              (re.compile(r"^ui_screen(?:_lit)?$"), "ui_display"),
              (re.compile(r"^ui_ffc_(contacts|stiffener)$"), "ui_ffc"),   # one cable
              # what is mounted or plugged on a new board is one thing with it (user, 2026-11-14:
              # "boards should be selectable as a single part"): the CM5 and its SoC lid, the
              # DF40 pair, the IDC sockets and ribbon stubs, the MX15 plugs and their screws
              (re.compile(r"^(brain_board|connector_board)_(?:cm5\w*|df40\w*|idc\w*|tb_\w+)$"),
               r"\1_pcb"))


def unit_of(name: str):
    """The part `name` is one object with, or None."""
    for rx, to in _ONE_PRINT:
        if rx.match(name):
            return rx.sub(to, name)
    return None


# THE BENCHES keep their own tables (their parts are named wb_ and are in no PARTS row),
# and the instrument's limits they draw (ghost_) are no material at all: see-through.
_BENCHES = (("wb_", "src.wood_bench"),)


def material_of(name: str):
    """What `name` (an instance in the assembly) is made of: "petg-gf" | "pctg" |
    "pctg-clear" | "pctg-black" | "tpu" for a printed part, a finish for a bought one, else None.
    None is an ERROR in the viewer (cadkit.web.export): there is no plastic default."""
    name = name.split("__")[0]
    base = re.sub(r"(_\d+)+$", "", name)
    if base.startswith("ghost_"):
        return "pctg-clear"
    # THE PLANK BENCH (src.plank_bench): its prints are PETG-GF; its bought parts are the
    # instrument's own, renamed "x..." (the stack turned along X) or "inline_..." (the motor)
    if base.startswith("plank_") or base == "inline_coupler":
        return "petg-gf"
    if re.search(r"_m[34](_[a-z]+)?$|^crown_axle$", base):
        return "steel"
    if base.startswith("inline_motor"):
        base = base[len("inline_"):]
    elif re.match(r"^x(nut|string_nut|leadscrew|yoke_m3_\w+|screw_\w+)$", base):
        base = base[1:]
    from src import direct_bench as _DB      # THE INSTRUMENT (plain names, user 2026-11-14)
    if _DB.owns(base):
        return _DB.material_of(base)
    for pre, mod in _BENCHES:
        if base.startswith(pre):
            import importlib
            # the bench's table is authoritative for ITS parts; a db_ part it does not list
            # falls through to the general rules (pcb, screw, ...) like any other name
            m = importlib.import_module(mod).material_of(base)
            if m is not None:
                return m
            break
    return _filament_of(name) or finish_of(base)


def _filament_of(name: str):
    exact, pats = _table()
    base = re.sub(r"(_\d+)+$", "", name)
    # THE TWO CAPS THE HAND FINDS on the deck, the stick's and the power button's, are
    # BLACK PCTG (user, 2026-10-09), not the deck's colour
    if base in ("ui_knob", "ui_pwr_cap"):
        return "pctg-black"
    # PRINTED, AND IN NO PARTS ROW (they are exported inside a coupon, or not yet at all):
    # the build table cannot say what these are made of, so this does. PCTG, like every
    # other small fine-feature part (user, 2026-10-12: the nut's sliding inserts and the
    # belt clamps are PCTG and so the same green; the shims and the Pi's spacer are an
    # assumption on the same rule).
    if base in _PRINTED:
        return "pctg"
    # a part drawn as several solids is exported one solid at a time (cadkit.web.pieces), each with one more index on its name
    tail = name
    while True:
        for rx, mat in pats:
            if rx.match(tail):
                return mat
        cut = re.sub(r"_\d+$", "", tail)
        if cut == tail:
            break
        tail = cut
    if base in exact:
        return exact[base]
    bare = base
    # a part made in variants under one instance name (screw_pulley -> _hi / _lo)
    # (two or more of them: one key that merely starts the same is another part --
    # `pickup` is not pickup_zplate, `motor` is not motor_pulley). A VARIANT IS ONE WORD
    # after the name: the brass leadscrew `nut` is not the printed nut_slide_insert,
    # and counting those as its variants drew the nut in PCTG (user, 2026-10-16).
    kin = [m for k, m in exact.items()
           if k.startswith(bare + "_") and "_" not in k[len(bare) + 1:]]
    return kin[0] if len(kin) >= 2 and len(set(kin)) == 1 else None


if __name__ == "__main__":
    import collections
    import sys
    names = [f.stem for d in (".scratch_cache", ".webview/live") for f in (ROOT / d).glob("*.brep")]
    got = collections.Counter(material_of(n) for n in names)
    print(dict(got))
    if "-v" in sys.argv:
        for mat in MATERIALS:
            print(mat, sorted({re.sub(r"(_\d+)+$", "", n) for n in names if material_of(n) == mat}))
        from cadkit.web.finishes import FINISHES
        for fin in FINISHES:
            print(fin, sorted({re.sub(r"(_\d+)+$", "", n) for n in names if material_of(n) == fin}))
        print("none:", sorted({re.sub(r"(_\d+)+$", "", n) for n in names if material_of(n) is None}))
