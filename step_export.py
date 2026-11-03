"""Shared STEP exporter for CadQuery 3D-printing projects.

A bare ``cq.exporters.export(obj, "housing.step")`` names the STEP *product*
"Open CASCADE STEP translator 7.8 …", so slicers and viewers (Bambu Studio)
show that instead of "housing". This helper exports normally, then
rewrites the product name to match the file stem — giving a single, correctly
named product that every viewer reads, with no extra wrapper assembly.

Usage (single printed part):

    from cadkit.step_export import export_step

    export_step(part, "housing.step")          # imports/slices as "housing"

For a multi-part *assembly*, keep using ``cq.Assembly`` with a per-part
``name=`` on each ``.add(...)`` — that already names every product.

ONE PRINT IN TWO FILAMENTS (public-steel-guitar, 2026-11-03): bodies that
print as one object, each in its own filament, go in ONE file:

    export_print_parts([("chassis_1", body), ("chassis_1_light", window)],
                       PRINT_ORIENTATION["chassis_1"], "petg-gf/chassis_1.step")

Every body is posed by the SAME transform, so they keep their places
relative to each other, and each is its own named product under one named
for the file. Bambu Studio loads that as ONE object with one part per
body, named after the products, with no prompt — and gives each part its
own filament (checked on a real import, 2026-11-03).

PRINT POSE (user, cable-spool #935): per-part STEP files should land in the
slicer ALREADY print-oriented — nobody should have to remember which way to
flip a part in Bambu. Wrap each export in ``print_pose``:

    export_step(print_pose(part, "flip"), "lid.step")     # a +z→−z print
    export_step(print_pose(part), "frame.step")           # models as printed
    export_step(print_pose(part, ((1, 0, 0), -90)), ...)  # bed = its +y face

It rotates the part onto its documented bed face, drops it to z = 0 and
centres it on x/y. EXPORT-ONLY by design: pass the posed copy straight to
``export_step`` and keep adding the as-modeled part to the ``cq.Assembly`` —
the viewer keeps every part in its assembly place.

DECLARE IT ONCE (cable-spool #1070). A part's bed face is a fact about the
part, and the project states it in ONE table of `PrintOrientation`s, which
both this exporter and the joinery's `facing` read:

    from cadkit.orientation import PrintOrientation as PO

    PRINT_ORIENTATION = {
        "lid":   PO("flip", "modelled top is the bed — slots print clean"),
        "frame": PO(None, "models as printed"),
    }

    for name, part, fname in PARTS:
        export_print(part, PRINT_ORIENTATION[name], out / fname)

`export_print` REFUSES anything that is not a `PrintOrientation`, so a part
can no longer be exported with its bed face unstated — which is how a TPU pin
shipped standing on its end as a 5.9:1 tower. Call `require_declared()` on the
table at import time to catch a missing or stale name, and print
`unconfirmed()` on every build so a guessed orientation stays visible. The
legacy ``PRINT_ROT = {name: rotate}`` forms still work through `print_pose`
during migration.

Self-test: ``python -m cadkit.step_export`` (or run this file).
"""

import pathlib
import re

import cadquery as cq

from .orientation import PrintOrientation

# Matches a STEP PRODUCT entity's first two fields (id, name), which both carry
# the OCC default name. The fields can be split across lines, so \s* spans them.
_PRODUCT_RE = re.compile(r"PRODUCT\(\s*'[^']*'\s*,\s*'[^']*'")


def export_step(obj, path, name=None):
    """Export ``obj`` to ``path`` as STEP, naming the product after the file
    stem (or ``name`` if given).

    ``obj`` may be a ``cq.Workplane``, ``cq.Shape``/``cq.Solid`` — anything
    ``cq.exporters.export`` accepts. The geometry is the standard CadQuery
    export; only the product name is rewritten.
    """
    path = str(path)
    label = name or pathlib.Path(path).stem
    cq.exporters.export(obj, path)
    _rename_products(path, label)


def export_print(obj, orientation, path, name=None):
    """Pose ``obj`` for printing and export it — the ONE export path for a
    printed part.

    Unlike ``export_step(print_pose(obj, rot), path)`` this REFUSES an
    undeclared bed face: ``orientation`` must be a
    `cadkit.orientation.PrintOrientation`, so "nobody said" can no longer
    arrive as the same ``None`` that means "models as printed" (#1070).
    """
    if not isinstance(orientation, PrintOrientation):
        raise TypeError(
            "export_print needs a PrintOrientation for %s, not %r. Every "
            "printed part declares its bed face AND the reason for it:\n"
            "    from cadkit.orientation import PrintOrientation as PO\n"
            "    PO(None, 'models as printed')   PO('flip', 'why')\n"
            "    PO(((1, 0, 0), -90), 'stands on its +y face')"
            % (name or pathlib.Path(str(path)).stem, orientation))
    export_step(print_pose(obj, orientation), path, name)


def export_print_parts(parts, orientation, path, name=None):
    """Pose several bodies that print as ONE object and export them to ONE
    STEP: a product per body, named after it, under a product named after the
    file (or ``name``). ``parts`` is a sequence of ``(part_name, obj)``; an
    entry with no solid is left out, and a single body is a plain
    `export_print`. ``orientation`` is the object's one `PrintOrientation`:
    the bodies share a bed, so they share a bed face."""
    if not isinstance(orientation, PrintOrientation):
        export_print(None, orientation, path, name)   # raises the same TypeError
    path = str(path)
    label = name or pathlib.Path(path).stem
    ws = [(n, o if isinstance(o, cq.Workplane) else cq.Workplane(obj=o)) for n, o in parts]
    ws = [(n, w) for n, w in ws if w.solids().size()]
    if not ws:
        raise ValueError("export_print_parts: no solid in any of %s" % [n for n, _ in parts])
    if len(ws) == 1:
        return export_print(ws[0][1], orientation, path, label)
    names = [n for n, _ in ws]
    assert len(set(names)) == len(names), "two bodies named alike: %s" % names
    posed = _pose([w for _, w in ws], orientation.rot)
    top = label
    while top in names:                    # cq.Assembly wants every name unique;
        top += "_"                         # the file still says `label` (below)
    assy = cq.Assembly(name=top)
    for n, w in zip(names, posed):
        assy.add(w, name=n)
    assy.export(path)
    if top != label:
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        text = text.replace("PRODUCT('%s','%s'" % (top, top), "PRODUCT('%s','%s'" % (label, label))
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)


def read_print_parts(path):
    """[(name, shape)] of a print STEP: one per body of an `export_print_parts`
    file, named as it was written, or the one body of a plain export, named
    after the file. For checkers, which judge each filament's body on its own.

    Read through XCAF, not ``cq.Assembly.importStep``: that one keys bodies by
    name and returns none when a body is named like its file, which is what
    `export_print_parts` writes (``chassis_1`` in chassis_1.step)."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool

    path = str(path)
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    if reader.ReadFile(path) != 1:
        raise OSError("could not read STEP %s" % path)
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    def named(label):
        attr = TDataStd_Name()
        return attr.Get().ToExtString() if label.FindAttribute(TDataStd_Name.GetID_s(), attr) else ""

    free = TDF_LabelSequence()
    tool.GetFreeShapes(free)
    out = []
    for i in range(1, free.Length() + 1):
        comps = TDF_LabelSequence()
        tool.GetComponents_s(free.Value(i), comps)
        for j in range(1, comps.Length() + 1):
            ref = TDF_Label()
            tool.GetReferredShape_s(comps.Value(j), ref)
            out.append((named(ref), cq.Shape.cast(tool.GetShape_s(comps.Value(j)))))
    if len({n for n, _ in out}) > 1:       # a plain export of a multi-solid part is
        return out                          # components too, all under one name
    return [(pathlib.Path(path).stem, cq.importers.importStep(path).val())]


def _pose(ws, rotate):
    """The Workplanes ``ws`` moved by ONE print pose: rotated alike, then
    dropped and centred by their joint bounding box (see `print_pose`)."""
    if rotate == "flip":
        rotate = ((1.0, 0.0, 0.0), 180.0)
    if rotate is not None:
        axis, deg = rotate
        ws = [w.rotate((0.0, 0.0, 0.0), tuple(axis), deg) for w in ws]
    bbs = [cq.Compound.makeCompound(w.vals()).BoundingBox() for w in ws]
    x0, x1 = min(b.xmin for b in bbs), max(b.xmax for b in bbs)
    y0, y1 = min(b.ymin for b in bbs), max(b.ymax for b in bbs)
    z0 = min(b.zmin for b in bbs)
    return [w.translate((-(x0 + x1) / 2.0, -(y0 + y1) / 2.0, -z0)) for w in ws]


def print_pose(obj, rotate=None):
    """``obj`` posed for PRINTING: rotated onto its bed face, dropped so
    its lowest point sits at z = 0, centred on x/y. EXPORT-ONLY — feed
    the result to ``export_step`` and keep the as-modeled part in the
    assembly, so viewer poses never move.

    rotate:
      None         the part already models in print orientation
                   (drop-and-centre only)
      "flip"       180° about X — the standard +z→−z print (the modeled
                   TOP face is the bed)
      (axis, deg)  anything else, about the origin: ((1, 0, 0), -90)
                   stands a part on its +y face, etc.

    A `cadkit.orientation.PrintOrientation` is also accepted, and is what
    projects should pass — it carries the same rotation plus the REASON for
    it. Prefer `export_print`, which refuses the bare forms outright.
    """
    if isinstance(rotate, PrintOrientation):
        rotate = rotate.rot
    return _pose([obj if isinstance(obj, cq.Workplane) else cq.Workplane(obj=obj)], rotate)[0]


def _rename_products(path, label):
    """Rewrite every PRODUCT id/name in the STEP file to ``label`` so the
    slicer/viewer show the part as its filename, not the OCC translator
    string. No-op if the file has no PRODUCT entity."""
    text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    new = _PRODUCT_RE.sub(f"PRODUCT('{label}','{label}'", text)
    if new != text:
        # newline="" keeps the file's existing line endings unchanged.
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)


if __name__ == "__main__":
    # print_pose self-test: an off-origin box with a marker nub on its +z
    # face, in each rotate mode.
    def _box():
        b = (cq.Workplane("XY").workplane(offset=30.0)
             .center(50.0, -20.0).rect(10.0, 6.0).extrude(4.0))
        return b.union(cq.Workplane("XY").workplane(offset=34.0)
                       .center(50.0, -20.0).rect(2.0, 2.0).extrude(1.0))

    def _bb(w):
        return w.val().BoundingBox()

    bb = _bb(print_pose(_box()))                       # drop + centre only
    assert abs(bb.zmin) < 1e-9 and abs(bb.zmax - 5.0) < 1e-9
    assert abs(bb.xmin + bb.xmax) < 1e-9 and abs(bb.ymin + bb.ymax) < 1e-9

    bb = _bb(print_pose(_box(), "flip"))               # nub becomes the bed side
    assert abs(bb.zmin) < 1e-9 and abs(bb.zmax - 5.0) < 1e-9
    # flipped: the 2-wide nub is DOWN, so the slab's full 10x6 face is at the TOP
    assert abs(bb.xlen - 10.0) < 1e-9 and abs(bb.ylen - 6.0) < 1e-9

    bb = _bb(print_pose(_box(), ((1.0, 0.0, 0.0), -90.0)))   # stand on +y face
    assert abs(bb.zmin) < 1e-9 and abs(bb.zlen - 6.0) < 1e-9, \
        "the 6-long y edge must become the height"

    # a bare Shape (not a Workplane) is accepted too
    bb = _bb(print_pose(_box().val()))
    assert abs(bb.zmin) < 1e-9

    # a PrintOrientation poses exactly like the bare form it carries
    from .orientation import PrintOrientation as _PO
    for _rot in (None, "flip", ((1.0, 0.0, 0.0), -90.0)):
        a = _bb(print_pose(_box(), _rot))
        b = _bb(print_pose(_box(), _PO(_rot, "self-test")))
        assert (abs(a.zlen - b.zlen) < 1e-9 and abs(a.xlen - b.xlen) < 1e-9
                and abs(a.ylen - b.ylen) < 1e-9), _rot

    # export_print refuses an undeclared bed face, in every bare form
    import tempfile, os
    _d = tempfile.mkdtemp()
    for _bad in (None, "flip", ((1.0, 0.0, 0.0), -90.0)):
        try:
            export_print(_box(), _bad, os.path.join(_d, "x.step"))
        except TypeError as e:
            assert "PrintOrientation" in str(e)
        else:
            raise AssertionError("export_print accepted %r" % (_bad,))
    _f = os.path.join(_d, "nub.step")
    export_print(_box(), _PO("flip", "self-test"), _f)
    assert "nub" in pathlib.Path(_f).read_text(errors="replace")

    # export_print_parts: one file, a named product per body, posed together
    _f = os.path.join(_d, "pair.step")
    _lid = cq.Workplane("XY").workplane(offset=35.0).center(50.0, -20.0).rect(10.0, 6.0).extrude(1.0)
    export_print_parts([("pair", _box()), ("pair_lid", _lid),
                        ("pair_none", cq.Workplane("XY"))], _PO("flip", "self-test"), _f)
    _t = pathlib.Path(_f).read_text(errors="replace")
    assert _t.count("PRODUCT('pair','pair'") == 2, "the file and its first body"
    assert "PRODUCT('pair_lid','pair_lid'" in _t and "pair_none" not in _t
    _back = cq.importers.importStep(_f)
    assert _back.solids().size() == 2
    _bb = cq.Compound.makeCompound(_back.solids().vals()).BoundingBox()
    assert abs(_bb.zmin) < 1e-6 and abs(_bb.zlen - 6.0) < 1e-6, "posed as one, the lid on the bed"
    assert [n for n, _ in read_print_parts(_f)] == ["pair", "pair_lid"]
    assert [n for n, _ in read_print_parts(os.path.join(_d, "nub.step"))] == ["nub"]

    print("cadkit.step_export self-test OK")
