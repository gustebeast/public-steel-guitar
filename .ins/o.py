import sys; sys.path.insert(0, ".")
import src.electronics as E
print(E.op_origin(), E.OP_BOARD_X, E.OP_BOARD_Y, [tuple(round(v,2) for v in E.op_pt(r)) for r in ("J10","J7","J9")])
import src.wiring as W
w=[c for n,c in W.components() if n=='wire_pwr_hot_12'] if hasattr(W,'components') else None
