import sys, pcbnew
D = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"
for spec in sys.argv[1:]:
    lib, name = spec.split(":")
    fp = pcbnew.FootprintLoad(D + "\\" + lib + ".pretty", name)
    cy = fp.GetCourtyard(pcbnew.F_CrtYd) if hasattr(fp, "GetCourtyard") else None
    bb = fp.GetBoundingBox(False)
    try:
        c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cyd = (pcbnew.ToMM(c.GetLeft()), pcbnew.ToMM(c.GetTop()), pcbnew.ToMM(c.GetRight()), pcbnew.ToMM(c.GetBottom()))
    except Exception as e:
        fp.BuildCourtyardCaches() if hasattr(fp, "BuildCourtyardCaches") else None
        c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        cyd = (pcbnew.ToMM(c.GetLeft()), pcbnew.ToMM(c.GetTop()), pcbnew.ToMM(c.GetRight()), pcbnew.ToMM(c.GetBottom()))
    print(name, "crtyd", [round(v, 2) for v in cyd])
    if "-v" in sys.argv[0:1] or name.startswith("JST"):
        for p in fp.Pads():
            print("   pad", p.GetNumber(), round(pcbnew.ToMM(p.GetPosition().x), 2), round(pcbnew.ToMM(p.GetPosition().y), 2),
                  round(pcbnew.ToMM(p.GetSize(pcbnew.F_Cu).x), 2), round(pcbnew.ToMM(p.GetSize(pcbnew.F_Cu).y), 2))
