"""The first-flash bench in a viewer tab of its own (src/flash_bench.py).

    py -3.12 -m tools.flash_bench_view

Not the instrument, and not a build: it writes views/first-flash/.webview (which ignores
itself) and tells the viewer. It bumps no build number and publishes nothing.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import cadquery as cq

REPO = pathlib.Path(__file__).resolve().parents[1]
ROOT = REPO / "views" / "first-flash"

_METAL = {"wch_linke_pins", "stlink_v2_pins"}


def material_of(name: str):
    base = name.split("__")[0]
    if base.startswith("pi4"):
        from src.pi4b import GROUPS
        # a part of several solids arrives one solid at a time: pi4_shells_3
        return next(f for k, (_c, f) in sorted(GROUPS.items(), reverse=True)
                    if base[3:].startswith(k))
    if base.endswith("_board"):
        return "board"
    if base.endswith("_silk"):
        return "ink"
    if base in _METAL:
        return "gold"
    if "_tail_" in base or base.endswith(("_usb", "_supply")) or base.startswith(
            ("optical_power_", "power_link_")):
        return "nylon" if name.endswith("__socket") else "pvc"
    return "painted"


def _r1_geom() -> pathlib.Path:
    """The viewer's part models read every board's file straight from a folder, not through
    Boards.load, so they get a folder with the R1 boards in: elec/geom, elec/rev1 over it.
    The ink it keeps per board goes with it, or an R2 outline stays in the cache."""
    geom = ROOT / ".webview" / "geom"
    geom.mkdir(parents=True, exist_ok=True)
    for src in (REPO / "elec" / "geom", REPO / "elec" / "rev1"):
        for f in src.glob("*.geom.json"):
            shutil.copyfile(f, geom / f.name)
            if src.name == "rev1":
                (ROOT / ".webview" / "boards" / (f.name[:-len(".geom.json")] + ".ink.pkl")).unlink(
                    missing_ok=True)
    return geom


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    from cadkit.web import show
    from src import flash_bench as FB
    parts = [(n, w, cq.Color(*rgb)) for n, w, rgb in FB.components()]
    ROOT.mkdir(parents=True, exist_ok=True)
    FB.BOARDS.geom_dir = str(_r1_geom())
    ok = show(parts, root=ROOT, title="First flash: what plugs into what", boards=FB.BOARDS,
              materials=material_of, units=FB.unit_of, cache_dir=ROOT / ".webview" / "boards",
              mesh_cache=ROOT / ".webview" / "mesh")
    for r in FB.conductors():
        print("  %-28s %-34s -> %s" % r)
    return 0 if ok is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
