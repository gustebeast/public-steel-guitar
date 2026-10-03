"""Autoroute a placed board (freerouting, headless) and import the result.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/route.py elec/out/lever_sensor

The code is cadkit's (`cadkit/pcbflow/route.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import route` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "route")
