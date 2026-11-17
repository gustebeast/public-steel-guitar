"""The viewer's per-wire note: each lead's cut length, read from src/wire_cuts.json.

The table was generated from src/wiring.py's v1 harness (the old main() here, which drew it
through src.build's v1 bus components). That generator went with the v1 build (lead,
2026-11-17; git tag v1-instrument). The direct instrument's harness will regenerate this
file when it is drawn; until then the notes only name parts that are no longer built.
"""
from __future__ import annotations

import json


def notes():
    """{part name: the line the viewer shows while it is selected}, from src/wire_cuts.json."""
    import pathlib
    path = pathlib.Path(__file__).resolve().parent.parent / "src" / "wire_cuts.json"
    return {n: "cut %d mm" % mm for n, mm in json.loads(path.read_text(encoding="utf-8")).items()}