"""Pour trial: an intent's pours laid on a finished run's placement, then layout.py (with its pour gate).

    py -3.12 pourtry.py SRC_RUN_DIR INTENT.json OUT_DIR      (OUT_DIR must not exist)

A pour / layer-assignment change needs its fills, and place_flow lays pours only after placement
(--place-only stops before them) -- an hour per trial. This takes SRC's final placement (its
output_board.board.json placements; a --place-only run's flow/init.json when that is all there is)
and runs place_flow's own _intent, kelvin_seats, auto_pour, _raise_widths and _pours with the new
intent, writes OUT_DIR/output_board.{net,parts.json,kicad_pro,board.json}, and runs layout.py there:
POUR CUT lines, declared-copper refusals and the unrouted board in minutes. The placement is NOT
redone, so an intent that moves parts is refused where its declared copper names a pad that did
not move with it ("copper for X names P, but no track end lands on that pad") -- trial pours on a
run of the same placement intent.

Environment as for place_flow: PCBFLOW_FOOTPRINT_DIRS, PCBFLOW_PROJECT (and PYTHONPATH for a
headless pcbnew, if the project uses one). Two-sided boards (back_refs) are refused.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main(src, intent, out):
    sys.path.insert(0, HERE)
    cwd = os.getcwd()
    os.chdir(HERE)
    try:
        import place_flow as PF
        import place_intent as pi
    finally:
        os.chdir(cwd)
    os.makedirs(out)
    for f in ("output_board.net", "output_board.parts.json", "output_board.kicad_pro"):
        shutil.copy(os.path.join(src, f), out)
    stem = os.path.join(out, "output_board")
    notes = json.load(open(os.path.join(src, "flow", "input.board.json"), encoding="utf-8"))
    bj = os.path.join(src, "output_board.board.json")
    pl = json.load(open(bj, encoding="utf-8")).get("placements")
    if not pl:
        pl = {k: v for k, v in json.load(open(os.path.join(src, "flow", "init.json"), encoding="utf-8")).items()}
        print("pourtry: %s has no placements -- using flow/init.json (a --place-only run)" % bj)
    parts = json.load(open(stem + ".parts.json", encoding="utf-8"))["parts"]
    rules, _ = PF._intent(json.load(open(intent, encoding="utf-8")), parts, notes, stem + ".net", True)
    if pi.back_refs(rules):
        raise SystemExit("pourtry: a two-sided board (back_refs) -- not handled")
    rules, _kl, kb = pi.kelvin_seats(rules, parts, pi.read_values(stem + ".net"))
    if kb:
        raise SystemExit("pourtry: kelvin ties off their land:\n  " + "\n  ".join(kb))
    rules, _ap = pi.auto_pour(rules, parts, notes)
    for w in PF._raise_widths(notes, parts, pl, False):
        print("WIDTH", w)
    for p in PF._pours(notes, parts, pl, rules, list(notes.get("zones", []) or [])):
        print("POUR", p)
    json.dump(dict(notes, placements=pl), open(stem + ".board.json", "w"), indent=0)
    r = subprocess.run([PF.KICAD_PY, os.path.join(HERE, "layout.py"), stem], cwd=HERE,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print("\n".join(l for l in (r.stdout + r.stderr).splitlines() if "duplicate image handler" not in l))
    print("pourtry: layout rc %d -> %s.kicad_pcb" % (r.returncode, stem))
    return r.returncode


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__.strip().splitlines()[2].strip())
    sys.exit(main(*(os.path.abspath(a) for a in sys.argv[1:4])))
