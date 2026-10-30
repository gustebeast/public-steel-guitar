"""Does each board's CAD actually render the board that was ROUTED?

    py -3.12 elec/cad_geom_check.py            # every board
    py -3.12 elec/cad_geom_check.py optical    # one

⚠ WHAT THIS REPLACED, AND WHY IT HAD TO. The previous version compared the CAD's
hand-copied connector anchors with elec/<board>.py's placements -- the numbers layout is
GIVEN. A copy checked against its own source can only agree, and it did while:
  * the output board's two panel connectors' bodies stopped 0.54 mm short of the edge
    (their COURTYARDS had been placed flush; a courtyard is the keep-out, not the part),
  * the 24 V barrel inlet faced along the board at the chassis rail (0 degrees, where
    that footprint's mouth is its local +Y) and the CAD drew it as a panel inlet,
  * and the USB-C hole was cut 7.85 mm above the receptacle.
The user's words for the gap: "your validation passes didn't cover accurately rendering
each board in CAD". Right -- DRC checks copper against the netlist, the overlap gate checks
solids against solids, and nothing ever compared the CAD's board with the real one.

WHAT THIS DOES. elec/geom/<board>.geom.json is the ROUTED board read back (export_geom.py,
run by finish.py). The comparison itself is cadkit's (`cadkit/board_check.py`): every
routed part's body must land on CAD material, the board must not be mirrored, and the
plate's cutouts must match the routed board's. It finds each board's pose for itself, so
the only thing this file has to know is WHICH solid the assembly draws for each board --
_cad() below -- plus the one check that is ours alone (the UI deck's placement rule).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from cadkit import board_check as _CHK                # noqa: E402

from src import board_geom as BG                      # noqa: E402


def _cad(board):
    """(solid, ink): the board's CAD solid, whole -- plate plus every part -- and the
    LETTERING the assembly places for it, both in the same frame. The ink comes from the
    function the build itself calls, so a board whose lettering never reaches the
    assembly has nothing to hand over here and fails."""
    if board == "output_panel":
        from src import electronics as EL
        # J8 is drawn as its own part (screw_terminal, output_panel_term), not in the board
        # solid. R1 passed without it only because J8's probe landed on a neighbour's body.
        sol = EL.output_panel()
        for v in EL.output_panel_term().values():
            sol = sol.union(v)
        return sol, EL.output_panel_silk()
    if board == "motor_ctrl":
        from src import electronics as EL
        return EL.motor_ctrl(), EL.motor_ctrl_silk()
    if board == "ui_board":
        from src import ui_panel as UIP
        return UIP.ui_pcb(), UIP.ui_silk()
    if board == "can_tee":
        from src import electronics as EL
        return EL.tee_pcb(0.0, 0.0), EL.tee_silk(0.0, 0.0)
    if board in ("foot_led_a", "foot_led_b"):
        from src import foot_light as FOOT
        return FOOT.pcb(board[-1]), FOOT.silk(board[-1])
    if board == "pi_cap":
        from src import electronics as EL
        return EL.pi_cap(), EL.pi_cap_silk()
    if board == "optical":
        from src import optical_pickup as OP
        return OP.opt_pcb(), OP.opt_silk()
    if board == "lever_sensor":
        from src import knee_lever as KL
        return KL.sensor_pcba(), KL.sensor_silk()
    if board in ("fret_led_mid", "fret_led_key"):
        # the two fret boards: the laminate with every routed body, and the LEDs, which
        # src/fret_light.py draws as their own part so they read as lit
        from src import fret_light as FL
        panel = board.rsplit("_", 1)[1]
        return FL.pcb(panel), FL.silk(panel)
    if board.startswith("leg_pogo_"):
        # the leg's blind-mate boards: src/leg_pogo.py draws each as board + contacts +
        # connector at its joint. They stand on the tenon's DIAGONAL, and this check looks
        # for axis-aligned plates, so the joint is turned 45 deg about the leg's axis first
        # (t onto +X). That changes nothing the check measures -- parts against their board.
        from src import leg_pogo as P
        _, kind, joint = board.rsplit("_", 2)
        j = P.BOTTOM if joint == "bottom" else P.TOP
        parts = P.male(j) if kind == "male" else P.female(j)
        s = parts[0][1]
        for _n, part in parts[1:]:
            s = s.union(part)
        ink = dict(P.ink(j))["pogo_%s_silk_%s" % (kind, j.name)]
        turn = lambda w: w.rotate((j.x, j.y, 0.0), (j.x, j.y, 1.0), -j.ang)
        return turn(s), turn(ink)
    raise KeyError(board)


BOARDS = ("output_panel", "motor_ctrl", "optical", "lever_sensor", "can_tee",
          "pi_cap", "ui_board", "fret_led_mid", "fret_led_key", "foot_led_a", "foot_led_b",
          "leg_pogo_male_bottom", "leg_pogo_male_top",
          "leg_pogo_female_bottom", "leg_pogo_female_top")


def _ui_rule_check():
    """Does the UI board's routed switch land where the deck's placement rule says?

    src/ui_panel.py owns the rule -- the inputs either side of the display on its Y
    (2026-10-30) -- and
    elec/ui_board.py places SW1 from it. Nothing downstream compares the
    two: the CAD draws the ROUTED switch, so if the placement drifted the deck's hole
    would drift with it, silently and consistently. This is the one check that reads
    both. It lives here rather than in ui_panel because ui_panel is on the generator's
    own import path, and an assertion there deadlocks the pipeline it is checking."""
    from src import ui_panel as UIP
    kx, ky = UIP.routed("SW1")
    wx, wy = UIP.knob_x(), UIP.input_y()
    off = max(abs(kx - wx), abs(ky - wy))
    if off > 0.05:
        print("   ui_board: the routed switch is at (%.3f, %.3f) and the placement rule "
              "wants (%.3f, %.3f) -- %.3f off" % (kx, ky, wx, wy, off))
        return 1
    # ...and the power button's (ui_panel.power_x)
    px, py = UIP.routed("SW2")
    p_off = max(abs(px - UIP.power_x()), abs(py - wy))
    if p_off > 0.05:
        print("   ui_board: the routed power switch is at (%.3f, %.3f) and its rule "
              "wants (%.3f, %.3f) -- %.3f off" % (px, py, UIP.power_x(), wy, p_off))
        return 1
    bad = 0
    for complaint in UIP.check_posts():
        print("   ui_board: %s" % complaint)
        bad += 1
    if bad:
        return bad
    print("   ui_board: the routed switch is on the placement rule (%.3f off), and the "
          "cradle's four posts stand on bare board" % off)
    return 0


# Bodies drawn to their real shape that do not reach the board face at one end of their
# fab rectangle. Everything else must: the end probes COUNT on every board (strict_ends),
# so a part drawn turned, short or shifted fails here rather than being remarked on.
ENDS_OK = {
    "output_panel": {
        "J5": "the 6.35 mm jack's nose is its round bushing, on the jack's axis and clear "
              "of the board face; the fab rectangle is the plan view of it",
    },
}


def _rev_silk(board):
    """Disagreements between a board's printed revision and its REV switch (0 or 1). A
    board with a switch must print that rev: optical R2 went out in the model reading
    'OPTICAL r1' because the labeller's default was never told otherwise."""
    rev = BG.REV.get(board)
    if rev is None:
        return 0
    found = [t["text"] for t in BG.load(board)["silk"]
             if t["text"].split()[-1:] and t["text"].split()[-1] in ("r1", "r2", "r3")]
    if [t.split()[-1] for t in found] == ["r%d" % rev]:
        return 0
    print("%-13s REV %d but the board prints %r" % (board, rev, found))
    return 1


# Optical R1, on the bench, goes on R2's mounts and lines up with the same strings (user,
# 2026-10-30). R1's geom sits 10.995 further +Y, its centre being further +Y on the shorter board.
# The M4 pilot's growth moved R2's two mounts 0.05 in each axis: R1's O4.4 still takes the M4.
_R1_FIT_DY = -10.995
_R1_FIT_HOLE = 0.05


def _r1_fit(board):
    """Optical R2's holes and detectors against R1's, the one thing R1 still has to match."""
    if board != "optical":
        return 0
    r1 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rev1",
                                     "optical.geom.json"), encoding="utf-8"))
    r2 = BG.load(board)

    def mid(poly):
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        return (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0

    pairs = [("hole %d" % k, mid(a), mid(b), _R1_FIT_HOLE + 0.0015)
             for k, (a, b) in enumerate(zip(r2["holes"], r1["holes"]))]
    if len(r2["holes"]) != len(r1["holes"]):
        pairs.append(("hole count", (0, 0), (1e3, 0), 0.0))
    fp1 = {f["ref"]: f for f in r1["footprints"]}
    for f in r2["footprints"]:
        if f["ref"].startswith("PD"):
            f1 = fp1[f["ref"]]
            pairs.append((f["ref"], (f["x"], f["y"]), (f1["x"], f1["y"]), 0.0015))
    bad = 0
    for name, a, b, tol in pairs:
        if abs(a[0] - b[0]) > tol or abs(a[1] - b[1] - _R1_FIT_DY) > tol:
            print("   optical: R1 does not fit R2's %s: R2 %s, R1 %s" % (name, a, b))
            bad += 1
    return bad


def check(board, verbose=True):
    solid, ink = _cad(board)
    return _rev_silk(board) + _r1_fit(board) + _CHK.check(board, solid, BG.load(board), verbose=verbose,
                                         strict_ends=True, ends_ok=ENDS_OK.get(board), ink=ink)


def main(argv):
    bad = 0
    for b in (argv or BOARDS):
        try:
            bad += check(b)
        except Exception as exc:                  # a board the check cannot read is a
            print("%-13s COULD NOT CHECK: %s" % (b, exc))   # finding, not a pass
            bad += 1
        if b == "ui_board":
            try:
                bad += _ui_rule_check()
            except Exception as exc:
                print("   ui_board: COULD NOT CHECK THE SPACING RULE: %s" % exc)
                bad += 1
    print("\n%s" % ("every routed part is where the CAD draws it" if not bad
                    else "*** %d DISAGREEMENT(S) BETWEEN THE CAD AND THE ROUTED BOARDS ***"
                    % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
