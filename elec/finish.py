"""Route a board, then hand the router's own failures back to the generator.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/finish.py elec/out/optical

⚠ THIS EXISTS BECAUSE PRE-LAYING COPPER IS A TRADE, NOT AN IMPROVEMENT, and the trade
only pays on the nets the router cannot do. Measured on three boards, freezing every
short net in advance took lever_sensor from 4 unconnected to 7 and output_panel from 2 to
5, while taking optical from 26 to 12. The mechanism is not subtle once seen: the
router's strength is that every path it lays is NEGOTIABLE -- it can rip one up to make
room for another -- and copper laid before it starts is not in that negotiation at all.
It is an obstacle, like a pad or a board edge, and it can never be reconsidered.

So pre-laying converts negotiable copper into fixed copper, and doing that to nets the
router would have solved anyway is pure loss: it takes away the work it does well, leaves
the work it does badly, and shrinks the space left to do it in.

The fix is to stop guessing which nets need help. Route the board; ask DRC what is still
unconnected; lay THOSE nets deterministically; route again. Nothing is declared in
advance and nothing goes stale, because the list is measured fresh every run.

AND KEEP THE BETTER OF THE TWO. The second pass can lose -- the copper it adds is an
obstacle like any other and may cost more than it buys. This compares and keeps whichever
board is actually better, so a retry can never make a board worse than not retrying.
That guarantee is only available because the pipeline is reproducible: without it, "worse"
and "a different roll of the dice" are the same measurement.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

import netcheck
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
PY = sys.executable


def _drc(stem):
    """(unconnected count, the net names involved) for the board at `stem`."""
    out = stem + ".finish.drc.json"
    # ⚠ NO --severity-error: THIS PIPELINE HAD NEVER SEEN A DRC WARNING. Asking only for
    # errors is asking KiCad to hide a whole class of finding, and it hid five on the
    # optical board -- four dangling vias and a 9 um track fragment. The vias turned out
    # to be the router's abandoned stubs on the very nets still unconnected, which is
    # useful corroboration, and the fragment is copper that drop_degenerate's 5 um floor
    # is just too low to catch.
    # Warnings do NOT fail a board. They are printed, because a warning nobody prints is
    # the same as a warning nobody gets.
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json",
                    "-o", out, stem + ".kicad_pcb"], capture_output=True, text=True)
    d = json.load(open(out, encoding="utf-8"))
    nets = set()
    for v in d.get("unconnected_items", []):
        for item in v["items"]:
            m = re.search(r"\[([^\]]+)\]", item["description"])
            if m:
                nets.add(m.group(1))
    # ⚠ WHAT IS RETURNED IS THE UNEXPECTED COUNT, NOT THE TOTAL. The optical board
    # declares twenty courtyard overlaps and reporting the total taught everyone to read
    # "20" as "fine" -- at which point 23 also reads as fine for exactly as long as it
    # takes somebody to stop listing them. See netcheck.classify_violations.
    declared = netcheck.optical_declared if "optical" in os.path.basename(stem) \
        else (lambda t, r: False)
    # errors decide the board; warnings are reported and nothing more
    warn = [v for v in d.get("violations", []) if v.get("severity") == "warning"]
    d = dict(d, violations=[v for v in d.get("violations", [])
                            if v.get("severity") != "warning"])
    ok, bad = netcheck.classify_violations(d, declared)
    if warn:
        import collections as _c
        kinds = _c.Counter(v["type"] for v in warn)
        print("  %d DRC warning(s): %s"
              % (len(warn), ", ".join("%s x%d" % kv for kv in sorted(kinds.items()))))
    if ok:
        print("  %d declared violation(s) (%s), %d unexpected"
              % (len(ok), "sensor triplets" if ok else "-", len(bad)))
    for t, refs in bad:
        print("     UNEXPECTED %s: %s" % (t, " + ".join(refs)))
    return len(d.get("unconnected_items", [])), sorted(nets), len(bad)


def _run(script, stem):
    """Run a pipeline step, streaming its output as it arrives.

    ⚠ STREAM IT. Capturing the output and printing it at the end made a twenty-minute
    run look exactly like a hung one -- two routing passes on a 153-part board, and not a
    character until both had finished. For a tool whose whole purpose is to be left
    running unattended, "is it working or is it stuck?" is the one question it has to be
    able to answer, and a progress line costs nothing.
    """
    out = []
    proc = subprocess.Popen([PY, os.path.join(HERE, script), stem],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1)
    for line in proc.stdout:
        if "image handler" in line:
            continue          # KiCad's Python greets every start-up with a dozen
        out.append(line)
        sys.stdout.write("    " + line)
        sys.stdout.flush()
    if proc.wait():
        raise SystemExit("%s failed on %s" % (script, stem))
    return "".join(out)


def finish(stem, rounds=1):
    """Route `stem`; with rounds>1, retry the nets the router could not finish.

    ⚠ THE RETRY IS OFF BY DEFAULT BECAUSE IT HAS NEVER YET PAID. Re-measured on the
    optical board 2026-09-17, now that layout's inner-layer fallback works: pass 1 gives
    1 unconnected and 0 violations, pass 2 gives 3 and 7. It doubles the wall clock of
    every run and its only achievement is not making things worse, which the
    keep-the-better-board rule guarantees anyway. (The old figures here, 12 -> 27, were
    from before the board had a working pre-lay; the conclusion survived the re-measure
    but the numbers did not.)

    ⚠ AND THE REASON RECORDED HERE WAS WRONG, WHICH MATTERS MORE THAN THE NUMBERS. It
    said a net the router could not finish is usually one the generator cannot finish
    either, blocked by the same geometry. Printing the names of the edges the pre-lay
    skips shows otherwise: the retry LAYS its net without difficulty, 8 segments. What it
    costs is everything laid after it -- local nets drop from 90 segments with nothing
    skipped to 76 with EIGHTEEN skipped, every one a short cluster hop in the strip that
    the long retried run has just cut across. The 3 unconnected and 7 violations are that
    damage, not the retried net.

    ⚠ SO THE FIX LOOKS LIKE AN ORDERING FIX -- AND IT IS NOT SAFE YET. Running local nets
    BEFORE the retry, by the same "fewer alternatives first" argument that put the
    stitcher ahead of local nets in layout.py, does remove the interference exactly:
    local nets keep all 90 segments with nothing skipped. But route.py then exits
    non-zero on the second pass, twice out of twice, where the current order completes
    cleanly, and the failure is at interpreter shutdown AFTER the board has been written
    correctly -- no traceback, the segments imported, the file on disk. Something about
    the extra pre-laid copper upsets pcbnew's teardown.

    Reverted until that is understood, because the only path the reorder helps is the one
    it breaks. To reproduce: move the local_nets block in layout.py above the retry block
    and run finish(stem, rounds=2) on optical.
    """
    retry = stem + ".retry.json"
    if os.path.isfile(retry):
        os.remove(retry)          # always start from the board as designed
    _run("layout.py", stem)
    _run("route.py", stem)
    best_n, nets, best_v = _drc(stem)
    print("  pass 1: %d unconnected, %d violation(s)" % (best_n, best_v))
    # ⚠ THE DRC FILE TRAVELS WITH THE BOARD, because otherwise it does not. This routine
    # keeps the BEST board but _drc overwrites .finish.drc.json on every pass, so after a
    # two-round run the board on disk was pass 1 and the DRC file beside it described
    # pass 2 -- a file whose whole purpose is to say what the board is, saying something
    # else. It reads as a board that just got worse, and it is the same file the retry
    # list is built from. Caught by re-running DRC by hand and getting a different answer
    # from the one lying next to the board.
    shutil.copy(stem + ".kicad_pcb", stem + ".best.kicad_pcb")
    shutil.copy(stem + ".finish.drc.json", stem + ".best.drc.json")

    for k in range(2, rounds + 1):
        if not best_n:
            break
        json.dump(nets, open(retry, "w", encoding="utf-8"))
        _run("layout.py", stem)
        _run("route.py", stem)
        n, nets_now, v = _drc(stem)
        print("  pass %d: %d unconnected, %d violation(s)" % (k, n, v))
        # ⚠ STRICTLY BETTER OR IT DOES NOT COUNT. A violation is worse than an
        # unconnected pad -- one is a board that cannot be made, the other a board that
        # is not finished -- so violations are compared first and only then the count.
        if (v, n) < (best_v, best_n):
            shutil.copy(stem + ".kicad_pcb", stem + ".best.kicad_pcb")
            shutil.copy(stem + ".finish.drc.json", stem + ".best.drc.json")
            best_n, best_v, nets = n, v, nets_now
        else:
            print("  pass %d did not improve on pass %d -- keeping the better board"
                  % (k, k - 1))
            break

    if os.path.isfile(retry):
        os.remove(retry)
    shutil.copy(stem + ".best.kicad_pcb", stem + ".kicad_pcb")
    os.remove(stem + ".best.kicad_pcb")
    shutil.copy(stem + ".best.drc.json", stem + ".finish.drc.json")
    os.remove(stem + ".best.drc.json")
    print("%s: %d unconnected, %d violation(s)"
          % (os.path.basename(stem), best_n, best_v))
    return best_n, best_v


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: finish.py <stem> [<stem> ...]")
    for st in sys.argv[1:]:
        finish(os.path.abspath(st))
