"""Fast SINGLE-PART build for iteration -- imports only the part's own module, not all of
`src.build` (26s of module-level geometry you don't need). ~20x faster per part, and with
ZERO staleness risk: it builds fresh from the current source every time -- the only thing
cached is the name->module MAP (rebuilt whenever build.py changes), never geometry.

  py -3.12 -m tools.fast_build carriage            # rebuild just carriage.step, fast
  py -3.12 -m tools.fast_build kv_housing kv_lever # a few parts
  py -3.12 -m tools.fast_build --list              # parts this fast path can handle
  py -3.12 -m tools.fast_build --refresh           # force-rebuild the name->module map

The canonical GUARANTEED build stays `py -3.12 -m src.build` (full set + assembly). This is
an opt-in accelerator for the inner loop. Parts whose builder can't be reconstructed from the
map (fused/multi-module ones like the pedal bar) fall back with a message to use src.build.

HOW: most PARTS builders are `[heal](__import__("src.X", ...).ATTR)`. We import src.build ONCE
(the slow 26s) to read PARTS, disassemble each builder to recover (module, attr, heal?), and
cache that tiny map keyed by build.py's hash. Thereafter a part rebuild imports ONLY src.X.
"""

from __future__ import annotations

import argparse
import dis
import hashlib
import json
import pathlib
import sys
import time
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD_PY = ROOT / "src" / "build.py"
MAP_FILE = pathlib.Path(__file__).with_name("fast_build_map.json")


def _reconstruct(builder, buildmod):
    """Recover {module, attr, heal} from a builder we can rebuild via a LAZY import:
      * [heal](__import__("src.X", ...).ATTR)                  -> module src.X, member ATTR
      * [heal](ALIAS.member[()]) where ALIAS is a module bound -> that module, member
        at build.py top (`from . import legs as LG`, `import components as C`, ...)
    Returns None for shapes we can't (partial(pre-built object), fused multi-module bars, ...).
    At REBUILD the member is called iff it's callable, so both a function (LG.leg_sleeve())
    and a pre-built object (mod.kv_housing) come out right."""
    code = getattr(builder, "__code__", None)
    if code is None:
        return None                                   # functools.partial etc. -> fall back
    heal = "heal" in code.co_names
    instrs = list(dis.get_instructions(builder))
    members = [i.argval for i in instrs if i.opname in ("LOAD_ATTR", "LOAD_METHOD")]

    srcs = [c for c in code.co_consts if isinstance(c, str) and c.startswith("src.")]
    if len(srcs) == 1 and members:                    # __import__("src.X").MEMBER
        return {"module": srcs[0], "attr": members[-1], "heal": heal}

    for k, ins in enumerate(instrs):                  # ALIAS.member, ALIAS a build.py module
        if ins.opname in ("LOAD_GLOBAL", "LOAD_NAME", "LOAD_DEREF") and isinstance(ins.argval, str):
            obj = getattr(buildmod, ins.argval, None)
            if isinstance(obj, types.ModuleType) and obj.__name__.split(".")[0] in ("src", "cadkit"):
                mem = next((i.argval for i in instrs[k + 1:k + 3]
                            if i.opname in ("LOAD_ATTR", "LOAD_METHOD")), None)
                if mem:
                    return {"module": obj.__name__, "attr": mem, "heal": heal}
    return None


def _build_map():
    """Import src.build ONCE (slow) and disassemble every PARTS builder into a lazy-rebuild map."""
    print("building name->module map (one-time src.build import ~26s)...", flush=True)
    from src import build as B
    entries = {}
    for name, (builder, path, _note) in B.PARTS.items():
        rec = _reconstruct(builder, B)
        if rec:
            rec["path"] = path
            entries[name] = rec
    payload = {"build_hash": hashlib.sha256(BUILD_PY.read_bytes()).hexdigest(),
               "total_parts": len(B.PARTS), "entries": entries}
    MAP_FILE.write_text(json.dumps(payload, indent=2))
    return payload


def _load_map(refresh=False):
    cur = hashlib.sha256(BUILD_PY.read_bytes()).hexdigest()
    if not refresh and MAP_FILE.exists():
        try:
            m = json.loads(MAP_FILE.read_text())
            if m.get("build_hash") == cur:
                return m
        except Exception:
            pass
    return _build_map()


def fast_build(name, entries):
    """Rebuild one part by importing ONLY its module. Returns seconds, or None if unsupported."""
    rec = entries.get(name)
    if rec is None:
        return None
    from importlib import import_module
    from cadkit.step_export import export_step
    t = time.perf_counter()
    mod = import_module(rec["module"])
    obj = getattr(mod, rec["attr"])
    if callable(obj):                    # a function (LG.leg_sleeve()) -> call it; a pre-built
        obj = obj()                      # Workplane/Assembly (mod.kv_housing) is not callable
    if rec["heal"]:
        from src.helpers import heal
        obj = heal(obj)
    dest = ROOT / rec["path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    export_step(obj, str(dest))
    return time.perf_counter() - t


def main() -> None:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="fast_build")
    ap.add_argument("parts", nargs="*", help="part name(s) to rebuild fast")
    ap.add_argument("--list", action="store_true", help="list parts this fast path can handle")
    ap.add_argument("--refresh", action="store_true", help="rebuild the name->module map")
    a = ap.parse_args()

    m = _load_map(refresh=a.refresh)
    entries = m["entries"]
    if a.list or not a.parts:
        print(f"fast path handles {len(entries)}/{m['total_parts']} parts "
              f"(the rest are fused/multi-module -- use src.build --part <name>):")
        for n in sorted(entries):
            print(f"  {n:22s} <- {entries[n]['module']}")
        return

    for name in a.parts:
        dt = fast_build(name, entries)
        if dt is None:
            print(f"  {name}: not fast-buildable (fused/multi-module) -- "
                  f"py -3.12 -m src.build --part {name}", file=sys.stderr)
        else:
            print(f"  {name}: rebuilt in {dt:.2f}s ({entries[name]['path']})")


if __name__ == "__main__":
    main()
