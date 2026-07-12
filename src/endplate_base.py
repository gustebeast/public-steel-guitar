"""Shared endplate base — the TWO INITIAL PRISMS both endplates start from.

Endplate methodology (user): the keyhead and the bridge endplate are DRAWN
FROM THE SAME TWO PRISMS (shared code, this module), then each unions its
own string-holding mechanism above the deck and cuts/adds its specific
features (windows, ledges, dovetail sockets, stow bores, jack recesses,
leg-shell foot pockets) from there:

  1) the FILL SLAB (z -23.15 .. 6): full endplate thickness x full width
     (rail outer to rail outer), foot line up to the deck level. This band
     IS the end's cross-tie (no separate chassis crossbar) and ties the
     rails together.
  2) the FOOT BOX (z bed .. -23.15): the same footprint continued to the
     floor, hollowed to CH.T (10) exterior walls — the instrument's END
     face and the two +-Y side faces stay solid; the interior face opens
     toward the chassis box (the rail-end shells + dovetail tongues come
     from the chassis side).

`end` picks which X face is the instrument's exterior end wall: the
keyhead keeps its -X face ('lo'), the bridge its +X face ('hi').
"""

from __future__ import annotations

import cadquery as cq

from . import chassis as CH
from .helpers import box_at


def endplate_base(xlo: float, xhi: float, end: str) -> cq.Workplane:
    """The two shared prisms for an endplate spanning x xlo..xhi (both
    endplates: 25.2). end='lo' -> solid -X end wall (keyhead); end='hi'
    -> solid +X end wall (bridge). Exterior side walls always CH.T."""
    yfl = CH.Y_LO - CH.T / 2                    # -Y rail outer face
    yfh = CH.Y_HI + CH.T / 2                    # +Y rail outer face
    yc, yw = (yfl + yfh) / 2, yfh - yfl
    xc, xw = (xlo + xhi) / 2, xhi - xlo
    z6, foot_z = CH.TP_GZ1, CH.KH_DT_Z0         # deck level / foot line
    # prism 1: the FILL SLAB (foot line -> deck level), fully solid
    w = box_at(xw, yw, z6 - foot_z, x=xc, y=yc, z=(z6 + foot_z) / 2)
    # prism 2: the FOOT BOX (bed -> foot line), hollowed to CH.T walls —
    # the hollow steps 0.1 into the slab (no coincident-face seam) and
    # opens through the interior X face
    foot = box_at(xw, yw, foot_z - CH.Z_BOT, x=xc, y=yc,
                  z=(foot_z + CH.Z_BOT) / 2)
    hx0 = xlo + CH.T if end == "lo" else xlo - 1.0
    hx1 = xhi + 1.0 if end == "lo" else xhi - CH.T
    foot = foot.cut(box_at(hx1 - hx0, (yfh - CH.T) - (yfl + CH.T),
                           (foot_z + 0.1) - (CH.Z_BOT - 1.0),
                           x=(hx0 + hx1) / 2, y=yc,
                           z=((CH.Z_BOT - 1.0) + (foot_z + 0.1)) / 2))
    return w.union(foot)
