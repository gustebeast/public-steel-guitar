"""Checks a netlist must pass that nothing else in the pipeline can see.

    import netcheck        # from a board generator

The code is cadkit's (`cadkit/pcbflow/netcheck.py`, shared with every project -- read it
there). This file keeps the project's old entry point and `import netcheck` working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.pcbflow._shim import forward  # noqa: E402

forward(__name__, "netcheck")
