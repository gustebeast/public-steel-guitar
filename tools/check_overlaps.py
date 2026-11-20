"""Overlap checker for the pedal-steel assembly.

Project glue over the shared engine in ``cadkit/overlap_check.py``: this file
supplies the placed parts (``src.build.collect_components``) and the project's
``intended()`` whitelist of designed contacts (the direct instrument keeps its own:
src.direct_bench.is_intended); the engine runs the parallel boolean scan and reports the
UNINTENDED interpenetrations.

  py -3.12 -m tools.check_overlaps            # fast scan (skips belts -- see below)
  py -3.12 -m tools.check_overlaps --full     # check EVERY part (belts too) -- the lead's build runs this
  py -3.12 -m tools.check_overlaps --all      # also list intended contacts
  py -3.12 -m tools.check_overlaps --only endplate,keyhead            # just these bases
  py -3.12 -m tools.check_overlaps --exclude string,wire            # skip more bases
  py -3.12 -m tools.check_overlaps -j 14      # set worker count (default: cores/2)
  py -3.12 -m tools.check_overlaps --serial   # single-process (baseline/debug)
  py -3.12 -m tools.check_overlaps --coils    # springs/threads as drawn (default: as cylinders)

The belts are slow to boolean (swept compounds dominate the runtime) and rarely
move, so the DEFAULT scan skips them for a quick inner-loop check; pass --full for
the complete gate. Contributors do NOT run it before submitting: the lead's
`agent_sync build` runs it on the merged tree (cadkit/AGENTS.md); agents gate their
portion with `scratch_view --gate`. Every run prints what it skipped.

Exit code is the number of unintended overlapping pairs (0 = clean).

The heavy project build is imported only inside main(), so spawned workers (which
re-import this module) don't rebuild it — they just load the serialized shapes.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

from cadkit.overlap_check import run              # shared engine

def base(name: str) -> str:
    # Strip EVERY trailing index group, not just the last one. Parts numbered per
    # string used to be `screw_bearing_4`, but a second index arrived when each
    # screw grew three bearings (`screw_bearing_4_1` = string 4, position 1). A
    # single-group strip left base = "screw_bearing_4", which matches nothing in
    # the allow list — so the designed bearing-in-rail contact quietly stopped
    # being allow-listed, and only stayed silent because it sits under VOL_EPS.
    name = re.sub(r"(_\d+)+$", "", name)
    # THE Pi IS ONE BOUGHT BOARD DRAWN AS SEVERAL PARTS, one per colour (pi4_shells,
    # pi4_black ...; src/pi4b.py). Whatever may touch the Pi may touch any of them --
    # but its header PINS stay themselves: they stand inside the cap's socket, and that
    # one designed fit must not make the rest of the Pi invisible to the cap. So does its
    # microSD CARD, which stands past the board's edge where the cradle's wall is.
    if name.startswith("pi4_") and name not in ("pi4_pins", "pi4_card"):
        return "pi4"
    # SO IS THE MOTOR (src/servo42d.py: one solid per material). Whatever may touch the
    # motor -- its pulley on the shaft, the bank's faceplate walls -- may touch any of it.
    if _MOTOR_PART.match(name):
        return "motor"
    return name


_MOTOR_PART = re.compile(r"^motor_(?:face|stack|shaft|coil_plug|driver|terminal|coil_terminal"
                         r"|screws|term_screws|buttons|lead_[a-z]+)$")


# THE DESIGNED CONTACTS. The direct instrument (the main build since 2026-11-13) judges every
# pair with one of its parts in it itself (src.direct_bench.is_intended). The v1 instrument's
# allow-lists -- per-string drive contacts, the chassis, the endplates, the deck panels, the
# levers, the pedals, the harness and the DEFERRED overlaps -- went with it (lead, 2026-11-17,
# v1 removal round 3; git tag v1-instrument): measured on the direct assembly and the wood
# bench, not one pair reached them.
def intended(na, nb) -> bool:
    from src import direct_bench as _DB
    if _DB.owns(na) or _DB.owns(nb):
        return _DB.is_intended(na, nb)
    # A BOARD'S LETTERING against whatever that face of the board is seated on. The ink is
    # drawn 0.02 mm PROUD of the laminate so that it is a solid at all (board_geom.SILK_T),
    # so a board that lies on a printed face has its lettering 0.02 into that face: nothing a
    # print or a fab can act on. The BOARD itself is still gated against the same part.
    if "_silk" in na or "_silk" in nb:
        return True
    # ONE ROUTED BOARD DRAWN AS SEVERAL PARTS (src/new_boards_view.py: the laminate with its
    # parts, the CM5 on its plugs, the ribbon sockets, the screw terminal): its own layout is
    # checked by its courtyards in pcbflow; here it is gated against everything else.
    for b in ("brain_board", "connector_board"):
        if na.startswith(b) and nb.startswith(b):
            return True
    return False


# Base names skipped by default: the belts are swept compounds whose booleans
# dominate the runtime, and they rarely move. --full overrides this.
DEFAULT_SKIP = {"belt", "belt_clamp"}


# A 0.025 mm bite over an 11 mm run is only ~0.21 mm^3, so the engine's 1.0 default
# is BLIND to thin, tall interferences — exactly the shape a bearing bore, a press
# fit or two near-parallel walls make. One such (guide-rod bore into a bridge
# bearing) sat green until it was found by hand. Measured cost of dropping to 0.05
# on this assembly: 392 -> 492 interpenetrating pairs, but only 2 extra UNINTENDED,
# and both are wire-vs-solid clips, which this project's own WIRE_OK doctrine calls
# real routing bugs. So it buys sensitivity at no noise cost.
MIN_VOL = 0.05

# INCREMENTAL PAIR CACHE (cadkit.overlap_check): a pair's common volume depends only on
# the two shapes, so it is keyed by their BRep fingerprints and reused while both are
# byte-identical. A build that changed three parts re-booleans only those parts' pairs.
# NOT an exclusion list -- nothing is assumed safe; a changed part always recomputes.
# Gitignored: it is derived, per-worktree, and cheap to rebuild.
CACHE = str(pathlib.Path(__file__).resolve().parent.parent / ".overlap-cache.json")
HELIX_CACHE = str(pathlib.Path(__file__).resolve().parent.parent / ".helix-proxy-cache.json")


def gate(comps, *, full=False, only=(), exclude=(), jobs=None, show_all=False,
         cache=None, coils=False) -> int:
    """Scan ALREADY-BUILT components and return the unintended-overlap count.

    ``comps`` is ``[(name, cq.Shape), ...]`` — i.e. what ``collect_components()``
    yields, already ``.val()``-ed. Split out of ``main()`` so the BUILD can gate
    the model it just built instead of paying for a second full build: the
    pairwise scan is ~13 s, the build behind it is ~5.5 min.
    """
    only = set(only)
    if only:
        comps = [(n, s) for n, s in comps if base(n) in only]
        print(f"checking ONLY base names: {sorted(only)}")
    else:
        skip = (set() if full else set(DEFAULT_SKIP)) | set(exclude)
        if skip:
            comps = [(n, s) for n, s in comps if base(n) not in skip]
            print(f"skipping base names (pass --full to include): {sorted(skip)}")
    if not coils:
        # HELICES AS CYLINDERS (user, 2026-11-12): a spring's coils or a screw's thread cost
        # minutes a pair to boolean and answer no clearance question their cylinder doesn't
        # (the cylinder is the stricter answer). tools/helix_proxy.py; --coils keeps them.
        import time
        from tools.helix_proxy import swap
        t0 = time.time()
        comps, hit = swap(comps, cache_path=HELIX_CACHE)
        bases = sorted({base(n) for n in hit})
        print(f"helices checked as their cylinders: {len(hit)} parts ({', '.join(bases)}) "
              f"in {time.time() - t0:.1f} s (--coils to check the coils)")
    return run(comps, intended, jobs=jobs, show_all=show_all, min_vol=MIN_VOL,
               cache=CACHE if cache is None else cache)


def main():
    ap = argparse.ArgumentParser(description="Pedal-steel assembly overlap checker.")
    ap.add_argument("--all", action="store_true", help="also list intended contacts")
    ap.add_argument("--full", action="store_true",
                    help=f"check ALL parts (default skips {sorted(DEFAULT_SKIP)})")
    ap.add_argument("--exclude", default="", metavar="A,B",
                    help="comma-separated base names to also skip")
    ap.add_argument("--only", default="", metavar="A,B",
                    help="check ONLY these comma-separated base names")
    ap.add_argument("--serial", action="store_true", help="single-process (baseline/debug)")
    ap.add_argument("--coils", action="store_true",
                    help="check springs and threads as drawn, not as their cylinders (slow)")
    ap.add_argument("-j", "--jobs", type=int, default=None,
                    help="worker processes (default: cores/2)")
    args = ap.parse_args()

    from src.build import collect_components       # heavy: deferred so workers skip it

    comps = [(n, wp.val()) for n, wp in collect_components()]
    sys.exit(gate(comps,
                  full=args.full,
                  only=[s for s in args.only.split(",") if s],
                  exclude=[s for s in args.exclude.split(",") if s],
                  jobs=1 if args.serial else args.jobs,
                  show_all=args.all,
                  coils=args.coils))


if __name__ == "__main__":
    main()
