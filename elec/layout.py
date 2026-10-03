"""Netlist + placement -> a .kicad_pcb with every part already where it belongs.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/layout.py elec/out/can_tee

The code is cadkit's (`cadkit/pcbflow/layout.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import layout` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "layout")
