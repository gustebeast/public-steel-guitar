"""Emit docs/rig.json -- the animation manifest the web viewer plays.

THE DIRECT DRIVE MOVES (user, 2026-11-23: "update the pedal and knee buttons to move the
drivetrains and string balls"). Each string's entry (`_screw_string`) tells the viewer how its
drive follows a pedal or lever: the nut and everything that rides it slide along the screw, the
screw and what turns with it turn at the screw's lead, and the spring stretches between its plug
and the collar. Parts are named by pattern, so pieces the build numbers (m3_0_3...) come along.
The levers and pedals themselves do not swing yet (no stations drawn).

HISTORY (lead, 2026-11-17): the direct instrument had no animation at first. The rig this file used to
write was the v1 belt drive's: each string's carriage riding its vertical leadscrew, the
screw and motor pulleys turning, the belt clamps sliding along their runs, and the levers
and pedals swinging at v1's stations. None of those parts are in the direct instrument, so
that rig animated nothing and its code reached into v1 geometry on every build. It is in
the git tag v1-instrument.

What the viewer still uses is written: the copedent (its control panel and key map), the
open tuning, the deck's name prefixes (the "hide the deck" toggle) and the build number.
The per-string motion was an empty list, which the viewer treats as "nothing to move", until
the direct drive's entries above (cadkit's viewer reads them: rig.strings[i].slide).

  py -3.12 -m tools.export_rig
"""
from __future__ import annotations

import json
import math
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


# WHAT TURNS WITH THE SCREW: the coupler and its screws, the screw's bearing collars and theirs,
# and the motor's shaft (src.direct_bench's string parts and motor pieces)
_TURNING = ("screw", "coupler", "cpl_m3", "cpl_insert", "collar_a", "ca_m3", "ca_ins",
            "collar_b", "cb_m3", "cb_ins", "motor_shaft")


def _names(prefixes, i: int) -> str:
    """A pattern for string i's parts with these names, pieces too (yoke_3, m3_0_3)."""
    return r"^(%s)(_\d+)?_%d$" %("|".join(sorted(prefixes)), i)


def _screw_string(i: int) -> dict:
    """String i's direct drive, for the viewer. Stretch beyond slack = t * T_TRAVEL (src.direct_bench
    x_yt: the nut moves -X as t grows); the model is drawn at T_OPEN. A right-hand screw held
    axially, turned +a about +X, drives its nut -X: a = -2 pi dx / lead (the reverse for LH)."""
    from src import direct_bench as DB
    assert DB.THETA == 0.0, "the drive is drawn yawed: its axis is no longer +X"
    x0, x1 = DB.spring_span(DB.T_OPEN, i)
    hand = 1.0 if D.SCREW_HAND == "RH" else -1.0
    return {
        "i": i,
        "axis": [1.0, 0.0, 0.0], "center": [0.0, DB.y_of(i), DB.za(i)],
        "open_dl": D.DL_OPEN, "drawn_dl": DB.T_OPEN * DB.T_TRAVEL, "dl_max": DB.T_TRAVEL,
        "slide_dir": [-1.0, 0.0, 0.0],                    # the nut, per mm of stretch
        "slide": _names(DB._RIGID, i),
        "turn": _names(_TURNING, i),
        # per mm of stretch the nut goes -X 1 mm: the screw turns +2 pi / lead (RH)
        "turn_rad_per_mm": hand * 2 * math.pi / D.SCREW_PITCH,
        "stretch": {"re": _names(("spring",), i), "from": [x0, DB.y_of(i), DB.za(i)], "len": x1 - x0},
    }


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
        "strings": [_screw_string(i) for i in range(D.N_STRINGS)],
        "pedals": [],
        "copedent": copedent,
    }
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rig, indent=1))
    print(f"wrote {out.name}  ({len(copedent)} controls, {len(rig['strings'])} drives, build #{build_n})")
    return out


def main() -> None:
    build_rig()


if __name__ == "__main__":
    main()