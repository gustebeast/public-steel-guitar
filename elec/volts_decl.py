"""A16's declarations for one board, loaded from elec/volts/<board>.json.

    import volts_decl
    volts_decl.into(BOARD_NOTES, "motor_ctrl")      # just before the board.json is written

cadkit's A16 (PCB_QUALITY.md) asks every board for the worst-case voltage of every net
(`quality.net_volts`) and the rating of every pin (`quality.pin_volts`). Here they are
GENERATED, never typed: `py -3.12 elec/voltage_check.py --declare` works each net's level
out from the board's own netlist and each pin's rating from voltage_ratings.json (keyed by
the LCSC code in the fab BOM, each with the document it was read from), and writes the
file this loads. A net or a part added to a generator and not yet to that script is a net
or a pin with no declaration, and A16 fails on it by name -- which is the reminder to run
it again. A board with no file declares nothing, and A16 says that too.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def into(notes, board):
    path = os.path.join(HERE, "volts", board + ".json")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        decl = json.load(f)
    q = notes.setdefault("quality", {})
    for key in ("net_volts", "pin_volts"):
        # A generator may state a net or a part itself, and what it states wins. The file
        # is written per pin ("J1.7"), which A16 would read before a whole-part entry
        # ("J1"), so a part the generator declares takes its generated pins out with it.
        own = q.get(key, {})
        gen = {k: v for k, v in decl.get(key, {}).items()
               if k.split(".")[0] not in own}
        q[key] = dict(gen, **own)
    return True
