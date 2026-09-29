"""POST-FILL STITCH REPAIR, prototype on a copy. Detector = connectivity, keyed by UUID."""
import math
import pcbnew

SRC = r"elec/out/led_strip.kicad_pcb"
OUT = r"C:/Users/gus/AppData/Local/Temp/claude/C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar/d7576032-b257-4aee-8a45-89e587fe4007/scratchpad/led_fixed2.kicad_pcb"
FM, MM = pcbnew.FromMM, pcbnew.ToMM
PROBE, STEP = 12.0, 0.1


def key(it):
    try:
        return it.m_Uuid.AsString()
    except Exception:
        return None


def loose_items(b, net="GND"):
    """GND tracks/pads NOT in the zone's connected component. ⚠ keyed by UUID, never id():
    SWIG hands back a fresh wrapper per call and id() never matches."""
    b.BuildConnectivity()
    conn = b.GetConnectivity()
    zs = [z for z in b.Zones() if z.GetNetname() == net]
    linked = set()
    for z in zs:
        for it in conn.GetConnectedItems(z):
            linked.add(key(it))
    out = [t for t in b.GetTracks() if t.GetNetname() == net and key(t) not in linked]
    return out, zs


def path_clear(b, a, z, net, layer, w):
    """⚠ THE STEP THE FIRST PROTOTYPE LACKED, AND IT SHORTED THE BOARD. Sample the straight run
    from `a` to `z` and refuse it if any sample sits in copper of ANOTHER net. Without this the
    repair took led_strip to 0 unconnected AND introduced tracks_crossing 0 -> 1 -- two different
    nets crossing, which is strictly worse than the floating stub it removed."""
    import math as _m
    n = max(2, int(_m.hypot(z.x - a.x, z.y - a.y) / FM(0.1)))
    for i in range(n + 1):
        p = pcbnew.VECTOR2I(int(a.x + (z.x - a.x) * i / n), int(a.y + (z.y - a.y) * i / n))
        for o in b.GetTracks():
            if o.GetNetname() == net or o.GetLayer() != layer:
                continue
            if o.HitTest(p, int(w)):
                return False
        for m in b.GetFootprints():
            for pd in m.Pads():
                if pd.GetNetname() == net:
                    continue
                if pd.HitTest(p):
                    return False
    return True


def plane_candidates(pos, zs, limit=6):
    """Every plane point out to PROBE, nearest first -- so a blocked path can try the next."""
    out = []
    for i in range(1, int(PROBE / STEP) + 1):
        r = i * STEP
        for a in range(0, 360, 5):
            p = pcbnew.VECTOR2I(int(pos.x + r * 1e6 * math.cos(math.radians(a))),
                                int(pos.y + r * 1e6 * math.sin(math.radians(a))))
            if any(z.GetFilledPolysList(z.GetLayer()).Collide(p) for z in zs):
                out.append((p, r))
                if len(out) >= limit:
                    return out
    return out


def nearest_plane(pos, zs):
    for i in range(1, int(PROBE / STEP) + 1):
        r = i * STEP
        for a in range(0, 360, 5):
            p = pcbnew.VECTOR2I(int(pos.x + r * 1e6 * math.cos(math.radians(a))),
                                int(pos.y + r * 1e6 * math.sin(math.radians(a))))
            if any(z.GetFilledPolysList(z.GetLayer()).Collide(p) for z in zs):
                return p, r
    return None, float("nan")


b = pcbnew.LoadBoard(SRC)
loose, zs = loose_items(b)
print("before: %d loose GND track(s)" % len(loose))

laid = 0
for t in loose:
    if t.GetClass() != "PCB_TRACK":
        continue
    w = t.GetWidth()
    placed = False
    for src in (t.GetStart(), t.GetEnd()):
        for tgt, r in plane_candidates(src, zs):
            if not path_clear(b, src, tgt, t.GetNetname(), t.GetLayer(), w):
                continue
            dx, dy = tgt.x - src.x, tgt.y - src.y
            n = math.hypot(dx, dy) or 1.0
            end = pcbnew.VECTOR2I(int(tgt.x + dx / n * w), int(tgt.y + dy / n * w))
            nt = pcbnew.PCB_TRACK(b)
            nt.SetStart(src); nt.SetEnd(end); nt.SetWidth(w)
            nt.SetLayer(t.GetLayer()); nt.SetNet(t.GetNet())
            b.Add(nt)
            laid += 1
            placed = True
            print("   from (%.2f,%.2f): laid %.2f mm, path CLEAR"
                  % (MM(src.x), MM(src.y), r + MM(w)))
            break
        if placed:
            break
    if not placed:
        print("   no CLEAR path to the plane from either end -- left alone (correct: a short "
              "is worse than a floating stub)")

b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
after, _ = loose_items(b)
print("after %d repair track(s) + refill: %d loose" % (laid, len(after)))
b.Save(OUT)
print("wrote", OUT)
