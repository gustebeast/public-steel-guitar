"""The ONE copper width model: how wide a track must be for a current (no pcbnew, so the
planner, the router, quality and the power gate all import it).

    required_width_mm(amps, layer, q)   the NEED: width (mm) on `layer` at quality.temp_rise_c
    drawn_width_mm(amps, layer, q)      the width to DRAW: the need + RASTER_MARGIN_MM, up to 0.05
    draw_mm(need_mm)                     the same rule for a need already in mm (the router's)
    foil_mm(layer, q)                    finished copper thickness (mm) of `layer` on the order
    via_barrel_mm(drill)                 the track width a via's plated barrel counts as
    via_drill_mm(amps, q)                the smallest drill (0.05 steps) whose barrel carries `amps`

quality.required_width_mm / foil_mm and place_intent.width_for are this; there is no second
copy of the IPC curve to drift (lead 2026-11-25: place_intent carried 2221's inner k after
quality had dropped it).
"""

# Finished foil thickness (mm) by ordered copper weight (oz), as the fab states it. JLCPCB's
# multilayer stackups (jlcpcb.com/impedance: JLC06161H-3313, -7628, ...) list 0.035 mm outer
# (1 oz) and 0.0152 mm inner -- the 0.5 oz default ("Finished copper weight of inner layer is
# 0.5oz by default", jlcpcb.com/capabilities/pcb-capabilities), thinner than 0.5 x 0.035.
# A weight not in the table is taken as oz x 0.035.
OUTER_FOIL_MM = {1.0: 0.035, 2.0: 0.070}
INNER_FOIL_MM = {0.5: 0.0152}
PLATING = 25.0 / 35.0     # a via barrel's derating: 25 um plating against 35 um outer foil (quality A1)
VIA_DRILL_STEP = 0.05     # drills are sized in these steps
K = 0.048            # IPC-2221's external-conductor k, used on EVERY layer (see required_width_mm)
RASTER_MARGIN_MM = 0.05   # drawn power copper is this much over its need (drawn_width_mm)


def foil_mm(layer, q):
    """Finished copper thickness (mm) of `layer` on this order: quality.copper_mm / inner_mm
    when given, else quality.copper_oz (outer, default 1) / inner_oz (inner, default 0.5)
    through the fab's table above."""
    q = q or {}
    outer = layer in ("F.Cu", "B.Cu")
    mm = q.get("copper_mm") if outer else q.get("inner_mm")
    if mm:
        return float(mm)
    oz = float(q.get("copper_oz", 1.0)) if outer else float(q.get("inner_oz", 0.5))
    return (OUTER_FOIL_MM if outer else INNER_FOIL_MM).get(oz, oz * 0.035)


def required_width_mm(amps, layer, q):
    """Track width (mm) for `amps` at the declared temperature rise (quality.temp_rise_c,
    default 10 C).

    I = k * dT^0.44 * A^0.725, A in square mils, k = 0.048 ON EVERY LAYER; the width is A over
    the layer's finished foil (foil_mm). An inner track differs from an outer one only by its
    thinner copper.

    ⚠ NO IPC-2221 INNER HALVING (lead ruling, 2026-11-25). 2221's inner k (0.024) is the chart
    IPC-2152 (2009) replaced: 2152's data has inner conductors in a board with planes at or
    below an external conductor's rise. Together with the 0.5 oz foil it made an inner track
    worth 0.192 of an outer one, and brain_board's VIN_BUS legs FAILed on the In2 pour; at the
    foil ratio alone (0.0152 / 0.035 = 0.434) they pass. Outer widths are unchanged.
    """
    dt = float((q or {}).get("temp_rise_c", 10.0))
    area_mil2 = (amps / (K * dt ** 0.44)) ** (1.0 / 0.725)
    return area_mil2 / (foil_mm(layer, q) / 0.0254) * 0.0254


def drawn_width_mm(amps, layer="F.Cu", q=None, min_mm=0.0):
    """The width to DRAW power copper at: required_width_mm + RASTER_MARGIN_MM, rounded up to
    0.05 mm, never under min_mm. Every drawn power width goes through here -- declared bands,
    auto_pour tracks, net_widths (place_intent.width_for) and close_last's power ladder -- and
    the judges (quality A1, rasterpath / widepath, close_last's pour guard) keep the bare need.

    ⚠ COPPER DRAWN AT EXACTLY ITS NEED MEASURES UNDER IT (brain_board fixq3f, 2026-11-25; lead
    ruling). The gate rasterises the ordered gerbers at 0.025 mm and reads a track ~0.02-0.05
    under its nominal width, so a track at the need is a WARN, and a long one a FAIL: +24V_LED
    0.89 / 0.90, SW 1.30 / 1.34, SVC_VBUS 0.34 / 0.34, VIN_CM5's 0.70 trunk a 3.55 mm "neck".
    The copper gets one raster step over; the judge stays strict."""
    return draw_mm(required_width_mm(amps, layer, q), min_mm)


def draw_mm(need_mm, min_mm=0.0):
    """The width to DRAW copper whose bare need is need_mm: need + RASTER_MARGIN_MM, rounded
    up to 0.05 mm, never under min_mm (drawn_width_mm's rule, for a need already worked out --
    the router's power_width adds the drop budget to IPC's heating width)."""
    import math
    w = float(need_mm) + RASTER_MARGIN_MM
    return round(max(min_mm, math.ceil(w / 0.05 - 1e-9) * 0.05), 2)


def via_barrel_mm(drill_mm):
    """The track width (mm) a via's plated barrel counts as: pi x drill x PLATING (quality A1).
    The power gate (widepath / rasterpath), power_vias and the router all read it here."""
    import math
    return math.pi * float(drill_mm) * PLATING


def via_drill_mm(amps, q, step=VIA_DRILL_STEP, max_mm=None):
    """The smallest drill, in `step`s, whose barrel (via_barrel_mm) is at least the NEED for
    `amps` (required_width_mm on an outer layer, as the gate grades a via), capped at max_mm.

    ⚠ THE ROUTER AND THE GATE TAKE A VIA'S NEED FROM HERE (lead ruling, 2026-11-26). The
    router's own copy of the IPC curve (1 oz = 1.378 mil) put +24V's 3 A at 20 C at 0.89757 mm,
    6 um under the gate's 0.89760; a 0.40 drill's barrel is 0.89760 -- enough by the router's
    sum, short by the gate's -- so it drew 0.40 vias and the gate FAILed the path. One need,
    and a barrel checked against it after the rounding, so the two can't disagree."""
    import math
    need = required_width_mm(amps, "F.Cu", q)
    n = max(1, int(math.ceil(need / via_barrel_mm(step) - 1e-9)))
    while via_barrel_mm(n * step) < need:     # floating point at a step boundary
        n += 1
    d = round(n * step, 3)
    return min(d, max_mm) if max_mm is not None else d
