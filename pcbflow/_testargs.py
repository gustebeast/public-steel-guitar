"""A test that runs on a real board (a run directory, a stem, two boards) says SKIP and exits 0
when it is run without one, so a plain run of the whole suite reads clean (lead 2026-11-27):

    import _testargs
    _testargs.need(2, "UNROUTED ROUTED boards (brain_board rPS_e3)")

An argument counts as given when it exists as a path, or as a stem (<arg>.kicad_pcb)."""
import os
import sys


def _there(a):
    return os.path.exists(a) or os.path.exists(a + ".kicad_pcb")


def need(n, what):
    args = sys.argv[1:1 + n]
    if len(args) < n or not all(_there(a) for a in args):
        print("SKIP: needs %s" % what)
        sys.stdout.flush()
        sys.exit(0)
