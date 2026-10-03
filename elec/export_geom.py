"""Read a ROUTED board back and write the geometry the CAD needs: elec/geom/<board>.geom.json.

    "C:/Program Files/KiCad/10.0/bin/python.exe" elec/export_geom.py elec/out/output_panel

The exporter itself is cadkit's (`cadkit/kicad_geom.py` -- the file format and the reason
it exists are documented there). This is the project's entry point for it, kept under
its old name because finish.py runs it at the end of every board run: the geom file is
TRACKED, unlike elec/out, and is rewritten whenever the board is.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cadkit.kicad_geom import export  # noqa: E402

GEOM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geom")

if __name__ == "__main__":
    for a in sys.argv[1:]:
        export(os.path.abspath(a), GEOM_DIR)
