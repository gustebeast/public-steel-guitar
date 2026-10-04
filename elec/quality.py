"""The standard PCB validation pass (cadkit/PCB_QUALITY.md): is this board fit to order?

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/quality.py elec/out/optical

The code is cadkit's (`cadkit/pcbflow/quality.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import quality` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "quality")
