"""Close the nets a finished route left open, by maze search on the routed board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/close_last.py elec/out/output_panel

The code is cadkit's (`cadkit/pcbflow/close_last.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import close_last` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "close_last")
