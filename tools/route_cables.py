"""Route cables taut, on demand, into src/cable_routes.json -- and audit every cable.

    py -3.12 -m tools.route_cables                  # route every cable whose cache is stale
    py -3.12 -m tools.route_cables NAME [NAME..]    # route these, stale or not
    py -3.12 -m tools.route_cables --check          # which cached routes' surroundings moved
    py -3.12 -m tools.route_cables --audit          # every drawn conductor: drawn vs taut

WHY ON DEMAND (user, 2026-10-22): a taut route is a search through the solids round a
cable -- seconds to a minute each -- and the build must stay fast. So the build only
READS routes (src/cable_routes.py) and this solves them. Run it when the geometry
round a cable has moved and you want the drawing right again, and always before wires
are cut to the cut list.

THE OBSTACLES ARE THE LEAD'S LAST BUILD, read from the shared part cache
(cadkit.scratch) -- every part but the cables themselves, which may lie on each other.
A part you changed in this worktree and have not had built is routed against its old
shape; `--live` rebuilds the assembly here first (minutes) when that matters.

WHAT A ROUTE REQUEST IS comes from the drawing: src.wiring asks cable_routes.taut() for
each routed cable with its two free ends (each connector's straight lead already
drawn), its clearance and any gates (the channel it is meant to lie in), and this tool
reads those requests after drawing the wires once.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cable_route import Obstacles, Router, length          # noqa: E402

# the cables themselves, and anything with no volume: never obstacles
NOT_OBSTACLE = re.compile(r"^(wire_|pogo_wire_)|_cable(_|$)|_coil(_|$)|_silk|__pads|_lead_")
REACH = np.array([25.0, 25.0, 25.0])            # the box round a cable's ends, each way
BBOX_CACHE = ROOT / ".route-bbox.json"           # part -> (sha, bbox): skip far parts unread
MEM_LIMIT_MB = 1500                              # stop rather than eat the machine (user)


def rss_mb():
    """This process's working set, MB (Windows; 0 elsewhere)."""
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        c = PMC()
        c.cb = ctypes.sizeof(c)
        k32 = ctypes.WinDLL("kernel32")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        ps = ctypes.WinDLL("psapi")
        ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        ps.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return 0.0
        return c.WorkingSetSize / 1e6
    except Exception:
        return 0.0


def guard():
    """Raise once this process passes MEM_LIMIT_MB."""
    mb = rss_mb()
    if mb > MEM_LIMIT_MB:
        raise MemoryError("route_cables stopped itself at %.0f MB (limit %d): shrink REACH "
                          "or raise MEM_LIMIT_MB" % (mb, MEM_LIMIT_MB))


def be_nice():
    """Below-normal priority, so a route never makes the machine sluggish."""
    try:
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(
            ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)   # BELOW_NORMAL
    except Exception:
        pass


# cables the audit leaves out: the pedal bar (WIP, user 2026-10-22: pogo harness run 3 is
# the bar's stub), the coils (slack on purpose) and the servo's own coil lead (bought on
# the motor, not cut by us)
AUDIT_SKIP = re.compile(r"^pogo_wire_\w+_3$|_coil(_|$)|^motor_lead_")


def capture_paths():
    """Draw EVERY cable once with the cable builders wrapped, and return
    {name: (pts, across, thick)} -- the centreline each was drawn on, whichever module
    drew it. Most draw through cadkit.cables and only wiring.PATHS remembered its paths;
    this hooks the builders instead, so nothing in src has to register anything."""
    import sys as _sys
    import cadkit.cables as CC
    from src import build as B
    from src import leg_pogo as PG
    from src import led_leads as LL
    from src import wiring as WR
    from src import optical_pickup as OP
    seen = {}
    orig_oct, orig_flat = CC.oct_cable, CC.flat_cable

    def oct_(pts, d):
        s = orig_oct(pts, d)
        seen[id(s)] = ([tuple(map(float, q)) for q in pts], float(d), float(d))
        return s

    def flat_(pts, w, t, across=None):
        s = orig_flat(pts, w, t, across=across)
        seen[id(s)] = ([tuple(map(float, q)) for q in pts], float(w), float(t))
        return s

    swaps = []
    for m in list(_sys.modules.values()):
        for attr, new, old in (("oct_cable", oct_, orig_oct), ("flat_cable", flat_, orig_flat)):
            if getattr(m, attr, None) is old:
                swaps.append((m, attr, old))
                setattr(m, attr, new)
    try:
        comps = (list(WR.build_wires()) + list(B._ctrl_bus_components())
                 + list(B._lever_bus_components()) + list(LL.parts()) + list(PG.harness())
                 + list(WR.optical_feed()) + [("optical_cable_usb", OP.opt_cables("usb"))])
    finally:
        for m, attr, old in swaps:
            setattr(m, attr, old)
    out = {}
    for c in comps:
        name, shape = c[0], c[1]
        if id(shape) in seen and not AUDIT_SKIP.search(name):
            out[name] = seen[id(shape)]
    return out


def draw_wires():
    """Draw every cable once, so src.cable_routes.REQUESTS and src.wiring.PATHS fill."""
    from src import build as B
    from src import wiring as WR
    from src import led_leads as LL
    WR.build_wires()
    B._ctrl_bus_components()
    B._lever_bus_components()
    LL.fret_routes()
    from src import cable_routes as CR
    return CR, WR


class Parts:
    """The shared part cache, read lazily: a part is parsed only when a route's box
    reaches its bounding box, and the boxes are remembered by hash between runs."""

    def __init__(self):
        from cadkit.scratch import shared_cache
        self.dir = shared_cache(ROOT)
        man = json.loads((self.dir / "MANIFEST.json").read_text())
        self.build, self.sha = man.get("build"), man["parts"]
        try:
            self.bbox = json.loads(BBOX_CACHE.read_text())
        except (FileNotFoundError, ValueError):
            self.bbox = {}
    def shape(self, name):
        """Parsed on every call and NOT kept: a few parts are near any one route, and
        holding all of them is what used to fill memory."""
        from cadkit.scratch import read_brep
        return read_brep(self.dir / (name + ".brep"))

    def box(self, name):
        e = self.bbox.get(name)
        if e is None or e[0] != self.sha[name]:
            s = self.shape(name)
            guard()
            try:
                bb = s.BoundingBox()
                e = [self.sha[name], [bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax]]
            except Exception:
                e = [self.sha[name], None]
            self.bbox[name] = e
        return e[1]

    def near(self, lo, hi, moved=()):
        """[(name, shape)] of the obstacle parts whose boxes reach (lo, hi), parsed one at
        a time as the caller asks for them. `moved` [(regex, offset)] shifts the parts
        it names, for a route in a pose the build does not draw."""
        moved = [(re.compile(rx), np.asarray(d, float)) for rx, d in moved]
        for n in self.sha:
            if NOT_OBSTACLE.search(n):
                continue
            b = self.box(n)
            if b is None:
                continue
            d = next((off for rx, off in moved if rx.search(n)), None)
            b = np.array(b, float)
            if d is not None:
                b = b + np.concatenate([d, d])
            if np.any(b[3:] < lo) or np.any(b[:3] > hi):
                continue
            s = self.shape(n)
            yield n, (s if d is None else s.translate(cq_vec(d)))

    def save(self):
        BBOX_CACHE.write_text(json.dumps(self.bbox))


def cq_vec(d):
    import cadquery as cq
    return cq.Vector(*map(float, d))


def region(req):
    pts = [req["a"], req["b"]] + [p for g in req["gates"] for p in g]
    pts = np.array(pts, float)
    return pts.min(axis=0) - REACH, pts.max(axis=0) + REACH


def solve(name, req, parts, log=print):
    """Route one request; return its cache entry."""
    t0 = time.time()
    lo, hi = region(req)
    near = parts.near(lo, hi, req.get("moved", ()))
    ob = Obstacles(near, (lo, hi), guard=guard)
    r = Router(ob, req["r"])
    pts = r.route(req["a"], req["b"], gates=[tuple(map(tuple, g)) for g in req["gates"]])
    drawn = length(req["legacy"])
    taut = length(pts)
    log("  %-28s taut %7.1f  hand-drawn %7.1f  (%+.1f)  %d bends, %d parts near, %.0fs"
        % (name, taut, drawn, taut - drawn, len(pts) - 2, len(ob.names), time.time() - t0))
    return {"a": req["a"], "b": req["b"], "r": req["r"], "gates": req["gates"],
            "moved": req.get("moved", []),
            "pts": [[round(v, 4) for v in p] for p in pts], "length": round(taut, 2),
            "parts": {n: parts.sha[n] for n in ob.names}, "build": parts.build,
            "routed": time.strftime("%Y-%m-%d")}


def check(CR, parts):
    """Which cached routes have parts round them that changed since they were solved."""
    data = CR._load()
    bad = 0
    for name, e in sorted(data.items()):
        moved = [n for n, h in e.get("parts", {}).items() if parts.sha.get(n) != h]
        if moved:
            bad += 1
            print("  %-28s %d part(s) round it changed: %s" % (name, len(moved), ", ".join(moved[:6])))
    print("%d of %d cached routes have changed surroundings" % (bad, len(data)))
    return bad


def audit(paths, parts, every=False):
    """Every drawn conductor: its drawn length against a straight line and against its
    own taut route between the ends of its straight leads. A flat ribbon is routed by its
    THICKNESS (it can turn edge-on through a slot) -- so its taut length is a floor, and
    whether it really fits flat is the overlap gate's job, not this."""
    rows = []
    for name, (pts, across, thick) in sorted(paths.items()):
        if len(pts) < 3:
            continue
        a, b = np.array(pts[1], float), np.array(pts[-2], float)     # past each lead
        drawn = length(pts[1:-1])
        chord = math.dist(a, b)
        if not every and drawn - chord < 2.0:
            rows.append((name, drawn, chord, None, across != thick))
            continue
        req = {"a": list(a), "b": list(b), "gates": [], "r": min(across, thick) / 2.0 + 0.2,
               "legacy": pts[1:-1]}
        try:
            lo, hi = region(req)
            ob = Obstacles(parts.near(lo, hi), (lo, hi), guard=guard)
            taut = length(Router(ob, req["r"]).route(a, b))
        except MemoryError:
            raise
        except Exception as ex:
            taut = None
            print("  %s: %s" % (name, ex))
        rows.append((name, drawn, chord, taut, across != thick))
    print("\n%-34s %8s %8s %8s %8s" % ("conductor", "drawn", "straight", "taut", "excess"))
    for name, drawn, chord, taut, flat in rows:
        ref = chord if taut is None else taut
        print("%-34s %8.1f %8.1f %8s %+8.1f%s" % (name, drawn, chord,
                                                "-" if taut is None else "%.1f" % taut,
                                                drawn - ref, "  (flat)" if flat else ""))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--all", action="store_true", help="audit: route every conductor")
    a = ap.parse_args(argv)
    be_nice()
    CR, WR = draw_wires()
    parts = Parts()
    print("obstacles: the shared part cache, build %s (%d parts); %.0f MB in use"
          % (parts.build, len(parts.sha), rss_mb()))
    try:
        if a.check:
            return 1 if check(CR, parts) else 0
        if a.audit:
            audit(capture_paths(), parts, a.all)
            return 0
        names = a.names or list(CR.STALE)
        unknown = [n for n in names if n not in CR.REQUESTS]
        if unknown:
            raise SystemExit("not a routed cable: %s (routed: %s)"
                             % (", ".join(unknown), ", ".join(sorted(CR.REQUESTS))))
        if not names:
            print("every routed cable's cache is current")
            return 0
        out = {}
        for n in names:
            out[n] = solve(n, CR.REQUESTS[n], parts)
        CR.save(out)
        print("wrote %d route(s) to %s" % (len(out), CR.CACHE.relative_to(ROOT)))
        return 0
    finally:
        parts.save()


if __name__ == "__main__":
    sys.exit(main())
