"""The power gate: widepath's verdict on every quality.power_paths entry of a board.

    run(stem, report=".power_gate.txt") -> (n_fail, n_warn), or None if it did not run
    verdicts(stem) -> the gate's JSON for the board as it is now (runs the gate if needed)

The routed board is copied, its zones refilled, its gerbers exported, and rasterpath --specs
judges every path on the copper as fabbed: every layer rasterised, layers joined through the
plated holes, inner copper scaled to outer-equivalent, a declared neck graded against its
declaration (widepath.judge). It writes <stem><report> (the text lines) and the same verdicts
as JSON beside it (<stem><report> with .json for .txt), stamped with the board file's hash.

⚠ ONE JUDGE OF WIDTH (lead, 2026-11-26). finish's gate and quality A1 used to measure power
copper with two different models, and they disagreed on brain_board fold10: A1 failed +24V
Q209.5>F203.1 on a 0.08 mm axis cut through ONE layer's pour (the F.Cu fill, four pieces),
while the current runs in the In3.Cu band the gate counts (0.95 outer-equivalent, PASS); and A1
failed the declared pin-pitch necks (U205.11, U221.6) the gate grades against their declaration.
A1 now takes its width verdict from here; what A1 still measures itself is connectivity and the
DC drop, which the gate does not.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
# kicad-cli sits beside the interpreter this runs under (<KiCad>/bin); $KICAD_CLI overrides
KICAD_CLI = os.environ.get("KICAD_CLI") or next(
    (p for p in (os.path.join(os.path.dirname(os.path.abspath(sys.executable)), n)
                 for n in ("kicad-cli.exe", "kicad-cli")) if os.path.isfile(p)),
    r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")


def _scipy_py():
    """A python with numpy + scipy for widepath (KiCad's has none)."""
    if os.environ.get("CADKIT_SCIPY_PY"):
        return [os.environ["CADKIT_SCIPY_PY"]]
    if shutil.which("py"):
        return [shutil.which("py"), "-3.12"]
    return [shutil.which("python3") or "python"]


def board_hash(stem):
    """The hash of <stem>.kicad_pcb as saved: a verdict belongs to exactly this board."""
    with open(stem + ".kicad_pcb", "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()


def json_path(stem, report=".power_gate.txt"):
    return stem + report[:-4] + ".json"


def run(stem, report=".power_gate.txt", quiet=False):
    """Run the gate on <stem>.kicad_pcb; (n_fail, n_warn), None if it did not run."""
    say = (lambda *_a: None) if quiet else print
    h = board_hash(stem)
    pg = stem + ".pg"
    shutil.copy(stem + ".kicad_pcb", pg + ".kicad_pcb")
    subprocess.run([PY, "-c",
                    "import sys, pcbnew; sys.path.insert(0, %r); import stable_fill\n"
                    "b = pcbnew.LoadBoard(%r); stable_fill.fill(b, b.Zones()); pcbnew.SaveBoard(%r, b)\n"
                    "import os; os._exit(0)" % (HERE, pg + ".kicad_pcb", pg + ".kicad_pcb")],
                   capture_output=True, text=True)
    gd = pg + "_gerb"
    os.makedirs(gd, exist_ok=True)
    subprocess.run([KICAD_CLI, "pcb", "export", "gerbers", "-o", gd + os.sep, pg + ".kicad_pcb"],
                   capture_output=True, text=True)
    subprocess.run([KICAD_CLI, "pcb", "export", "drill", "-o", gd + os.sep, pg + ".kicad_pcb"],
                   capture_output=True, text=True)
    specs = stem + ".power_specs.json"
    subprocess.run([PY, os.path.join(HERE, "power_specs.py"), stem, specs],
                   capture_output=True, text=True)
    jp = json_path(stem, report)
    if os.path.exists(jp):
        os.replace(jp, jp + ".old")            # never read a verdict this run did not write
    r = subprocess.run(_scipy_py() + [os.path.join(HERE, "rasterpath.py"), gd,
                                      os.path.basename(pg), "0.025", "--specs", specs,
                                      "--open-ok", "--json", jp],
                       capture_output=True, text=True)
    lines = [ln for ln in r.stdout.splitlines() if ln[:4] in ("FAIL", "WARN", "PASS", "OPEN")
             or ln.startswith("rasterpath:")]
    open(stem + report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    nf = sum(ln.startswith("FAIL") for ln in lines)
    nw = sum(ln.startswith("WARN") for ln in lines)
    no = sum(ln.startswith("OPEN") for ln in lines)
    if not any(ln.startswith("rasterpath:") for ln in lines) or not os.path.exists(jp):
        say("  ⚠ power gate DID NOT RUN: %s" % (r.stderr.strip().splitlines() or ["?"])[-1])
        return None
    d = json.load(open(jp, encoding="utf-8"))
    d["board_sha1"] = h
    json.dump(d, open(jp, "w", encoding="utf-8"), indent=1)
    for ln in lines:
        if ln.startswith("FAIL"):
            say("    " + ln)
    say("  power gate%s: %d FAIL, %d OPEN, %d WARN of %d power paths (%s)"
        % (" (pre-close)" if report != ".power_gate.txt" else "", nf, no, nw,
           sum(ln[:4] in ("FAIL", "WARN", "PASS", "OPEN") for ln in lines),
           os.path.basename(stem) + report))
    return nf, nw


def verdicts(stem):
    """The gate's verdicts for <stem>.kicad_pcb as it is now: finish's final gate when it was
    run on this exact board, else a fresh run (report .power_gate.quality.txt). None if the
    gate cannot run."""
    h = board_hash(stem)
    for report in (".power_gate.txt", ".power_gate.quality.txt"):
        jp = json_path(stem, report)
        if os.path.exists(jp):
            try:
                d = json.load(open(jp, encoding="utf-8"))
            except ValueError:
                continue
            if d.get("board_sha1") == h:
                return d
    if run(stem, ".power_gate.quality.txt", quiet=True) is None:
        return None
    return json.load(open(json_path(stem, ".power_gate.quality.txt"), encoding="utf-8"))
