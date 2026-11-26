"""quality A1 takes its width verdict from the power gate: one judge of width (lead, 2026-11-26;
brain_board fold10: A1's one-layer axis cut read +24V at 0.08 mm, the gate 0.95 PASS, and A1
failed the declared pin-pitch necks the gate grades against their declaration).

    py -3.12 test_a1_gate.py

Checks: A1 has no width model of its own left (no axis cut, no pin-entry rule); A1 asks
power_gate.verdicts; power_specs builds a path for EVERY destination part, not the first;
rasterpath writes its verdicts as JSON; a gate WARN (short or declared neck) is an A1 pass,
a FAIL / DECLARED NECK BROKEN an A1 fail; a verdict is matched by net and part pair; and
power_gate refuses a verdict for a different board file. Exit 0 = PASS.
"""
import ast
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
rd = lambda f: open(os.path.join(HERE, f), encoding="utf-8").read().replace("\r\n", "\n")
q, ps, rp, pg, fin = (rd(f) for f in ("quality.py", "power_specs.py", "rasterpath.py",
                                      "power_gate.py", "finish.py"))
bad = []
for name in ("_pour_narrowest", "_pin_entry", "PIN_ENTRY_MM"):
    if name in q:
        bad.append("quality.py still has its own width model (%s)" % name)
if "power_gate.verdicts(ctx.stem)" not in q:
    bad.append("A1 does not take the power gate's verdicts")
if 'for to in (e["to"] if isinstance(e["to"], list) else [e["to"]]):' not in ps:
    bad.append("power_specs judges only the first destination of a path")
if '"--json"' not in rp:
    bad.append("rasterpath does not write its verdicts as JSON")
if "power_gate.run(stem, report)" not in fin:
    bad.append("finish's gate is not power_gate.run (two copies of the gate)")

# _gate_row and the verdict mapping, from quality.py's own source (no pcbnew needed)
tree = ast.parse(q)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_gate_row")
ns = {}
exec(compile(ast.Module([fn], []), "quality._gate_row", "exec"), ns)
gate = {"neck_ratio": 2.0, "paths": [
    {"net": "+3V3D", "frm": ["U21.2"], "to": ["U17.10", "U1.23"], "verdict": "PASS"},
    {"net": "+3V3D", "frm": ["U21.2"], "to": ["U202.3"], "verdict": "WARN", "declared": "k"}]}
if (ns["_gate_row"](gate, "+3V3D", "U21.2", "U1.36") or {}).get("verdict") != "PASS":
    bad.append("a row is not matched to its part pair (U21>U1 by another U1 pin)")
if ns["_gate_row"](gate, "+3V3D", "U21.2", "U16.6") is not None:
    bad.append("a row matched a path to a different part")
if ns["_gate_row"](gate, "+5V", "U21.2", "U17.10") is not None:
    bad.append("a row matched a path on a different net")
i = q.index("gr = _gate_row(gate, net, p[\"from\"], dst)")
blk = q[i:q.index("# ...and the DROP", i)]
if 'elif gr["verdict"] in ("PASS", "WARN"):\n                    width_ok = True' not in blk:
    bad.append("a gate WARN (a short or declared neck) is not an A1 pass")
if "width_ok = False" not in blk or "DECLARED NECK BROKEN" not in blk:
    bad.append("a gate FAIL / broken declared neck is not an A1 fail")
if "width_ok, width_txt = None" not in blk:
    bad.append("a board the gate could not judge is not left OPEN")

# power_gate.verdicts: a JSON for another board file is not used
import power_gate  # noqa: E402
d = tempfile.mkdtemp()
stem = os.path.join(d, "b")
open(stem + ".kicad_pcb", "w").write("(kicad_pcb A)")
json.dump({"board_sha1": "not-this-board", "paths": []}, open(stem + ".power_gate.json", "w"))
power_gate.run = lambda *a, **k: None                  # the gate cannot run here
if power_gate.verdicts(stem) is not None:
    bad.append("power_gate.verdicts used a verdict for a different board file")
json.dump({"board_sha1": power_gate.board_hash(stem), "paths": [1]}, open(stem + ".power_gate.json", "w"))
if (power_gate.verdicts(stem) or {}).get("paths") != [1]:
    bad.append("power_gate.verdicts ignored finish's verdict for this exact board")

for b_ in bad:
    print("  FAIL:", b_)
print("PASS" if not bad else "FAIL")
sys.exit(1 if bad else 0)
