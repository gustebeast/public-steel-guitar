"""Which filament each part of the assembly is printed in, for the viewer.

    material_of("lkr_main_cart_base_0")  ->  "pctg"
    material_of("chassis_2")             ->  "petg-gf"
    material_of("kl_bearing")            ->  None        (bought, not printed)

The build's PARTS table (src/build.py) is the one place a printed part's material is
written: the folder of its STEP file, "petg-gf/chassis_2.step". This reads that table AS
TEXT, because importing the build module costs over a minute and the viewer's export
must not. An assembly instance is named after its part with a station prefix and index
groups round it (pedal3_axle, rkl_knee_housing, top_plate_1), so the name is reduced the
way the build's own colour lookup reduces it.

The viewer uses this for its "as printed" view: every part of one filament in that
filament's colour and finish, to judge the instrument as it will come off the printer.
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


def material_of(name: str):
    """"petg-gf" | "pctg" | "pctg-alt" | "tpu" for a printed part's instance name, else None."""
    exact, pats = _table()
    name = name.split("__")[0]
    base = re.sub(r"(_\d+)+$", "", name)
    # THE DECK IS ONE PRINT IN TWO COLOURS OF PCTG. Its `top_plate_color_N` bodies are
    # the skin you see (the whole top face); `top_plate_N` is the body under it, which
    # shows through as the fret lines and markers. The skin takes the PCTG colour and
    # the body under it reads as "pctg-alt", a second colour, or the markers would
    # vanish into the deck.
    if base == "top_plate_color":
        return "pctg"
    if base == "top_plate":
        return "pctg-alt"
    for rx, mat in pats:                                   # chassis_2
        if rx.match(name):
            return mat
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
        print("none:", sorted({re.sub(r"(_\d+)+$", "", n) for n in names if material_of(n) is None}))
