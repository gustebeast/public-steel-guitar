"""THE DIRECT INSTRUMENT'S HARNESS, MEASURED: every lead's taut run through the built model.

tools/wire_total.py left with v1 (11-17), and the cost tool went back to guessing: three Samtec
ribbons at assumed lengths and hook-up wire bought by v1's spools (lead, 2026-11-23). This
routes each run with the taut cable router (tools/cable_route.py) among the lead's last build,
read from the shared scratch cache (cadkit.scratch: no geometry is rebuilt), and prints:

  * each run's taut length and the length to buy or cut (CUT_SLACK and the ends' allowances);
  * the shortest stock Samtec ribbon lead that covers each ribbon run;
  * the hook-up wire per gauge, in metres, for elec/prices.json mechanical.hookup_wire.

THE ENDS are where each lead leaves its connector, read from the boards' footprints placed by
src/new_boards_view.header_pose (brain, connector, UI and fret boards, each where the model places
it) and from the cached parts (motor terminals);
the ones the model does not hold exactly are marked INFERRED in RUNS and in the printout.
CABLE OVER CABLE IS FINE (user, 2026-10-29): ribbons, IDC sockets and terminal plugs are
not obstacles, only boards, printed parts, motors and metal.

    py -3.12 -m tools.harness_runs            (~1-3 min, below-normal priority, < 1.5 GB)
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

INCH = 25.4
# Samtec FFSD-xx-D: made to length in 0.25 in steps (the part number's -LL.LL-), so "stock"
# means the shortest whole inch that covers the run with slack; these are the lengths already
# quoted in elec/prices.json or the standard catalogue steps.
RIBBON_STEPS_IN = (3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 24, 30, 36)
CUT_SLACK = 1.15            # a taut run is never how a cable lies: 15 % for its bends and dress
END_ALLOW = 25.0            # per wire: strip, ferrule / crimp and the fan-out at each end (2 ends)
RIBBON_ALLOW = 15.0         # per ribbon: the IDC socket bodies and the turn out of each socket
SERVICE = {"fret": 100.0}   # a lead to the deck keeps a loop so the panel lifts with it plugged


def _ends():
    """{run name: (a, b, kind, conductors {gauge: n}, notes)} in instrument mm."""
    from src import new_boards_view as V
    hdr = V.header_pose                 # every board's header where the model places that board

    runs = {}
    # the brain stands on the -Y wall, component side +Y; each IDC socket's ribbon leaves away
    # from the board's centre (src/ribbon_socket.py), so the run starts past the socket
    j240, j4, j205 = hdr("brain_board", "J240"), hdr("brain_board", "J4"), hdr("brain_board", "J205")
    c1 = hdr("connector_board", "J1")
    runs["ribbon_brain_connector_30p"] = (
        (j240[0], -80.0, j240[2] - 14.0), (c1[0], c1[1] - 15.0, c1[2] + 7.0), "ribbon", {},
        "brain J240 (ribbon leaves -Z) to connector_board J1 (leaves -Y)")
    # the optical board is the model's stand-in strip on deck_optical (x -32..-23, y -49..52,
    # z 12): INFERRED end at its -Y end, under the deck piece it sits on (a slot through it)
    runs["ribbon_brain_optical_20p"] = (
        (j4[0] + 14.0, -80.0, j4[2]), (-28.0, -50.0, -4.0), "ribbon", {},
        "brain J4 (leaves +X) to the optical board's -Y end, under deck_optical -- INFERRED "
        "(no 2x10 on the optical geometry yet), +16 through the deck piece added")
    # UI J2 is the 2x8 horizontal header at the UI board's -X end (src/ui_panel.py), its pins
    # out past the edge: the IDC socket's ribbon leaves -X
    u2 = hdr("ui_board", "J2")
    runs["ui_ribbon_lead_16p"] = (
        (j205[0] - 14.0, -80.0, j205[2]), (u2[0] - 14.0, u2[1], u2[2]), "ribbon", {},
        "brain J205 (leaves -X) to the UI board's J2 (leaves -X), as placed")
    # the ten motors: connector board J11..J20 (motor k = string k+1) to the motor's own
    # terminals on its driver's -X face; the MX15EDGK plug's wires leave it -Y
    from cadkit import scratch as S
    cache = S.shared_cache(REPO)
    for k in range(10):
        jx, jy, jz = hdr("connector_board", "J%d" % (11 + k))
        b = S.read_brep(cache / ("motor_terminal_%d.brep" % k)).BoundingBox()
        runs["motor_%d" % k] = (
            (jx, jy - 17.0, -94.5), (b.xmin - 3.0, (b.ymin + b.ymax) / 2, (b.zmin + b.zmax) / 2),
            "wire", {22: 2, 26: 2},
            "connector J%d plug (wires leave -Y) to motor_terminal_%d's middle: power and CAN "
            "blocks sit %.0f apart, in END_ALLOW's fan-out" % (11 + k, k, b.ymax - b.ymin))
    # the fret light: connector J4 (MX15, LED_DROP) to fret_led_key J1 (horizontal XH at the
    # board's -Y edge, -X end: the crimp housing goes in from -Y, its wires leave -Y)
    jx, jy, jz = hdr("connector_board", "J4")
    f1 = hdr("fret_led_key", "J1")
    runs["fret"] = ((jx, jy - 17.0, -94.5), (f1[0], f1[1] - 12.0, f1[2]), "wire", {22: 2, 26: 2},
                    "connector J4 to fret_led_key J1 (wires leave -Y), as placed")
    return runs


# what the cable may pass over (cable on cable is fine; these are the cables and their plugs)
_NOT_OBSTACLE = re.compile(r"(_idc|_idc_ribbon|tb_plug|tb_screws|^string_|^motor_lead_|"
                           r"_silk$|^deck_optical$|^optical_board$|^ui_ffc|fret_leds)")


def _guard():
    try:
        import ctypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("a", ctypes.c_size_t), ("b", ctypes.c_size_t), ("c", ctypes.c_size_t),
                        ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),
                                                 ctypes.byref(pmc), pmc.cb)
        if pmc.WorkingSetSize > 1.5e9:
            raise MemoryError("harness_runs stops itself at 1.5 GB")
    except (AttributeError, OSError):
        pass


def _route(a, b, kind, parts):
    import numpy as np
    from tools.cable_route import Obstacles, Router, length
    a, b = np.array(a), np.array(b)
    lo, hi = np.minimum(a, b) - 40.0, np.maximum(a, b) + 40.0
    lo[2] = max(lo[2], -112.0)
    ob = Obstacles(parts, (lo, hi), h=1.0, max_cells=4e6, guard=_guard)
    r = 0.8 if kind == "ribbon" else 1.6          # a ribbon on its flat; a 4-wire lead's bundle
    pts = Router(ob, r, free_near=8.0).route(a, b)
    return length(pts), pts


def main() -> int:
    if os.name == "nt":                            # below normal: never in the way of a build
        import ctypes
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
    from cadkit import scratch as S
    cache = S.shared_cache(REPO)
    man = json.loads((cache / S.MANIFEST).read_text())
    print("model: build #%s (%s)" % (man["build"], man["commit"][:8]))
    names = [n for n in man["parts"] if not _NOT_OBSTACLE.search(n)]
    parts = []
    for n in names:
        try:
            parts.append((n, S.read_brep(cache / (n + ".brep"))))
        except Exception:
            pass
    ends = _ends()
    out, wire = {}, {22: 0.0, 26: 0.0}
    for name, (a, b, kind, cond, note) in ends.items():
        try:
            L, pts = _route(a, b, kind, parts)
        except Exception as e:                     # noqa: BLE001 -- say so, keep the others
            L, pts = None, []
            print("  %-28s NO ROUTE (%s): %s" % (name, type(e).__name__, e))
            continue
        L += 16.0 if name == "ribbon_brain_optical_20p" else 0.0
        if kind == "ribbon":
            need = L * CUT_SLACK + RIBBON_ALLOW
            stock = next((s for s in RIBBON_STEPS_IN if s * INCH >= need), None)
            out[name] = {"taut_mm": round(L, 1), "need_mm": round(need), "stock_in": stock, "note": note}
            print("  %-28s taut %6.1f  need %4.0f mm  -> %s in   (%s)" % (name, L, need, stock, note))
        else:
            cut = L * CUT_SLACK + 2 * END_ALLOW + SERVICE.get(name, 0.0)
            for g, n in cond.items():
                wire[g] += n * cut
            out[name] = {"taut_mm": round(L, 1), "cut_mm": round(cut), "wires": cond, "note": note}
            print("  %-28s taut %6.1f  cut  %4.0f mm x %s   (%s)" % (name, L, cut, cond, note))
    print("hook-up wire: " + ", ".join("%d AWG %.2f m" % (g, m / 1000.0) for g, m in wire.items()))
    res = REPO / "elec" / "harness_runs.json"
    res.write_text(json.dumps({"build": man["build"], "commit": man["commit"], "cut_slack": CUT_SLACK,
                               "end_allow_mm": END_ALLOW, "runs": out,
                               "hookup_m": {str(g): round(m / 1000.0, 2) for g, m in wire.items()}},
                              indent=1))
    print("wrote", res.relative_to(REPO).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
