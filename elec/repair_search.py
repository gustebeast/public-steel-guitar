"""Find a legal path to close one stubborn net, on a ROUTED board.

    py -3.12 elec/repair_search.py elec/out/optical +3V3A U2 4

The code is cadkit's (`cadkit/pcbflow/repair_search.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import repair_search` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "repair_search")
