"""joinery.py — printable mortise-and-tenon slide joints (dull arrowhead).

See JOINERY_README.md for the full story. THE standard recipe — a tenon on a
sideways-printed (+Y build) host mated to a mortise in a flat-printed (+Z
build) host — is `ramp=True, hook_h=...` (print-validated in PETG; plain
`ramp=True` without a hook cams apart along the up-ramp diagonal and survives
only as a demo):

    from cadkit.joinery import arrow_tenon, arrow_mortise

    # print-validated 0.8-nozzle numbers (every face ≥ one bead); scale beads
    # not ratios for other nozzles. neck rule: stem_h = wanted_neck + clearance.
    J = dict(stem_w=2.4, head_w=4.0, stem_h=0.9, tip_w=0.8, ramp=True, hook_h=0.8)
    ten = arrow_tenon(length=5.5, **J)                      # +Y-printed host
    cut = arrow_mortise(length=12, clearance=0.1, **J)      # +Z-printed host
    host  = host.union(ten.translate(...))      # rail grows the tenon
    other = other.cut(cut.translate(...))       # ring gets the cavity

CONVENTIONS
- The profile lives in the local Y-Z plane and is extruded along +X — the
  SLIDE axis. The mortise part installs by sliding -X: relative to it the
  tenon travels +X through the cavity, entering at the cavity's OPEN -X end
  and halting against its +X END WALL — the hard stop. An external preload
  toward -X (our rubber band) then keeps the stop loaded; the only escape
  (the part sliding back +X) works against that preload.
- z=0 is the MATING PLANE (host surface the tenon grows from / the face the
  mortise opens through). The tenon extends `root` below it (union it into
  its host — volumetric fusion, never coplanar). The mortise cutter extends
  `drop` below it so the cavity opens cleanly through the host's face.
- The joint constrains ±Y and +Z (lift) by shape, -X by the stop wall; +X is
  free by design (that's the install/uninstall direction the preload guards).

VARIANTS (by print orientation of each part; more combos welcome — add them
here like threads.py grew):
- ramp=False — symmetric dull arrowhead. Mortise host AND tenon host both
  print -Z→+Z (tenon standing up).
- ramp=True  — the -Y half of the arrowhead is replaced by one straight 45°
  ramp so the TENON prints on a -Y→+Y host (mortise host still -Z→+Z).
  Point the ramp side toward the tenon host's PRINT BED.

A separate FAMILY, `octagon_tenon` / `octagon_mortise` (below), covers the
BOTH-hosts-(-Z→+Z) case with an octagon-on-fat-stem ("stop sign") section: one
`width` knob (the stem is a computed width/2), the nozzle FLOOR on the tenon and
the one-nozzle bridge CAP on the mortise roof. See the README's "Octagon joint".

Every working face is 45° ON PURPOSE — see the README for why the shared
ramp face can't be steepened for one part without hurting the other. The
only flat is the dull tip (default 1.6 = 2 bead widths of a 0.8 nozzle): a
tiny bridge in the mortise, deliberately "just big enough to print".
"""

import math

import cadquery as cq

_TIP_W = 1.6      # dull-tip flat: ~2 bead widths of a 0.8 mm nozzle


def _profile(stem_w, head_w, stem_h, tip_w, ramp, base_z, hook_h=None, nozzle=0.8):
    """Closed profile points in the local (y, z) plane, base at z=base_z.
    ENFORCES the nozzle floor: every working segment must be ≥ `nozzle`, or the
    printer can't render it accurately (raises ValueError)."""
    a, b, t = stem_w / 2.0, head_w / 2.0, tip_w / 2.0
    flare, taper = b - a, b - t
    if not (flare > 0 and taper > 0 and tip_w > 0 and stem_h >= 0):
        raise ValueError("need head_w > stem_w, head_w > tip_w > 0, stem_h >= 0")
    segs = {"stem_h (mortise neck + clearance)": stem_h, "tip_w": tip_w,
            "flare (barb per side)": flare}
    if hook_h is not None:
        segs["hook_h"] = hook_h
    else:
        segs["taper"] = taper
    bad = {k: v for k, v in segs.items() if v < nozzle - 1e-9}
    if bad:
        raise ValueError(f"segments below the {nozzle} nozzle floor: {bad} — "
                         "the printer can't render them accurately")
    if hook_h is not None:
        # SQUARE HOOK barb (print-tested fix): every 45° face is PARALLEL to the
        # up-ramp escape diagonal (+y+z), so an all-45 joint cams out that way.
        # A FLAT barb underside + vertical outer wall lock +z (and the diagonal)
        # flat-on-flat. Only for ramp=True: the flat underside is a model-(−z)
        # face = print-VERTICAL on a sideways (+Y-build) tenon; a +Z-printed
        # tenon would see it as a 90° overhang.
        # CANONICAL CLOSURE (user rule): the 45° taper off the hook is NOT free
        # length — it runs exactly until it is back HORIZONTALLY over the
        # profile's start (the stem wall), i.e. rise = the hook-flat width;
        # the dull tip then spans tip_w inward from the stem plane, and the
        # ramp closes to the base. Keeps the apex compact instead of running
        # to an arbitrary centreline.
        if not ramp:
            raise ValueError("hook_h needs ramp=True (see comment)")
        H = stem_h + hook_h + flare
        pts = [(a, base_z), (a, stem_h),           # stem wall (the profile's start)
               (b, stem_h),                        # FLAT hook underside (≥ nozzle wide)
               (b, stem_h + hook_h),               # square barb outer wall
               (a, H),                             # 45° taper — ends over the start
               (a - tip_w, H)]                     # dull tip, inward from the stem plane
    else:
        H = stem_h + flare + taper                 # total height above z=0
        pts = [(a, base_z), (a, stem_h),           # right stem wall
               (b, stem_h + flare),                # right barb (45° flare out)
               (t, H), (-t, H)]                    # 45° taper in, dull tip
    tip_left = pts[-1][0]
    if ramp:
        # ramp-side half = ONE straight 45° line, tip → foot at z=0. Rooted at
        # the host surface, so a side-printed (+Y-build) tenon never starts a
        # layer in mid-air the way a barb's leading edge would.
        pts += [(tip_left - H, 0.0)]
        if base_z < 0:
            pts += [(tip_left - H, base_z)]
    else:
        pts += [(-b, stem_h + flare), (-a, stem_h), (-a, base_z)]
    return pts, H


def arrow_height(stem_w, head_w, stem_h, tip_w=_TIP_W, hook_h=None):
    """Total tenon height above the mating plane (what the mortise host must swallow)."""
    b, t = head_w / 2.0, tip_w / 2.0
    flare = b - stem_w / 2.0
    if hook_h is not None:
        return stem_h + hook_h + flare      # hook: the taper returns over the start
    return stem_h + flare + (b - t)


def arrow_tenon(stem_w, head_w, stem_h, length, tip_w=_TIP_W, ramp=False, root=1.0,
                hook_h=None, nozzle=0.8):
    """Tenon prism along +X, base at z=0, extended `root` below for fusion.
    hook_h: square-hook barb height (flat underside; ramp=True only) — locks the
    up-ramp diagonal an all-45° profile cams out along. Every working segment is
    validated ≥ `nozzle`."""
    pts, _ = _profile(stem_w, head_w, stem_h, tip_w, ramp, -abs(root), hook_h, nozzle)
    return cq.Workplane("YZ").polyline(pts).close().extrude(length)


def arrow_mortise(stem_w, head_w, stem_h, length, tip_w=_TIP_W, ramp=False,
                  clearance=0.3, drop=2.0, hook_h=None, nozzle=0.8):
    """Cavity CUTTER: the tenon profile dilated `clearance` per side (mitred
    offset, so all faces stay 45°/vertical), dropped `drop` below the mating
    plane to open through the host's face. Extrude it out PAST the host's -X
    face so the channel is open on that side (where the tenon enters as the
    host slides -X onto it); the cutter's +X end, left inside the host, is
    the hard stop wall. Boolean-friendly plain prism."""
    if stem_h - clearance < nozzle - 1e-9:
        raise ValueError(f"mortise neck = stem_h - clearance = {stem_h - clearance:.2f} "
                         f"is below the {nozzle} nozzle floor")
    pts, _ = _profile(stem_w, head_w, stem_h, tip_w, ramp, -abs(drop), hook_h, nozzle)
    return (cq.Workplane("YZ").polyline(pts).close()
            .offset2D(clearance, "intersection")
            .extrude(length))


# ─────────────────── OCTAGON ("stop-sign") slide joint ───────────────────────
# A keyed slide joint whose cross-section is an OCTAGON on a POST — a "stop sign".
# BOTH hosts print -Z→+Z (octagon pointing +z), so it's the joint to reach for when
# neither part prints sideways. It exists for all-45°/one-bead printability:
#   • the LOWER 45° diagonal FLARES OUT (self-supporting overhang) — this flare is
#     also the retention shoulder the mortise lip captures;
#   • above the waist the UPPER diagonal TUCKS IN (each layer smaller than the one
#     below — always printable);
#   • the only unsupported span, the flat ROOF of the MORTISE cavity, is one nozzle
#     wide so the printer bridges it in a single bead. A sharp peak would print
#     rounded — the flat roof is the smallest peak a nozzle can actually lay.
#
# Two constraints, on OPPOSITE parts (both correct):
#   • the ROOF CAP is on the MORTISE roof — the face the printer bridges. The tenon
#     roof is pre-shrunk so that after the mortise's clearance dilation the bridge
#     lands on exactly one nozzle.
#   • the nozzle MINIMUM (thin-feature floor) is on the TENON — the smaller part
#     (mortise = tenon dilated), so the tenon's segments are what bind. The nominal
#     profile below IS the tenon; `octagon_width_min` is the smallest width whose
#     tenon segments all clear the nozzle.
#
# SIZING — give it ROOM, not force (see JOINERY_README "Octagon joint"). ONE knob:
#   • `width` (flat-to-flat) — the joint size. It sets the UPPER diagonal (the
#     "green" line): wider = bigger, and 45° means taller too.
#   • the STEM is width/2 and the LOWER ("orange") diagonal follows as the shoulder
#     — both computed (see _STEM_FRAC), NOT knobs. `length` is the engagement depth;
#     verticals are locked at one nozzle. The callsite makes no shape decisions.

# The stem is HALF the width — not a knob, a computed optimum. Under a lift load
# the stem carries tension (∝ stem width) while the TWO mortise lips resist in
# shear (∝ shoulder each); setting those equal gives stem = width/2 (shoulder =
# width/4 per side). Wider would starve retention, narrower would starve the neck.
_STEM_FRAC = 0.5


def _tenon_roof(nozzle, clearance):
    """Tenon top-flat width that makes the MORTISE roof (tenon dilated by
    `clearance`, mitred) exactly one nozzle. The dilation widens the horizontal
    roof by 2·clearance·(√2−1), so the tenon roof is pre-shrunk by that — the cap
    lands on the mortise BRIDGE (what the printer spans), not the tenon."""
    t = nozzle - 2.0 * clearance * (math.sqrt(2.0) - 1.0)
    if t <= 1e-6:
        raise ValueError(f"clearance {clearance} is too large for nozzle {nozzle}: "
                         "the tenon roof would vanish before the mortise bridge shrank "
                         "to one nozzle — use a smaller clearance or a coarser nozzle")
    return t


def octagon_width_min(nozzle=0.8, clearance=0.1):
    """Smallest `width` whose TENON segments (stem, upper + lower diagonal) all
    clear the nozzle floor — the tenon is the smaller part, so it binds. (The roof
    is exempt: it's the capped bridge, a supported last layer on the tenon.)"""
    n, sf = nozzle, _STEM_FRAC
    roof_t = _tenon_roof(n, clearance)
    return max(n / sf,                                       # stem = width/2 ≥ n
               n * math.sqrt(2.0) / (1.0 - sf),              # lower (orange) diagonal ≥ n
               roof_t + n * math.sqrt(2.0))                  # upper (green) diagonal ≥ n


def _octagon_profile(width, nozzle, base_z, clearance):
    """Closed (y, z) points for the TENON cross-section — the smaller part, where the
    nozzle floor is enforced. A stop sign: a `width`-wide waist over a stem of
    `width/2` (see _STEM_FRAC), joined by 45° diagonals — the UPPER (green) set by
    `width`, the LOWER (orange) shorter so the stem stays fat. The roof is
    pre-shrunk so the MORTISE roof (this dilated by clearance) is one nozzle. z=0 is
    the mating plane; the stem runs from base_z up through it. Returns
    (points, roof_z)."""
    if nozzle <= 0:
        raise ValueError("nozzle must be > 0")
    wmin = octagon_width_min(nozzle, clearance)
    if width < wmin - 1e-9:
        raise ValueError(f"width {width:.3f} is below the printable minimum "
                         f"{wmin:.3f} mm (a tenon segment would drop under the {nozzle} "
                         "nozzle) — give the joint more room, or use a finer nozzle")
    n = nozzle
    roof_t = _tenon_roof(n, clearance)     # tenon roof → mortise roof = one nozzle
    hw = width / 2.0                       # half flat-to-flat (the waist)
    stem = _STEM_FRAC * width              # FAT stem (strength optimum, = width/2)
    orange = hw - stem / 2.0               # lower diagonal run = shoulder overhang / side
    green = hw - roof_t / 2.0              # upper diagonal run (set by width)
    post_h = n                             # stem standoff above the mating plane (locked)
    z_neck = post_h
    z_wb = z_neck + orange                 # lower (orange) diagonal → waist bottom
    z_wt = z_wb + n                        # nozzle-tall vertical → waist top
    z_roof = z_wt + green                  # upper (green) diagonal → roof
    pts = [
        (stem / 2.0,  base_z),             # stem right (below the mating plane)
        (stem / 2.0,  z_neck),             # stem right wall (through z=0) to the bottom flat
        (hw,          z_wb),               # lower-right 45° diagonal → waist (shoulder)
        (hw,          z_wt),               # right vertical (one nozzle tall)
        (roof_t / 2.0, z_roof),            # upper-right 45° diagonal → roof
        (-roof_t / 2.0, z_roof),           # tenon ROOF (dilates to one nozzle in the mortise)
        (-hw,         z_wt),               # upper-left diagonal (mirror)
        (-hw,         z_wb),               # left vertical
        (-stem / 2.0, z_neck),             # lower-left diagonal
        (-stem / 2.0, base_z),             # stem left
    ]
    return pts, z_roof


def octagon_height(width, nozzle=0.8, clearance=0.1):
    """Tenon height above the mating plane (what the mortise host must swallow)."""
    _, h = _octagon_profile(width, nozzle, 0.0, clearance)
    return h


def octagon_tenon(width, length, nozzle=0.8, clearance=0.1, root=1.0):
    """Stop-sign TENON (the nominal shape, where the nozzle floor is enforced): an
    octagon-on-stem prism along +X, base at the z=0 mating plane and extended `root`
    below for fusion. Prints -Z→+Z. `width` = joint size, the stem is width/2 (a
    computed strength optimum, not a knob), `length` = engagement depth. Pass the
    SAME width/nozzle/clearance to the mortise so they mate."""
    pts, _ = _octagon_profile(width, nozzle, -abs(root), clearance)
    return cq.Workplane("YZ").polyline(pts).close().extrude(length)


def octagon_mortise(width, length, nozzle=0.8, clearance=0.1, drop=2.0):
    """Cavity CUTTER — the tenon profile DILATED `clearance` per side (mitred → faces
    stay 45°/vertical) and dropped `drop` below the mating plane so it opens through
    the host's face. Extrude PAST the host's open X-face so the tenon slides in; the
    far end left inside is the stop wall. The printed roof BRIDGE is exactly one
    nozzle (the tenon roof was pre-shrunk for this)."""
    pts, _ = _octagon_profile(width, nozzle, -abs(drop), clearance)
    return (cq.Workplane("YZ").polyline(pts).close()
            .offset2D(abs(clearance), "intersection")
            .extrude(length))


# ── Self-test: geometry gates (run `py -3.12 joinery.py`) ────────────────────
if __name__ == "__main__":
    import sys

    # neck = STEMH - CLR must clear the 0.8 floor (the library enforces it)
    STEM, HEAD, STEMH, TIP, CLR = 4.0, 7.0, 1.1, _TIP_W, 0.3
    fails = []

    def vol(a, b):
        try:
            v = a.intersect(b).val().Volume()
            return v if v > 1e-6 else 0.0
        except Exception:
            return 0.0

    for name, ramp, hook in (("symmetric", False, None), ("ramp", True, None),
                             ("ramp+hook", True, 1.0)):
        # tenon fixed at x 6.3..18.3; cavity open through the host's -x face,
        # stop wall at x = 18.6 (0.3 x-gap at the seat). The HOST moves, like
        # the real mortise part: install slide is -x, uninstall is +x.
        ten = arrow_tenon(STEM, HEAD, STEMH, 12, ramp=ramp, hook_h=hook).translate((6.3, 0, 0))
        host = (cq.Workplane("XY").box(26, 24, 7, centered=(False, True, False))
                .cut(arrow_mortise(STEM, HEAD, STEMH, 22.6, ramp=ramp, clearance=CLR,
                                   hook_h=hook)
                     .translate((-4, 0, 0))))
        n = len(ten.val().Solids())
        if n != 1:
            fails.append(f"{name}: tenon is {n} solids")
        d45 = (CLR + 0.3) / 2 ** 0.5
        checks = [
            ("seated",                   (0, 0, 0),            "=0"),
            ("+x free (uninstall dir)",  (2, 0, 0),            "=0"),
            ("-x stop (install ends)",   (-0.5, 0, 0),         ">0"),
            ("+z lift locked",           (0, 0, CLR + 0.3),    ">0"),
            ("+y locked",                (0, CLR + 0.3, 0),    ">0"),
            ("-y locked",                (0, -(CLR + 0.3), 0), ">0"),
        ]
        if hook is not None:
            # the hook's whole reason: an all-45° profile is PARALLEL to the
            # up-ramp diagonal and cams out along it (print-test finding)
            checks.append(("diag +y+z locked (the hook's job)", (0, d45, d45), ">0"))
        print(f"-- {name} --")
        for label, d, expect in checks:
            v = vol(host.translate(d), ten)
            ok = (v == 0.0) if expect == "=0" else (v > 0.0)
            print(f"  {label:<34} {v:>9.3f} mm3 (must be {expect}){'' if ok else '  <-- FAIL'}")
            if not ok:
                fails.append(f"{name}: {label} = {v:.3f}")
        if name == "ramp":
            # document the degeneracy, don't fail it: plain ramp+45 CANNOT block this
            v = vol(host.translate((0, d45, d45)), ten)
            print(f"  (known degeneracy: diag +y+z {v:>9.3f} mm3 — use hook_h to lock it)")

    # ── octagon ("stop-sign") joint: both hosts print -Z→+Z ──
    print("-- octagon --")
    WIDTH, NZ, CLR2 = 6.0, 0.8, 0.1
    Hh = octagon_height(WIDTH, NZ)
    oten = octagon_tenon(WIDTH, 14, nozzle=NZ, clearance=CLR2)      # x 0..14
    ohost = (cq.Workplane("XY").box(20, WIDTH + 8, Hh + 6, centered=(False, True, True))
             .translate((0, 0, Hh / 2.0))                          # z -3 .. Hh+3
             .cut(octagon_mortise(WIDTH, 22, nozzle=NZ, clearance=CLR2, drop=3)
                  .translate((-1, 0, 0))))                         # through-slot in x
    n_solids = len(oten.val().Solids())
    if n_solids != 1:
        fails.append(f"octagon: tenon is {n_solids} solids")
    g = CLR2 + 0.2
    ochecks = [
        ("seated",              (0, 0, 0),  "=0"),
        ("+x slide free",       (2, 0, 0),  "=0"),
        ("-x slide free",       (-2, 0, 0), "=0"),
        ("+z lift locked",      (0, 0, g),  ">0"),
        ("-z push locked",      (0, 0, -g), ">0"),
        ("+y locked",           (0, g, 0),  ">0"),
        ("-y locked",           (0, -g, 0), ">0"),
    ]
    for label, d, expect in ochecks:
        v = vol(ohost.translate(d), oten)
        ok = (v == 0.0) if expect == "=0" else (v > 0.0)
        print(f"  {label:<20} {v:>9.3f} mm3 (must be {expect}){'' if ok else '  <-- FAIL'}")
        if not ok:
            fails.append(f"octagon: {label} = {v:.3f}")
    # the ROOF CAP is on the MORTISE — exactly one nozzle at any width (measured off
    # the cutter's top face — this is the face the printer actually bridges)
    for w in (WIDTH, WIDTH * 3.0, octagon_width_min(NZ, CLR2)):
        m = octagon_mortise(w, 6, nozzle=NZ, clearance=CLR2)
        top = max(m.val().Faces(), key=lambda f: f.Center().z)
        rw = top.BoundingBox().ylen
        ok = abs(rw - NZ) < 1e-3
        print(f"  mortise roof @ w={w:5.2f}  {rw:.3f} mm (must be = nozzle {NZ}){'' if ok else '  <-- FAIL'}")
        if not ok:
            fails.append(f"octagon: mortise roof at width {w} = {rw:.3f} != {NZ}")
    # the MINIMUM is on the TENON: every load segment (stem, both diagonals,
    # vertical) >= nozzle — the tenon is the smaller part. (Roof is exempt: it's the
    # capped bridge, a supported last layer.) seg(1)=lower/orange, seg(2)=vertical,
    # seg(3)=upper/green; stem = 2·pts[1].y.
    wmin = octagon_width_min(NZ, CLR2)
    tpts, _ = _octagon_profile(wmin, NZ, 0.0, CLR2)           # nominal = tenon
    seg = lambda i: math.hypot(tpts[i + 1][0] - tpts[i][0], tpts[i + 1][1] - tpts[i][1])
    stem_w, orange, vert, green = 2 * tpts[1][0], seg(1), seg(2), seg(3)
    worst = min(stem_w, orange, vert, green)
    ok = worst >= NZ - 1e-6
    print(f"  tenon floor @ wmin={wmin:.2f}  stem={stem_w:.3f} orange={orange:.3f} "
          f"vert={vert:.3f} green={green:.3f} (min >= {NZ}){'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append(f"octagon: tenon segment {worst:.3f} < nozzle {NZ}")
    # the fat stem: stem = width/2 (computed optimum), and the lower (orange)
    # diagonal is SHORTER than the upper (green) so the stem stays thick
    tpts, _ = _octagon_profile(WIDTH, NZ, 0.0, CLR2)
    seg = lambda i: math.hypot(tpts[i + 1][0] - tpts[i][0], tpts[i + 1][1] - tpts[i][1])
    stem_w, orange, green = 2 * tpts[1][0], seg(1), seg(3)
    ok = abs(stem_w - 0.5 * WIDTH) < 1e-6 and orange < green
    print(f"  fat stem @ w={WIDTH}   stem={stem_w:.3f} (=width/2) "
          f"orange={orange:.3f} < green={green:.3f}{'' if ok else '  <-- FAIL'}")
    if not ok:
        fails.append(f"octagon: stem {stem_w:.3f} or orange>=green")
    # below the tenon-minimum width must raise
    try:
        octagon_tenon(wmin - 0.2, 10, nozzle=NZ, clearance=CLR2)
        fails.append("octagon: sub-minimum width did not raise")
        print("  width floor           did NOT raise  <-- FAIL")
    except ValueError:
        print(f"  width floor           raises below {wmin:.2f} mm (ok)")

    if fails:
        print("FAIL:", *fails, sep="\n  ")
    else:
        print("OK — all variants: seat clear, only the band-guarded +x is free; "
              "hook locks the up-ramp diagonal; octagon locks +-y/+-z, fat stem, "
              "tenon floor >= nozzle, mortise roof one nozzle at any width.")
    sys.exit(len(fails))
