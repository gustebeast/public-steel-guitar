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

The viewer uses this for its "as printed" view: every part of one filament in that
filament's colour and finish, to judge the instrument as it will come off the printer.

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
_FINISH = [(re.compile(rx), finish) for rx, finish in (
    (r"_shim$", None),                   # printed, though named after the board it packs
    (r"(^|_)wire_|_pigtail$|_cable_", "pvc"),
    (r"_silk(_|$)", "ink"),
    (r"insert", "brass"),
    (r"pogo_.*(pins|pads)|_pogo_pins$", "gold"),
    (r"bearing|magnet$|^string$", "polished"),
    (r"screw$|screw_(top|bottom)$|washer$|spring$|_dowel$|_rod$|^leadscrew$|_m4_(key|mid)$"
     r"|^ui_shaft$|^ui_display$", "steel"),
    (r"^belt$", "rubber"),
    (r"^pickup$", "aluminium"),
    (r"^motor$", "painted"),
    (r"_ph_(top|bottom)$|_plug_", "nylon"),
    (r"^ui_screen$", "glass"),
    (r"(^|_)pcb(_[a-z]+)?$|_board_(top|bottom)$|^(motor_ctrl|output_panel|pi_cap|pi4)$", "board"),
)]


def finish_of(base: str):
    """The finish of a part that is not printed, from its name; None if no rule fits."""
    bare = _STATION.sub("", base)
    for rx, finish in _FINISH:
        if rx.search(bare):
            return finish
    return None


# PRINTS IN TWO FILAMENTS: two parts in the build, ONE object on the printer and in the
# hand, so the viewer hides, selects and lists them as one (cadkit.web.export units=).
_ONE_PRINT = ((re.compile(r"^top_plate_color_(\d+)$"), r"top_plate_\1"),
              (re.compile(r"^chassis_light_(\d+)$"), r"chassis_\1"))


def unit_of(name: str):
    """The part `name` is printed as one object with, or None."""
    for rx, to in _ONE_PRINT:
        if rx.match(name):
            return rx.sub(to, name)
    return None


def material_of(name: str):
    """What `name` (an instance in the assembly) is made of: "petg-gf" | "pctg" |
    "pctg-clear" | "tpu" for a printed part, a finish for a bought one, else None."""
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
    if base == "top_plate_color":
        return "pctg"
    if base in ("top_plate", "chassis_light"):
        return "pctg-clear"
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
    for t in tries:
        if t in exact:
            return exact[t]
    # a part made in variants under one instance name (screw_pulley -> _hi / _lo)
    # (two or more of them: one key that merely starts the same is another part --
    # `pickup` is not pickup_zplate, `motor` is not motor_pulley)
    kin = [m for k, m in exact.items() if k.startswith(bare + "_")]
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
