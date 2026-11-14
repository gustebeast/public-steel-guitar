"""Quality declarations a new board shares with the instrument's earlier ones.

    import quality_share as QS
    QS.cited(["PCM1808PWR", ...])      # -> {value: "as output_panel.py: <its citation>"}

A pinout citation (cadkit A4) is read once, against the maker's drawing, on the board that
first used the part. A later board that uses the SAME part (same value, same footprint)
cites that reading instead of copying its text, so the two never drift: the earlier board's
own BOARD_NOTES are imported and quoted. Importing those generator modules builds no parts
(checked on the brain board: 0 parts before and after). A value no earlier board cites is
left out -- an A4 FAIL is the honest state until someone reads it.
"""
from __future__ import annotations

import importlib

SOURCES = ("output_panel", "optical", "motor_ctrl", "pi_cap", "lever_sensor", "brain", "ui_board")


def cited(values, sources=SOURCES):
    out = {}
    for mod in sources:
        pv = importlib.import_module(mod).BOARD_NOTES.get("quality", {}).get("pinouts", {})
        for v in values:
            if v in pv and v not in out:
                out[v] = "as %s.py: %s" % (mod, pv[v])
    return out


USB_HS = ("USB 2.0, a 90 ohm pair: it stays a PAIR on one layer (differential impedance is "
          "the two conductors' geometry) and collects no more than two vias. Skew at 480 Mbps "
          "has room (2,080 ps a bit); the budget is output_panel's for its hub pairs.")


def usb_match(pairs):
    """`match` groups for USB 2.0 pairs: [(name, dp, dm, why), ...]."""
    return [{"name": n, "max_skew_mm": 8.3, "same_layer": True, "max_vias": 2,
             "nets": [dp, dm], "why": w + " " + USB_HS} for n, dp, dm, w in pairs]
