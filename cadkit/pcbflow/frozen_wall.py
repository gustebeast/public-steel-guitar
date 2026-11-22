"""frozen_wall.py -- the one frozen-band wall every post-route copper writer asks (2026-11-21).

A frozen band (a pour zone named "frozen") is a power path whose shape was decided before
routing. The router keeps out of it (router.model frozen_d) and pour_around fills round it,
but copper laid AFTER the route is invisible to both: a foreign track or via inside the band's
outline is DRC-legal -- the refill simply flows round it -- and the refill then cuts the band.

⚠ WHY ONE HELPER (brain_board esc11, 2026-11-21): three writers in a row were caught doing
exactly that, each after a board was lost to it --
  * repair_plane_orphans' stub across VIN_SW's F.Cu band (rPS_e2; _path_clear got a wall),
  * link_close_gaps' GND tracks through +24V_LED's F.Cu band (rPS_11a1/11a3; its own wall),
  * rescue_stray_stitches' GND via inside +24V_RIB's band (rPS_11a4, 2.2 % of its area),
and every writer that builds its own obstacle list starts out blind to zones, because a zone
is not a track or a pad. Each wall that was added was a private copy of the same twenty lines.
Every post-route copper writer now builds a FrozenWall and asks it; test_frozen_wall.py scans
the sources so a NEW writer that does not ask fails a test instead of a board.

THE RULE (the router's): a point of copper with half-extent `half` (a track's w/2, a via's
radius) is refused when it lies inside another net's band OUTLINE, or within half + the zone's
own clearance of it. The outline, not the fill: the fill may not be poured yet, and the fill
is the outline knocked back -- copper in the gap still pushes the refill back by the clearance.
A via passes layer=None and is walled by a band on ANY layer; a track names its layer.
Bands on the asking copper's own net are never walls.

⚠ AND THE RULE AREAS (brain_board rPS_11a3, 2026-11-22: a VIN_BUS run inside the audio
domain's 1 mm moat, quality A25 hard). A keep-out that bans tracks or vias is a wall for every
net, its own edge the limit (edge distance 0, as DRC judges it and as widen_necks already
did): a track is refused by an area banning tracks on its layer, a via by one banning vias.
An ask with no layer (a via, or a layer-blind surface path) is refused by either kind.
"""
import math

import pcbnew

DEFAULT_ZC_MM = 0.5            # a band with no local clearance (pour_around's ZONE_CLR)


def _iu(v):
    return int(round(v))


class FrozenWall:
    """Built once per writer (outlines do not move after layout; only fills do)."""

    def __init__(self, board, keepouts=True):
        self.bands = []
        self.keepouts = []
        if keepouts:
            for zn in board.Zones():
                if not zn.GetIsRuleArea() or not (zn.GetDoNotAllowTracks() or zn.GetDoNotAllowVias()):
                    continue
                bb = zn.GetBoundingBox()
                self.keepouts.append(dict(zone=zn, outline=zn.Outline(), tracks=zn.GetDoNotAllowTracks(),
                                          vias=zn.GetDoNotAllowVias(),
                                          box=(bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
        for zn in board.Zones():
            if zn.GetIsRuleArea() or zn.GetZoneName() != "frozen":
                continue
            zc = zn.GetLocalClearance()
            zc = zc.value() if hasattr(zc, "value") else zc
            bb = zn.GetBoundingBox()
            self.bands.append(dict(zone=zn, outline=zn.Outline(), net=zn.GetNetname(),
                                   code=zn.GetNetCode(), zc=int(zc or pcbnew.FromMM(DEFAULT_ZC_MM)),
                                   box=(bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))

    def __bool__(self):
        return bool(self.bands or self.keepouts)

    @staticmethod
    def _own(b, net):
        if net is None:
            return False
        return b["code"] == net if isinstance(net, int) else b["net"] == net

    def band_at(self, x, y, net, half, layer=None):
        """The band (dict) a point of `net`'s copper with half-extent `half` (IU) at (x, y)
        would enter, or None. layer=None: any layer (a via)."""
        p = None
        for b in self.bands:
            if self._own(b, net) or (layer is not None and not b["zone"].IsOnLayer(layer)):
                continue
            reach = half + b["zc"]
            l_, t_, r_, bo = b["box"]
            if x < l_ - reach or x > r_ + reach or y < t_ - reach or y > bo + reach:
                continue
            if p is None:
                p = pcbnew.VECTOR2I(_iu(x), _iu(y))
            if b["outline"].Contains(p) or b["outline"].Collide(p, _iu(reach)):
                return b
        return None

    def keepout_at(self, x, y, half, layer=None):
        """The rule area (dict) copper with half-extent `half` at (x, y) would enter, or None.
        layer=None: a via (or a layer-blind ask) -- an area banning tracks or vias refuses it."""
        p = None
        for k in self.keepouts:
            if layer is None:
                if not (k["vias"] or k["tracks"]):
                    continue
            elif not k["tracks"] or not k["zone"].IsOnLayer(layer):
                continue
            l_, t_, r_, bo = k["box"]
            if x < l_ - half or x > r_ + half or y < t_ - half or y > bo + half:
                continue
            if p is None:
                p = pcbnew.VECTOR2I(_iu(x), _iu(y))
            if k["outline"].Contains(p) or k["outline"].Collide(p, _iu(half)):
                return k
        return None

    def hits(self, x, y, net, half, layer=None):
        return (self.band_at(x, y, net, half, layer) is not None
                or self.keepout_at(x, y, half, layer) is not None)

    def via_ok(self, x, y, net, radius):
        """A via (all layers) of radius `radius` IU at (x, y)."""
        return not self.hits(x, y, net, radius, None)

    def seg_ok(self, a, b, net, half, layer, step=None):
        """A track a->b ((x, y) IU) of half-width `half` on `layer`. Sampled at most every
        `step` IU (default: half a zone clearance, so a band corner cannot slip between)."""
        if not (self.bands or self.keepouts):
            return True
        step = step or pcbnew.FromMM(0.1)
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / step))
        return not any(self.hits(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n,
                                 net, half, layer) for k in range(n + 1))

    # the mm callers (power_vias, return_vias, close_last) ask in mm
    def via_ok_mm(self, x, y, net, radius_mm):
        return self.via_ok(pcbnew.FromMM(x), pcbnew.FromMM(y), net, pcbnew.FromMM(radius_mm))
