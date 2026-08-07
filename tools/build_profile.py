"""Per-part / per-module build-cost profiler for the pedal-steel build.

Answers "what does each part cost to build?" so a badly-written part can't quietly inflate
every agent's build time. Build cost lands in two places, and this measures BOTH:

  • MODULE-LEVEL geometry -- a ``foo = build_foo()`` at a src module's top level runs at
    IMPORT, so ``builder()`` never sees it. Measured with ``-X importtime``: each src module's
    self-import time IS its module-level geometry cost. (This is ~3/4 of the real build, so
    ignoring it -- as a naive builder()-only profiler does -- misattributes most of the time.)
  • LAZY geometry -- a ``lambda: build_foo()`` runs inside ``builder()``. Timed in-process,
    together with its throwaway ``export_step`` (tessellate + write STEP).

Each part also gets a FACE COUNT: a machine-INDEPENDENT complexity proxy that predicts
export / assembly / overlap-scan cost and is the cleanest "did someone bloat this" signal.

  py -3.12 -m tools.build_profile               # ranked module + part tables, flags
  py -3.12 -m tools.build_profile --top 15
  py -3.12 -m tools.build_profile --only belt_tensioner,carriage
  py -3.12 -m tools.build_profile --save-baseline
  py -3.12 -m tools.build_profile --json

REGRESSION GATE. With a baseline (tools/build_profile_baseline.json), a normal run flags any
part whose FACE COUNT or time SHARE jumped -- the signature of an LLM bloating one part. Faces
and share (not raw seconds) are used so the check is portable across machines. Exit code =
parts+modules flagged (0 = clean), so it can gate a periodic check or CI.

Cost: one full import (-X importtime) + build/export every lazy part -- ~1-2 min. Fine for a
periodic check; for an on-every-build summary call ``profile()`` from ``src.build`` (the build
already pays the import) once that file is free of other WIP.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

BASELINE = pathlib.Path(__file__).with_name("build_profile_baseline.json")

SHARE_FLAG    = 0.06       # a single part/module eating >=6% of the whole build is a lot
FACES_REGRESS = 0.20       # +20% faces vs baseline = geometry got materially heavier (exact, noise-free)
SHARE_REGRESS = 0.05       # +5 share-points: set above the ~2pt run-to-run import-timing noise


def _timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t


def _real_total(lib_s, src, rows):
    """The whole build's cost: fixed engine import + module-level geometry + the lazy loop.
    One definition, shared by the report and the --json paths so they can't drift."""
    return lib_s + sum(src.values()) + sum(r["total_s"] for r in rows if "total_s" in r)


def _import_profile():
    """Run ``python -X importtime -c "import src.build"`` and return (lib_s, {src_module: self_s}).
    A module's SELF import time is its own top-level execution -- i.e. its MODULE-LEVEL geometry.
    Non-src self time (cadquery / OCP / stdlib) is summed into lib_s: fixed engine overhead paid
    once, not attributable to any part."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-X", "importtime", "-c", "import src.build"],
                       cwd=str(pathlib.Path(__file__).resolve().parents[1]),
                       capture_output=True, text=True, env=env)
    lib_us, src = 0, {}
    for line in r.stderr.splitlines():
        if not line.startswith("import time:"):
            continue
        parts = [p.strip() for p in line[len("import time:"):].split("|")]
        if len(parts) != 3 or not parts[0].isdigit():        # skip the "self | cumulative | ..." header
            continue
        self_us, module = int(parts[0]), parts[2]
        if module.startswith("src."):
            src[module] = src.get(module, 0) + self_us / 1e6
        else:
            lib_us += self_us
    return lib_us / 1e6, src


def profile(only=None):
    """Build+export every LAZY part once (into a scratch dir). Returns [row, ...]; each row is
    {part, build_s, export_s, total_s, faces} or {part, error}. ``only`` restricts to a name set."""
    from src import build as B
    from cadkit.step_export import export_step

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="build_profile_"))
    rows = []
    for name, (builder, _path, _note) in B.PARTS.items():
        if only and name not in only:
            continue
        try:
            wp, build_s = _timed(builder)
            solid = wp.val() if hasattr(wp, "val") else wp
            faces = len(solid.Faces()) if hasattr(solid, "Faces") else -1
            _, export_s = _timed(lambda w=wp: export_step(w, str(scratch / f"{name}.step")))
            rows.append({"part": name, "build_s": build_s, "export_s": export_s,
                         "total_s": build_s + export_s, "faces": faces})
        except Exception as e:                       # noqa: BLE001 -- one bad part must not abort the profile
            rows.append({"part": name, "error": f"{type(e).__name__}: {e}"})
    return rows


def _load_baseline():
    if not BASELINE.exists():
        return None
    try:
        d = json.loads(BASELINE.read_text())
        return {r["part"]: r for r in d["parts"]}, d.get("modules", {})
    except Exception:                                # noqa: BLE001 -- a corrupt baseline just disables the gate
        return None


# ── near-zero-cost hook for an ON-EVERY-BUILD regression gate ─────────────────
# A full build ALREADY calls builder()+export_step per part; feeding those timings and the
# solid's face count here costs ~nothing (no extra import, no rebuild). Module-level import
# attribution is skipped (that needs the standalone -X importtime run), but FACE COUNT is the
# exact, machine-INDEPENDENT bloat signal -- so a part an LLM inflated trips the gate for free.
# src.build wires this in ~4 lines: record_part(...) inside _export, report_build_regressions()
# after the part loop.
_BUILD_RECORDS = []


def record_part(name, build_s, export_s, solid):
    """Called by src.build._export per part. Cheap: stores time + face count, nothing else."""
    faces = len(solid.Faces()) if hasattr(solid, "Faces") else -1
    _BUILD_RECORDS.append({"part": name, "build_s": build_s, "export_s": export_s,
                           "total_s": build_s + export_s, "faces": faces})


def report_build_regressions():
    """Called by src.build.main() after the part loop. Prints per-part FACE-COUNT regressions
    vs the baseline (a part that got heavier); silent if clean or no baseline. Returns the count."""
    base = _load_baseline()
    reg = {}
    if base:
        base_parts, _ = base
        for r in _BUILD_RECORDS:
            b = base_parts.get(r["part"])
            if b and b.get("faces", 0) > 0 and r["faces"] > b["faces"] * (1 + FACES_REGRESS):
                reg[r["part"]] = f"faces {b['faces']}->{r['faces']} +{(r['faces']/b['faces']-1)*100:.0f}%"
    if reg:
        print("\n[build_profile] FACE-COUNT REGRESSION vs baseline (a part got heavier):")
        for k, why in sorted(reg.items()):
            print(f"  • {k}: {why}")
    _BUILD_RECORDS.clear()
    return len(reg)


def _regressions(rows, src, real_total, base):
    """vs-baseline regressions ONLY -- this is the gate (exit code). Being heavy is a known
    fact, not a failure; a part getting HEAVIER than the recorded baseline is. Faces + share
    are used (not raw seconds) so the check is portable across machines."""
    if not base:
        return {}
    base_parts, base_mods = base
    reg = {}
    for r in rows:
        b = base_parts.get(r["part"]) if "total_s" in r else None
        if not b:
            continue
        if b.get("faces", 0) > 0 and r["faces"] > b["faces"] * (1 + FACES_REGRESS):
            reg[r["part"]] = f"faces {b['faces']}->{r['faces']} +{(r['faces']/b['faces']-1)*100:.0f}%"
        elif r["share"] - b.get("share", 0) >= SHARE_REGRESS:
            reg[r["part"]] = f"share +{(r['share']-b.get('share',0))*100:.0f}pts"
    for m, s in src.items():
        bs = base_mods.get(m)
        if bs is not None and s / real_total - bs >= SHARE_REGRESS:
            reg[m] = f"module share +{(s/real_total-bs)*100:.0f}pts"
    return reg


def _print_report(lib_s, src, rows, base, top):
    ok = sorted((r for r in rows if "total_s" in r), key=lambda r: r["total_s"], reverse=True)
    errs = [r for r in rows if "error" in r]
    module_geom = sum(src.values())
    lazy = sum(r["total_s"] for r in ok)
    real_total = _real_total(lib_s, src, rows) or 1.0
    for r in ok:
        r["share"] = r["total_s"] / real_total

    reg = _regressions(ok, src, real_total, base)          # the gate
    heavy = ({m for m, s in src.items() if s / real_total >= SHARE_FLAG}
             | {r["part"] for r in ok if r["share"] >= SHARE_FLAG})

    def _mark(name):
        return "  <== REGRESSED" if name in reg else ("  (heavy)" if name in heavy else "")

    print(f"\nBUILD COST  (real total ~{real_total:5.1f}s)")
    print(f"  engine import (cadquery/OCP, fixed): {lib_s:6.2f}s  {lib_s/real_total*100:4.1f}%")
    print(f"  module-level geometry (at import):   {module_geom:6.2f}s  {module_geom/real_total*100:4.1f}%")
    print(f"  lazy build + export (per-part loop): {lazy:6.2f}s  {lazy/real_total*100:4.1f}%")

    print(f"\n  module-level geometry, heaviest src modules  (self-import = its top-level build)")
    for m, s in sorted(src.items(), key=lambda kv: kv[1], reverse=True)[:top or None]:
        if s < 0.05:
            break
        print(f"    {s:6.2f}s {s/real_total*100:5.1f}%  {m}{_mark(m)}")

    print(f"\n  lazy parts (builder() + export), heaviest")
    print(f"    {'build':>7} {'export':>7} {'total':>7} {'share':>6} {'faces':>6}  part")
    for r in ok[:top or None]:
        print(f"    {r['build_s']:7.2f} {r['export_s']:7.2f} {r['total_s']:7.2f} "
              f"{r['share']*100:5.1f}% {r['faces']:6d}  {r['part']}{_mark(r['part'])}")

    if reg:
        print("\nREGRESSED vs baseline (this fails the gate):")
        for k, why in sorted(reg.items()):
            print(f"  • {k}: {why}")
    elif base:
        print("\nno regressions vs baseline.")
    else:
        print("\nno baseline yet -- run --save-baseline to arm the regression gate.")
    for r in errs:
        print(f"  ERROR {r['part']}: {r['error']}", file=sys.stderr)
    return reg, real_total


def _save_baseline(lib_s, src, rows, real_total):
    payload = {"lib_s": lib_s, "real_total_s": real_total,
               "modules": {m: s / real_total for m, s in src.items()},   # SHARE (portable), not seconds
               "parts": [{"part": r["part"], "share": r["total_s"] / real_total,
                          "faces": r.get("faces", -1)} for r in rows if "total_s" in r]}
    BASELINE.write_text(json.dumps(payload, indent=2))
    print(f"baseline written: {BASELINE.name} ({len(payload['parts'])} parts, {len(src)} modules)")


def main() -> None:
    for _s in (sys.stdout, sys.stderr):              # Windows cp1252 -> UnicodeError on •/→/…
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(prog="build_profile")
    ap.add_argument("--only", help="comma-separated part names to profile (default: all)")
    ap.add_argument("--top", type=int, default=20, help="rows per table (0 = all)")
    ap.add_argument("--save-baseline", action="store_true", help="record this run as the baseline")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    only = set(a.only.split(",")) if a.only else None
    lib_s, src = _import_profile()
    rows = profile(only)

    if a.json:
        real_total = _real_total(lib_s, src, rows)
        print(json.dumps({"lib_s": lib_s, "real_total_s": real_total,
                          "modules": src, "parts": rows}, indent=2))
        return

    flagged, real_total = _print_report(lib_s, src, rows, _load_baseline(), a.top)
    if a.save_baseline:
        _save_baseline(lib_s, src, rows, real_total)
        return
    sys.exit(len(flagged))


if __name__ == "__main__":
    main()
