"""Emit docs/rig.json -- the animation manifest the web viewer plays.

THE DIRECT INSTRUMENT HAS NO ANIMATION YET (lead, 2026-11-17). The rig this file used to
write was the v1 belt drive's: each string's carriage riding its vertical leadscrew, the
screw and motor pulleys turning, the belt clamps sliding along their runs, and the levers
and pedals swinging at v1's stations. None of those parts are in the direct instrument, so
that rig animated nothing and its code reached into v1 geometry on every build. It is in
the git tag v1-instrument.

What the viewer still uses is written: the copedent (its control panel and key map), the
open tuning, the deck's name prefixes (the "hide the deck" toggle) and the build number.
The per-string motion and the pedal poses are empty lists, which the viewer treats as
"nothing to move". When the direct drive gets animated, its nut and yoke ride the screw
along X; that is new work for cadkit/web/viewer, not a revival of the old Z carriage.

  py -3.12 -m tools.export_rig
"""
from __future__ import annotations

import json
import pathlib

from src import dimensions as D

REPO = pathlib.Path(__file__).resolve().parents[1]
RIG = REPO / "docs" / "rig.json"

# ── THE C6 COPEDENT (user's own, from their chart) ───────────────────────────
# As STRING NUMBERS (accepted standard: string 1 = highest pitch, furthest from the
# player). This model indexes strings 0..9 from that same far edge, so string number
# N = index + 1 (string 1 = index 0).
#
# Open tuning, strings 1..10:  D4 E4 C4 A3 G3 E3 C3 A2 F2 C2
#
# WAS the Emmons E9 A/B/C — three pedals, all raises. That was wrong twice over: the
# instrument's design bounds are C6, not E9, and the hardware has FIVE pedals and
# SIX levers, so the viewer was claiming three-elevenths of the controls.
#
# PEDAL NUMBERING: the user's chart is a DOUBLE-NECK layout whose pedal columns are
# shared with an E9 top neck, so its C6 moves sit on columns 4..8. Ours are P1..P5;
# the chart's number is 3 higher throughout (user).
#
# SEMITONES ARE SIGNED. The E9 set happened to be all raises, and this is not: P3
# lowers both its strings, P5 drops string 10 a minor third. That is fine
# mechanically — the carriage travels either way, tension up or down — and the
# viewer only sums them, so a negative simply runs the carriage the other way.
#
# SPLITS COST NOTHING HERE. The chart marks two, and BOTH land on P4 (strings 3 and
# 4). On a mechanical steel a split is a compromise stop where two pull-rods fight
# over one string; with an independent motor per string the controller just commands
# the pitch, so no split hardware exists to model.
# RE-READ FROM THE RAW SHEET, cell by cell. The first pass at this table went
# through a SUMMARISED read of the spreadsheet and landed a column out of step,
# with sign errors on top. Round-tripping each move back to a note name did not
# catch it, because that only proved the table was self-consistent — it checked
# arithmetic against my own transcription, never against the source. Every move
# in copedent.json is derived from the exported CSV's own cells, and the chart's target
# note is quoted beside each one so the next reader can check it without me.
#
# The chart's C6 pedal columns are 4..8 — contiguous, which is the "3 higher"
# offset the user described (its 1..3 are the E9 top neck's).
# The table itself lives with the Pi's copy, bench/publicbench/copedent.json, which the motor
# controller's table is compiled from (bench/publicbench/copedent.py, docs/control-path.md): one
# copedent for the viewer and the instrument. Each control's "chart" field quotes the sheet.
_COPEDENT_JSON = json.loads((REPO / "bench" / "publicbench" / "copedent.json").read_text())
_COPEDENT = {c["name"]: {"key": c["key"], "moves": {int(n): st for n, st in c["moves"].items()}}
             for c in _COPEDENT_JSON["controls"] if c["moves"]}
OPEN_TUNING = tuple(_COPEDENT_JSON["open"])


def _idx(string_no: int) -> int:
    return string_no - 1                           # N = index + 1  <=>  index = N - 1


# WHAT COMES OFF WITH THE DECK (user, 2026-10-05): the viewer's "hide the deck" hides every
# GLB node whose name starts with one of these. The direct body's deck is src.deck_v2's:
# the panels, their white and the LED board (user 11-14), plus the UI station and the pickup.
DECK_PREFIXES = ["deck_", "ui_", "wire_ui", "fret_", "wire_fret_led", "pickup", "wire_pickup"]


def build_rig(build_n=None, out=RIG) -> pathlib.Path:
    if build_n is None:
        from tools.export_glb import _current_build_n
        build_n = _current_build_n()
    copedent = []
    for name, spec in _COPEDENT.items():
        entry = {
            "name": name, "key": spec["key"],
            # JSON key stays "raises" (the viewer's contract); values are SIGNED
            "raises": [{"i": _idx(n), "semitones": st} for n, st in spec["moves"].items()],
        }
        if name.startswith("P"):
            entry["pedal"] = int(name[1:]) - 1
        copedent.append(entry)
    rig = {
        "build": build_n,
        "n_strings": D.N_STRINGS,
        "deck_prefixes": DECK_PREFIXES,
        "open_tuning": list(OPEN_TUNING),
        "strings": [],                 # no per-string motion drawn yet (see the docstring)
        "pedals": [],
        "copedent": copedent,
    }
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rig, indent=1))
    print(f"wrote {out.name}  ({len(copedent)} controls, no motion yet, build #{build_n})")
    return out


def main() -> None:
    build_rig()


if __name__ == "__main__":
    main()