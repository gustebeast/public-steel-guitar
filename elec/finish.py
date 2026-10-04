"""The whole board run: layout -> route -> DRC -> repair -> silk -> verify -> geom export -> CAD check.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/finish.py [--rounds N] elec/out/optical

The code is cadkit's (`cadkit/pcbflow/finish.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import finish` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "finish")
