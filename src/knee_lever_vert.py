"""VERTICAL knee lever (LKV) — the up-push variant of the control core. PCTG.

Same job as knee_lever.py (a pure POSITION SENSOR: magnet on the axle, MT6701
reading it, springs for feel) and the same bought parts, but the player's knee
pushes UP instead of sideways.

WHAT ACTUALLY CHANGES, and it is less than it looks:

  * THE ARM MOVES, NOT THE AXLE. In this part's LOCAL frame the axle still runs
    along +Y and the throw is still a rotation about it. The arm, instead of
    hanging -Z and swinging laterally, extends +X HORIZONTALLY and swings up in
    Z. What makes the whole thing a "vertical" lever is the MOUNT: the assembly
    is posed rotated 90° about Z, so local +Y lands on the guitar's X and local
    +X points -Y at the player. That is the sense in which the axis runs along
    the instrument's length.

  * THE FEEL BLOCK MOVES UP, IT DOES NOT MIRROR. For a +X-pushing piston to
    resist an UPWARD push on a +X arm, the contact has to sit ABOVE the axle:
    force +X at height h gives +Y torque, which drives the arm back down. So the
    lobe and both cartridges translate from -LOBE_RC to +LOBE_RC_V. NOT a Z
    mirror — the cartridge pocket's 45° gable has to stay on TOP whatever the
    lever does, because that is a printability constraint, not a lever one.
    Mirroring would put a flat ceiling over both pockets.

  * THE AXLE SITS LOWER. That is forced, not chosen: the cartridges have to stay
    under the instrument, so putting them above the axle pushes the axle down by
    exactly as much. It is also what buys the arm its room to swing up.

  * THROW IS SHORTER (20° vs 30°, user: the vertical is the space-constrained
    one) — but the FEEL IS UNCHANGED, because the spring stroke is
    LOBE_RC·sin(throw) and LOBE_RC is free. Raising it 9.0 -> 13.2 puts the
    stroke back at 4.51 against the horizontal lever's 4.50, so the springs,
    preload, back-stops, drag pads and half-stop all transfer with no re-tuning
    and no new part. The web behind the lobe recess scales with LOBE_RC too, so
    this is the SAFE direction for it (~6.8 of web where 9.0 gave 2.6).

  * TENONS RUN ALONG LOCAL X. cadkit's octagon slides along its extrude axis, so
    where the horizontal lever rotates it 90° to slide in Y, this one uses it
    as-is. After the mount's 90° pose that lands the slide on the guitar's Y,
    which is what the rib mortises accept. The stations then space out along
    local Y (= the guitar's X, the 23 mm rib comb), and only ~2 fit across the
    housing's 27.8 — so this lever mounts on FEWER but LONGER tenons than LKL's
    four short rails.

Everything else is imported from knee_lever and used unchanged: the cartridges,
their pistons, guide posts, back-stop screws and drag pads; the axle, magnet,
magnet cap, bearings and the MT6701 board.

DEFERRED (this round is the basic geometry, per the user):
  * the REST STOP. Gravity and the springs both pull this arm down, so unlike
    LKL there is no spring-defined rest angle — it needs a hard stop to land on.
  * the sensor CRADLE. knee_lever's is welded to that housing's own Z extents;
    it wants parameterising rather than copying, and this housing's Z span is
    30.4 against 22.2, so the board has room to spare either way.
  * the global MOUNT POSE (which bay, and how far inboard).
  * the follower RECESSES are plain rectangles here, not knee_lever's swept
    tongue envelopes — the arm keeps more material with the swept version, so it
    is worth porting once the throw is settled.
"""

from __future__ import annotations

import math

import cadquery as cq

from . import knee_lever as KL
from .helpers import box_at, cyl_y, heal

from cadkit.supports import printable_bore, contact_rib

# ── throw + the lobe that keeps the feel identical ───────────────────────────
THROW_V     = 20.0                  # user: the vertical may have less than the horizontal
ENGAGE_V    = THROW_V / 2.0         # half-stop still engages at half throw (10°)
LOBE_RC_V   = 13.2                  # chosen so LOBE_RC_V·sin(THROW_V) == the horizontal
                                    # lever's 4.50 stroke -> the feel system transfers
_STROKE     = LOBE_RC_V * math.sin(math.radians(THROW_V))
_FEEL_DZ_V  = LOBE_RC_V + KL.LOBE_RC        # +22.2: how far the whole feel block rises

# ── the lever ────────────────────────────────────────────────────────────────
ARM_LEN_V   = 50.0                  # axle -> paddle end. 50 gives 17.1 of paddle lift at
                                    # 20°, about an inch, which is a normal knee rise.
ARM_TZ      = 8.0                   # arm thickness in Z (it is the arm's bending depth now)
LEG_TOP     = LOBE_RC_V + 3.0       # leg reaches past the lobe station
HUB_D       = KL.HUB_D              # Ø10 hub on the axle — unchanged
LEVER_HW    = KL.LEVER_HW           # ±10 in Y — unchanged, so every bearing/sensor Y holds
REC_X       = 3.5                   # follower recess depth into the leg's -X face
REC_Z       = 7.0                   # recess height (the follower's swept band)


def _lever() -> cq.Workplane:
    """The L. Hub on the axle, a LEG rising +Z to carry the return lobe, and the
    ARM running +X to the knee. The lobe is a full-width ridge at LOBE_RC_V, on
    the leg's -X face, reached through one local recess per follower — same
    scheme as the horizontal lever (the ridge is a single primitive buried in
    solid material except where the pistons need to touch it)."""
    hub = cyl_y(HUB_D, 2 * LEVER_HW, y0=-LEVER_HW)
    leg = box_at(KL.ARM_TX, 2 * LEVER_HW, LEG_TOP, x=0.0, y=0.0, z=LEG_TOP / 2)
    arm = box_at(ARM_LEN_V, 2 * LEVER_HW, ARM_TZ, x=ARM_LEN_V / 2, y=0.0, z=0.0)
    body = hub.union(leg).union(arm)
    # follower recesses, one per cartridge lane, cut into the leg's -X face so the
    # lobe can protrude into them
    for yc in (KL.MAIN_YC, KL.HS_YC):
        body = body.cut(box_at(REC_X, KL.HS_CART_WY + 2 * KL.HS_CLR, REC_Z,
                               x=-KL.ARM_TX / 2 + REC_X / 2, y=yc, z=LOBE_RC_V))
    body = body.union(cyl_y(2 * KL.LOBE_R, 2 * LEVER_HW, y0=-LEVER_HW)
                      .translate((0.0, 0.0, LOBE_RC_V)))
    # axle D-bore — identical to the horizontal lever's (same axle, same flat, and
    # cadkit hands a lying part a plain cylinder rather than a teardrop)
    _bore = printable_bore(KL.AXLE_BORE_D, 2 * LEVER_HW, (0.0, -LEVER_HW, 0.0),
                           (0.0, 1.0, 0.0), (0.0, 1.0, 0.0), overshoot=1.0)
    _zhi, _zlo = KL.AXLE_FLAT_R + 0.1, -(KL.AXLE_BORE_D / 2 + 1.0)
    body = body.cut(_bore.intersect(box_at(
        KL.AXLE_BORE_D + 2.0, 2 * LEVER_HW + 4.0, _zhi - _zlo,
        x=0.0, y=0.0, z=(_zhi + _zlo) / 2)))
    return heal(body)


# ── housing envelope, derived the same way LKL's is ──────────────────────────
def vplace(s):
    """knee_lever's feel-block placement, lifted so the contact lands at
    +LOBE_RC_V. A pure translation — see the module docstring on why this must
    not be a mirror."""
    return KL.feel_place(s).translate((0.0, 0.0, _FEEL_DZ_V))


HOUS_X0 = KL.HOUS_X0                # cartridge back + back-stop engagement — unchanged
HOUS_X1 = HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL       # +7.8: the arm exits through here
HOUS_HW = KL.HOUS_HW                # ±13.9 — the whole Y stack is unchanged
# +Z comes from the RAISED POCKET's own measured extent, not from the piston: the
# cartridge block stands 6.6 above its centre where the piston stands 3.0, and using
# the piston's figure put the housing lid 3.6 BELOW the cartridge it is meant to
# enclose. Overlap probes cannot see that — a part poking out into free air
# intersects nothing — it took a bounding-box check.
HOUS_Z1 = (vplace(KL._hs_pocket(KL.HS_YC, -20.0, KL.HS_BACK_X)).val()
           .BoundingBox().zmax + KL.HS_HOUS_WALL)
HOUS_Z0 = -(HUB_D / 2 + KL.HS_CLR + KL.HS_HOUS_WALL)    # under the hub / the arm at rest
AXLE_DROP = HOUS_Z1 - KL.HOUS_Z1    # how much lower the axle sits than LKL's (+11.0..15.2)

# ── mount tenons: slide along LOCAL X (see the docstring) ────────────────────
TEN_X0, TEN_X1 = HOUS_X0 + 2.0, HOUS_X1     # the slide span available
TEN_PITCH = KL.RIB_PITCH / 2.0              # the chassis rib comb, now along local Y
TEN_Y = tuple(k * TEN_PITCH for k in (-1, 0, 1)
              if abs(k * TEN_PITCH) <= HOUS_HW - KL._JHW)


def _top_tenon(ty):
    """One fused octagon tenon at local y=ty. cadkit's octagon already slides
    along +X with its roof +Z, which is exactly what this lever wants — no
    rotation, unlike LKL's."""
    return (KL._lever_joint(TEN_X1 - TEN_X0).tenon(root=KL.TEN_ROOT)
            .translate((TEN_X0, ty, HOUS_Z1)))


def _lever_envelope() -> cq.Workplane:
    """The lever grown by HS_CLR on every face — the thing that gets swept to make
    the lever room. Built from the same primitives as _lever rather than offset
    from it, so a change to one is visibly a change to the other."""
    c = KL.HS_CLR
    hub = cyl_y(HUB_D + 2 * c, 2 * (LEVER_HW + c), y0=-(LEVER_HW + c))
    leg = box_at(KL.ARM_TX + 2 * c, 2 * (LEVER_HW + c), LEG_TOP + c,
                 x=0.0, y=0.0, z=(LEG_TOP + c) / 2)
    arm = box_at(ARM_LEN_V + 2.0, 2 * (LEVER_HW + c), ARM_TZ + 2 * c,
                 x=(ARM_LEN_V + 2.0) / 2, y=0.0, z=0.0)
    return heal(hub.union(leg).union(arm))


def _housing() -> cq.Workplane:
    """The prism, derived from the lever + the raised cartridges exactly as LKL's
    is, minus the lever room, the two house pockets and the drag recesses, plus
    the bearing seats, the sensor-side contact rib and the mount tenons."""
    w = box_at(HOUS_X1 - HOUS_X0, 2 * HOUS_HW, HOUS_Z1 - HOUS_Z0,
               x=(HOUS_X0 + HOUS_X1) / 2, y=0.0, z=(HOUS_Z0 + HOUS_Z1) / 2)
    for ty in TEN_Y:
        w = w.union(_top_tenon(ty))
    # LEVER ROOM = the lever's OWN SWEPT ENVELOPE, as a union of clearance copies
    # through the throw. The first attempt was one planar polygon from the hub to
    # the arm tip, and it was wrong in a way worth recording: its lower edge ran
    # from the hub straight out to the tip's FULL-THROW position, so it sloped up
    # above the arm's own rest underside and the lever fouled from 3° on. Sweeping
    # the real shape cannot make that mistake. 1° steps leave scallops well under
    # one nozzle; a closed-form polygon is the tidy-up, not a correctness fix.
    _hw = LEVER_HW + KL.HS_CLR
    _env = None
    for i in range(int(THROW_V) + 1):
        c = swing(_lever_envelope(), float(i))
        _env = c if _env is None else _env.union(c)
    w = w.cut(_env)
    # OPEN THE TOP over the leg AND over the arm's exit, out through the +X face.
    # Both halves of that are needed: the leg band so the leg has a slot, and the
    # +X reach because stopping at the leg left a 53 mm² flat ceiling roofing the
    # arm's full-throw position — the one thing this part cannot print.
    _x0 = -(KL.ARM_TX / 2 + KL.HS_CLR)
    _x1 = HOUS_X1 + 1.0
    _zt = HOUS_Z1 + KL.TEN_H + 2.0
    w = w.cut(box_at(_x1 - _x0, 2 * _hw, _zt - (-HUB_D / 2),
                     x=(_x0 + _x1) / 2, y=0.0, z=((-HUB_D / 2) + _zt) / 2))
    # BEARING SEATS + the sensor-side contact rib and axle way — all identical to
    # the horizontal lever, because the entire Y stack is untouched
    for by in (KL.BRG_Y0, -(KL.BRG_Y0 + KL.BRG_W + 0.3)):
        w = w.cut(printable_bore(KL.BRG_OD + 0.1, KL.BRG_W + 0.3, (0.0, by, 0.0),
                                 (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    w = w.union(contact_rib(KL.AXLE_FLANGE_D - 1.5, KL.RIB_PROUD, KL.RIB_T,
                            (0.0, HOUS_HW, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    _by0 = KL.BRG_Y0 + KL.BRG_W + 0.2
    w = w.cut(printable_bore(KL.AXLE_D + 1.0, (HOUS_HW + KL.RIB_PROUD) - _by0,
                             (0.0, _by0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                             overshoot=0.6))
    # cartridge house-pockets + drag recesses, raised with the feel block
    for dy in (KL.MAIN_YC - KL.HS_YC, 0.0):
        dx = KL.HS_SETBACK
        yc = KL.HS_YC + dy
        w = w.cut(vplace(KL._hs_pocket(yc, -HOUS_X1 - 1.0, KL.HS_BACK_X + dx)))
        _sgn = 1.0 if yc > 0 else -1.0
        _yw = yc + _sgn * KL.hs_pocket_hw()
        _ys = yc + _sgn * (KL.hs_pocket_hw() + KL.HS_DRAG_SEAT)
        w = w.cut(vplace(box_at(KL.HS_DRAG_LX + 0.4, abs(_ys - _yw),
                                KL.HS_PISTON_WZ + 0.4,
                                x=KL._drag_seat_xc(dx), y=(_yw + _ys) / 2, z=KL.HS_Z)))
    w = heal(w)
    # ...then the two female back-stop threads LAST and ALONE (thread rules)
    from cadkit.threads import threaded_rod
    for dy in (KL.MAIN_YC - KL.HS_YC, 0.0):
        nut = (threaded_rod(KL.HS_TH_MINOR, KL.HS_BSTOP_OD, KL.HS_TH_PITCH,
                            KL.HS_BSTOP_ENGAGE)
               .rotate((0, 0, 0), (0, 1, 0), 90)
               .translate((KL.HS_BACK_X + KL.HS_SETBACK, KL.HS_YC + dy, KL.HS_Z)))
        w = w.cut(vplace(nut), clean=False)
    return w


def swing(s, throw=0.0):
    """Pose a lever-frame solid at a given throw. +throw pushes the +X arm UP."""
    return s.rotate((0, 0, 0), (0, 1, 0), -throw)


kv_lever = _lever()
kv_housing = _housing()


def demo_parts():
    """Bought/printed dummies in the local frame, for the assembly."""
    out = []
    for i, by in enumerate((-(KL.BRG_Y0 + KL.BRG_W), KL.BRG_Y0)):
        out.append((f"kv_bearing_{i}", KL._bearing().translate((0, by, 0))))
    out.append(("kv_magnet", cyl_y(KL.MAG_D, KL.MAG_T, y0=KL.MAG_Y0)))
    for nm, off in (("main", KL.CART_MAIN_OFFSET), ("half_stop", KL.CART_HALFSTOP_OFFSET)):
        out.append((f"kv_{nm}_cart_base", vplace(KL.cart_base.translate(off))))
        out.append((f"kv_{nm}_cart_piston", vplace(KL.cart_piston.translate(off))))
        out.append((f"kv_{nm}_guide_post", vplace(KL.guide_post.translate(off))))
    return out


if __name__ == "__main__":
    print(f"THROW_V   {THROW_V}   LOBE_RC_V {LOBE_RC_V}   stroke {_STROKE:.2f} "
          f"(horizontal: {KL.LOBE_RC * math.sin(math.radians(KL.THROW)):.2f})")
    print(f"housing   x {HOUS_X0:.2f}..{HOUS_X1:.2f}  y ±{HOUS_HW}  z {HOUS_Z0:.2f}..{HOUS_Z1:.2f}")
    print(f"axle sits {AXLE_DROP:.2f} lower than the horizontal lever's")
    print(f"tenons at local y {TEN_Y}, sliding local x {TEN_X0:.2f}..{TEN_X1:.2f}")
