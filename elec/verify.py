"""Length-matched groups: inside budget, on one layer set?

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/verify.py elec/out/optical

The code is cadkit's (`cadkit/pcbflow/verify.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import verify` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "verify")
