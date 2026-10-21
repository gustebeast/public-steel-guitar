"""What each part of the assembly is made of, for the viewer.

    material_of("lkr_main_cart_base_0")  ->  "pctg"       the filament it is printed in
    material_of("chassis_2")             ->  "petg-gf"
    material_of("kl_bearing")            ->  "polished"   bought: its finish
    material_of("tee_insert_3")          ->  "brass"

The build's PARTS table (src/build.py) is the one place a printed part's material is
written: the folder of its STEP file, "petg-gf/chassis_2.step". This reads that table AS
TEXT, because importing the build module costs over a minute and the viewer's export
must not. An assembly instance is named after its part with a station prefix and index
groups round it (pedal3_axle, rkl_knee_housing, top_plate_1), so the name is reduced the
way the build's own colour lookup reduces it.

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
_PRINTED = ("nut_slide_insert", "belt_tensioner_half_a", "belt_tensioner_half_b",
            "pcb_shim", "pi_spacer")
_STATION = re.compile(r"^(?:lkl|lkr|rkl|rkr|vkl|pedal\d+)_")
_LANE = re.compile(r"^(?:main|half_stop)_")


@functools.lru_cache(maxsize=1)
def _table():
    """{part key: material} from PARTS, f-string keys (chassis_{_i}) as patterns."""
    src = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
    exact, pats = {}, []
    for m in re.finditer(r'(?:^\s{4}"([a-z0-9_]+)":\s*\(|PARTS\[(f?)"([^"]+)"\]\s*=\s*\()', src, re.M):
        body = src[m.end(): m.end() + 1500]
        nxt = re.search(r'\n\s{4}"[a-z0-9_]+":\s*\(|\n\s*PARTS\[', body)
        if nxt:
            body = body[: nxt.start()]
        mat = re.search(r'"(%s)/[^"]+\.step"' % "|".join(MATERIALS), body)
        if not mat:
            continue
        if m.group(1):
            exact[m.group(1)] = mat.group(1)
        elif m.group(2):                                   # an f-string key
            pats.append((re.compile("^" + re.sub(r"\{[^}]+\}", r"\\d+", m.group(3)) + "$"),
                         mat.group(1)))
        else:
            exact[m.group(3)] = mat.group(1)
    return exact, pats


# WHAT A BOUGHT PART IS, FROM ITS NAME. First match wins; searched in the name with its
# index groups off (lkr_main_spring_tension_screw, wire_canb_gnd_lkl, kl_bearing).
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
    (r"(main|half_stop)_spring$", "painted"),     # the levers' die springs are painted blue
    (r"screw$|screw_(top|bottom)$|washer$|spring$|_dowel$|_rod$|^leadscrew$|_m4_(key|mid)$"
     r"|^ui_shaft$|^ui_display$", "steel"),
    (r"^output_panel_term_metal$", "steel"),      # J8's screws and pins
    (r"^output_panel_term$", "nylon"),            # J8's PA66 housing (src/screw_terminal.py)
    (r"^belt$", "rubber"),
    (r"^pickup$", "aluminium"),
    (r"^motor$", "painted"),
    (r"_ph_(top|bottom)$|_plug_|^ui_pwr_stem$|^ui_disp_ffc_socket$", "nylon"),
    (r"^ui_ffc$", "pvc"),                         # the display's flat cable: a film
    (r"^ui_screen$", "screen"),
    (r"^ui_screen_lit$", "ink"),                  # light, not a surface: flat and bright
    (r"^pi4_(shells|lids|sd)$", "steel"),            # the Pi's parts (src/pi4b.py GROUPS)
    (r"^pi4_pins$", "gold"),
    (r"^pi4_(black|ffc|usb3|card)$", "nylon"),
    (r"^pi4_passives$", "painted"),
    (r"(^|_)pcb(_[a-z]+)?$|_board_(top|bottom)$|^(motor_ctrl|output_panel|pi_cap|pi4)$", "board"),
)]


def finish_of(base: str):
    """The finish of a part that is not printed, from its name; None if no rule fits."""
    bare = _STATION.sub("", base)
    for rx, finish in _FINISH:
        if rx.search(bare):
            return finish
    return None


# TWO PARTS IN THE BUILD, ONE OBJECT in the hand (a print in two filaments, a screen
# and what it shows), so the viewer hides, selects and lists them as one
# (cadkit.web.export units=).
_ONE_PRINT = ((re.compile(r"^top_plate_color_(\d+)$"), r"top_plate_\1"),
              # one bought motor, drawn one solid per material (src/servo42d.py)
              (re.compile(r"^motor_(?:face|stack|shaft|coil_plug|driver|terminal|coil_terminal"
                          r"|screws|term_screws|buttons|lead_[a-z]+)_(\d+)$"), r"motor_\1"),
              (re.compile(r"^pi4_[a-z0-9]+$"), "pi4"),            # one bought board
              (re.compile(r"^chassis_light_(\d+)$"), r"chassis_\1"),
              (re.compile(r"^ui_screen_lit$"), "ui_screen"))     # what the screen shows


def unit_of(name: str):
    """The part `name` is one object with, or None."""
    for rx, to in _ONE_PRINT:
        if rx.match(name):
            return rx.sub(to, name)
    return None


def material_of(name: str):
    """What `name` (an instance in the assembly) is made of: "petg-gf" | "pctg" |
    "pctg-clear" | "pctg-black" | "tpu" for a printed part, a finish for a bought one, else None."""
    name = name.split("__")[0]
    return _filament_of(name) or finish_of(re.sub(r"(_\d+)+$", "", name))


def _filament_of(name: str):
    exact, pats = _table()
    base = re.sub(r"(_\d+)+$", "", name)
    # THE DECK IS ONE PRINT IN TWO PCTGs. Its `top_plate_color_N` bodies are the skin
    # you see (the whole top face); `top_plate_N` is the body under it, CLEAR, which
    # shows through as the fret lines and markers and lets the fret lights up through
    # them. The chassis's light window is the same clear PCTG. "pctg-clear" is drawn
    # see-through (cadkit's viewer: any filament named ...-clear).
    # A BENCH COUPON (src/test/bench_joinery.py) is a piece of a real part, printed in
    # that part's filament and drawn in its colour
    if base.startswith("test_"):
        from src.test.bench_joinery import source_of
        src = source_of(base)
        return _filament_of(src) if src else None
    if base == "top_plate_color":
        return "pctg"
    if base in ("top_plate", "chassis_light"):
        return "pctg-clear"
    # THE TWO CAPS THE HAND FINDS on the deck, the stick's and the power button's, are
    # BLACK PCTG (user, 2026-10-09), not the deck's colour
    if base in ("ui_knob", "ui_pwr_cap"):
        return "pctg-black"
    # PRINTED, AND IN NO PARTS ROW (they are exported inside a coupon, or not yet at all):
    # the build table cannot say what these are made of, so this does. PCTG, like every
    # other small fine-feature part (user, 2026-10-12: the nut's sliding inserts and the
    # belt clamps are PCTG and so the same green; the shims and the Pi's spacer are an
    # assumption on the same rule).
    # The shims HAVE rows now (kl_/kv_/pedal_pcb_shim) but under their part names, not
    # the station names the assembly draws them by, so they are still answered here.
    if re.sub(r"^.*_(?=pcb_shim$)", "", base) in _PRINTED:
        return "pctg"
    # chassis_2 -- and chassis_1_0: a part drawn as several solids is exported one
    # solid at a time (cadkit.web.pieces), each with one more index on its name
    tail = name
    while True:
        for rx, mat in pats:
            if rx.match(tail):
                return mat
        cut = re.sub(r"_\d+$", "", tail)
        if cut == tail:
            break
        tail = cut
    tries = [base]
    bare = _STATION.sub("", base)
    tries += [bare, "kl_" + bare, _LANE.sub("", bare)]
    # the vertical lever's parts carry the design's prefix inside the station's
    # (vkl_kv_main_cart_base): the same cartridge, axle and cap as every other lever's
    inner = re.sub(r"^kv_", "", bare)
    tries += [inner, "kl_" + inner, _LANE.sub("", inner)]
    for t in tries:
        if t in exact:
            return exact[t]
    # a part made in variants under one instance name (screw_pulley -> _hi / _lo)
    # (two or more of them: one key that merely starts the same is another part --
    # `pickup` is not pickup_zplate, `motor` is not motor_pulley). A VARIANT IS ONE WORD
    # after the name: the brass leadscrew `nut` is not the printed nut_slide_insert_a/b/c,
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
