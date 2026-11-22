"""test_path_clear_frozen.py PCBFLOW_DIR rPS_e2/output_board.unrouted.kicad_pcb : layout._path_clear refuses e2's +24V stub across VIN_SW's band, allows a clear run."""
import sys, os, pcbnew
sys.path.insert(0, sys.argv[1]); import layout
b = pcbnew.LoadBoard(sys.argv[2]); L = b.GetLayerID("F.Cu"); w = pcbnew.FromMM(0.9)
v = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
cross = layout._path_clear(b, v(136.38, 131.15), v(132.35, 120.06), "+24V", L, w)
print("PASS" if not cross else "FAIL", "e2 +24V stub across VIN_SW band ->", "refused" if not cross else "allowed")
sys.stdout.flush(); os._exit(0 if not cross else 1)
