"""DRC violations this project's boards accept ON PURPOSE, by shape.

`cadkit/pcbflow/finish.py` looks for this file beside the board generators and asks
`declared(board, vtype, refs)` about every violation; anything it does not accept stays a
violation. A count is not a check -- see cadkit.pcbflow.netcheck.classify_violations.
"""
import re


def optical_declared(vtype, refs):
    """The optical board's sensing cell: an IR emitter between its own two detectors.

    Declared because it cannot be loosened -- PD_DY is an optical parameter before it is
    a placement one, and widening it would let the cover shade the detectors it exists to
    protect. Only this shape, and only between a D and its OWN PDs.

    ⚠ RE-MEASURED 2026-09-29, AND THE BODIES DO NOT CLEAR. This docstring said "courtyards
    overlap 0.390, BODIES clear by 0.350 and copper by 0.200". Measured on the finished
    board, identically in all 20 pairs (every D against each of its own two PDs):

        bodies      -0.035 mm   THEY ABUT -- the fab outlines overlap by 35 um
        courtyards  -0.320 mm   overlap, which is what DRC reports
        copper      +0.475 mm   clear, against the 0.127 rule

    Copper -- the number that decides whether the board can be built -- is better than
    was claimed, by more than double. The body figure was wrong in the direction that
    matters: it asserted a 0.350 clearance that does not exist, and THIS DECLARATION IS
    THE ONLY THING STOPPING DRC FROM SAYING SO, which is exactly why it has to be right.

    The 35 um is accepted rather than fixed, and deliberately: PD_DY cannot widen (see
    above), the pads clear by 0.475 so the parts self-align to copper rather than to each
    other, and 35 um is inside the placement tolerance of any machine that will build
    this -- the bodies will sometimes touch and nothing is harmed when they do. It is an
    assembly note, not a defect. What would be a defect is a reader trusting 0.350.
    """
    import re as _re
    if vtype != "courtyards_overlap" or len(refs) != 2:
        return False
    # ⚠ TP8 AGAINST R30 IS DECLARED, AND A COURTYARD IS THE ONLY THING IT OVERLAPS.
    # TP8 is a bare bring-up pad on BOOT0: no paste, no part, nothing ever sits on it, so
    # the courtyard it carries reserves room for a body that does not exist. R30 is the
    # BOOT0 pull-down, which is WHY they are adjacent -- that resistor is at the pin, and
    # the pin's net has no copper anywhere else. Copper clears by 0.492 mm over the 0.127
    # rule (searched, and DRC reported no clearance violation), and R30's body is a 0402
    # 0.5 mm away from a 1.5 mm target, which a hand probe does not care about.
    # Named as a pair rather than waved through by footprint type on purpose: a genuine
    # courtyard overlap involving a test pad should still fail.
    if set(refs) == {"TP8", "R30"}:
        return True
    m = [_re.fullmatch(r"(D|PD)(\d+)([AB]?)", r) for r in refs]
    if not all(m):
        return False
    kinds = {x.group(1) for x in m}
    return kinds == {"D", "PD"} and m[0].group(2) == m[1].group(2)


def foot_a_declared(vtype, refs):
    """Foot board A: its cable socket against the first LED of the row.

    The side-entry XH's courtyard is 16.7 x 12.0 because it takes in the plug's approach
    and both mounting lands; the parts themselves clear. elec/foot_led.py asserts the two
    gaps that matter before it writes the netlist -- the socket's body ends at least
    0.30 short of the LED's courtyard along the board, and its four signal lands at least
    0.30 from it across -- so this accepts a courtyard and nothing else. Only this pair."""
    return vtype == "courtyards_overlap" and set(refs) == {"J1", "D1"}


def declared(board, vtype, refs):
    if board.endswith("foot_led_a"):
        return foot_a_declared(vtype, refs)
    return "optical" in board and optical_declared(vtype, refs)
