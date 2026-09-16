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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
PY = sys.executable


def _drc(stem):
    """(unconnected count, the net names involved) for the board at `stem`."""
    out = stem + ".finish.drc.json"
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error", "--format", "json",
                    "-o", out, stem + ".kicad_pcb"], capture_output=True, text=True)
    d = json.load(open(out, encoding="utf-8"))
    nets = set()
    for v in d.get("unconnected_items", []):
        for item in v["items"]:
            m = re.search(r"\[([^\]]+)\]", item["description"])
            if m:
                nets.add(m.group(1))
    return len(d.get("unconnected_items", [])), sorted(nets), len(d["violations"])


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

    ⚠ THE RETRY IS OFF BY DEFAULT BECAUSE IT HAS NEVER YET PAID. Measured on three
    boards: lever_sensor 4 -> 4, output_panel 2 -> 2, optical 12 -> 27 with violations.
    It doubles the wall clock of every run -- twenty minutes instead of ten on the
    optical board -- and so far its only achievement is not making things worse, which
    the keep-the-better-board rule guarantees anyway.
    
    The idea still looks right: freeze the nets the router demonstrably failed rather
    than the ones guessed in advance. What the numbers say is that a net the router could
    not finish is usually one the generator cannot finish either -- they are blocked by
    the same geometry, and the generator has strictly fewer moves. Worth keeping and
    worth having off.
    """
    retry = stem + ".retry.json"
    if os.path.isfile(retry):
        os.remove(retry)          # always start from the board as designed
    _run("layout.py", stem)
    _run("route.py", stem)
    best_n, nets, best_v = _drc(stem)
    print("  pass 1: %d unconnected, %d violation(s)" % (best_n, best_v))
    shutil.copy(stem + ".kicad_pcb", stem + ".best.kicad_pcb")

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
            best_n, best_v, nets = n, v, nets_now
        else:
            print("  pass %d did not improve on pass %d -- keeping the better board"
                  % (k, k - 1))
            break

    if os.path.isfile(retry):
        os.remove(retry)
    shutil.copy(stem + ".best.kicad_pcb", stem + ".kicad_pcb")
    os.remove(stem + ".best.kicad_pcb")
    print("%s: %d unconnected, %d violation(s)"
          % (os.path.basename(stem), best_n, best_v))
    return best_n, best_v


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: finish.py <stem> [<stem> ...]")
    for st in sys.argv[1:]:
        finish(os.path.abspath(st))
