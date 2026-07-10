# Shared FreeCAD viewer + 3D project conventions

This folder is the shared tooling **and the canonical reference for starting a
new CadQuery project** under `Archive/3D`. New project? Jump straight to
[Starting a new 3D project](#starting-a-new-3d-project) below.

The centrepiece is a live FreeCAD viewer: it opens a project's assembly with
each part coloured and individually show/hide-able, then watches the STEP file
on disk and **auto-reloads on every rebuild** — preserving your camera and
hidden parts. No API, no clicks. The code here is used as-is by every project;
nothing is copied per project — only the STEP path differs, and the launcher
resolves that automatically.

```
Archive/3D/
  freecad/              <- you are here (shared)
    freecad_view.py     PROJECT-FACING: show(step) — "make this viewable" (launch hub / open tab)
    freecad_viewer.py   runs inside FreeCAD — the hub: import as named parts, colour, watch, reload, tabs
    view.FCMacro        thin entry FreeCAD runs; reads FREECAD_VIEW_STEP + FREECAD_VIEW_INBOX, calls start_hub()
    open_viewer.ps1     human convenience shim over freecad_view.py
    cq_colors.py        build-side helper: hex / 0..255 / name -> cq.Color (for baking colours into the STEP)
    step_export.py      build-side helper: export_step(obj, path) — names the STEP product after the file
    overlap_check.py    build-side helper: parallel interpenetration gate (projects wrap it in tools/check_overlaps.py)
    agent_sync.py       MULTI-AGENT (opt-in): git-worktree coordination — lead owns the build/tab, contributors file merge requests. See `-h` and CLAUDE.md.
    README.md
  servo-steel/          a project (has src/build.py -> assembly.step)
  single-ball-adapter/  a project (-> adapter.step)
  ...
```

---

## Starting a new 3D project

Point the agent at this section. With the skill below + a reference project
(`retractable-cable-spool/` is the canonical one) it has everything it needs.

**1. Use the CAD skill.** Models are parametric **CadQuery** (Python). Install
the skill once:

```bash
git clone https://github.com/flowful-ai/cad-skill ~/.claude/skills/parametric-3d-printing
```

It activates on 3D-print keywords or `/parametric-3d-printing` and works in
phases (base shape → features → finish). Needs **Python 3.10–3.12**
(`py -3.12 -m pip install cadquery`); viewing needs **FreeCAD 1.1** (see
[Requirements](#requirements--notes)).

**2. Copy the project layout** (worked example: `retractable-cable-spool/`):

```
<project>/
  src/
    build.py        orchestrator: builds parts, exports each STEP + assembly.step, calls show()
    dimensions.py   ALL shared constants — one source of truth; assert invariants here
    helpers.py      geometric helpers + heal() (OCCT ShapeFix before export)
    <part>.py       one module per printed part / subsystem
  tools/
    build_counter.txt    gitignored, per-machine build number
    check_geometry.py    optional bbox/volume regression gate
```

(A nested package dir — modules directly in the project dir, run as
`-m <project>.build` from the parent — also works; see `ha-keypad/keycaps/`.
`src/` is the default. Either way the package uses relative imports, so it runs
as a module, never as a bare `python build.py`; anchor outputs to `__file__`
per §3 so they land in the project folder regardless of the launch cwd.)

**3. STEP file conventions** — what the viewer and slicer expect:

- **Export STEP, never STL.** This workflow is STEP-only — the viewer and the
  slicer both consume STEP, which keeps the named, separable, coloured part
  structure that STL throws away. ⚠️ The CAD skill above emits STL + preview PNGs
  by default; override it and write `.step` (`export_step(obj, "name.step")` for
  parts, `asm.save("assembly.step", mode="default")` for the assembly). No `.stl`
  outputs.
- **One STEP per printed part** — `housing.step`, `axle.step`, … each a single
  solid you actually print. The slicer imports these individually.
- **Name every product to match its filename.** A bare
  `cq.exporters.export(part, "housing.step")` names the product *"Open CASCADE
  STEP translator 7.8 …"*, which is what the slicer/viewer then show. Use the
  shared exporter `step_export.py` instead — it exports normally, then rewrites
  the STEP product name to the file stem (one cleanly named product):
  ```python
  sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
  from step_export import export_step
  export_step(part, "housing.step")     # imports/slices as "housing"
  ```
  (For `assembly.step`, the per-part `name=` already does this.)
- **Dummy / visualization parts get NO standalone STEP.** Purchased or
  off-the-shelf items (springs, bearings, screws, switch bodies, motors) exist
  *only* inside the assembly, for fit-checking — never export them as printable
  files.
- **One `assembly.step`** — every part (printed **and** dummies) placed at its
  as-built position, kept **separate and coloured**:
  `cq.Assembly(...).add(part, name=…, color=…)` exported with parts un-fused
  (`mode="default"`). Each `name=` becomes an individually toggleable, coloured
  entry in the viewer. This is the file `show()` opens.
- **Write outputs relative to the build script, not the cwd.** Anchor every
  output path (and the `show()` path) to the script's own folder —
  `OUT = pathlib.Path(__file__).resolve().parent`, then
  `export_step(obj, str(OUT / "housing.step"))` and `show(str(OUT / "assembly.step"))`.
  A bare `"housing.step"` lands wherever the build was *launched* from, which
  scatters files into a parent dir when a package is run as `-m pkg.build`.

**4. Build number — bump it, and ANNOUNCE it.** The assembly carries a 3-D
number floating above it, incremented on every full build. **The agent MUST
tell the user the new number each time it increments** — that's the user's
receipt that a fresh model actually reached the viewer (the tab reloads too, but
the number is the proof). The build prints `[build #N]`; surface that in your
reply (e.g. *"Pushed build #42."*). Pattern (see `retractable-cable-spool`):

```python
COUNTER = pathlib.Path(__file__).resolve().parent.parent / "tools" / "build_counter.txt"

def _bump():
    n = (int(COUNTER.read_text()) + 1) if COUNTER.exists() else 1
    COUNTER.write_text(f"{n}\n")
    return n

# while building assembly.step, after adding the real parts + dummies:
n = _bump()
try:                                   # text engine can fail; never break the build
    asm.add(cq.Workplane("XZ").text(str(n), 20, 4).translate((0, 0, Z_ABOVE_ASSEMBLY)),
            name="build_counter")      # floats above; lives in assembly.step ONLY
except Exception:
    pass
asm.save("assembly.step", mode="default")
print(f"[build #{n}]")                 # <- announce this N to the user
```

**5. Make it viewable + colour it.** End the build with `show("assembly.step")`
(see [The contract](#for-an-llm-agent-eg-claude--how-to-use-this)) and bake
colours into the STEP (see [Per-part colours](#per-part-colours-baked-into-the-step)).
The whole loop is then: edit source → `py -3.12 -m src.build` → the tab reloads
→ announce the new build number.

### Token efficiency

Claude Code has **no setting to auto-compact at a fixed percentage** (only an
on/off `autoCompactEnabled`), and the model can't reliably read its own context
level — so "compact at 50%" can't be enforced from config or a CLAUDE.md rule.
What actually helps:

- Delegate heavy, read-only exploration (scanning many files/modules) to
  **subagents** so large reads never enter the main context.
- Run **`/compact`** at natural breakpoints (after a part is finalised) instead
  of waiting for auto-compact near the limit; **`/context`** shows current fill.
- Keep `dimensions.py` the one source of truth so fewer files need re-reading.

---

## For an LLM agent (e.g. Claude) — how to use this

**The contract.** A project's `src/build.py` calls **one verb** — `show(step)`
from `freecad_view` — at the end of its build, so that
**`py -3.12 -m src.build` alone is enough**: the build writes the STEP file
*and* makes sure it's viewable. The project doesn't reason about windows, tabs,
or refreshes; `show()` decides whether to launch the hub, open a tab, or do
nothing (the tab's own file-watcher handles the reload). `show()` never raises,
so it can't break a build.

```python
# once, near the top of src/build.py (same sys.path used for cq_colors)
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from freecad_view import show

# ...at the end of _export_assembly(), after writing assembly.step:
show("assembly.step")
```

**Wiring status:** every CadQuery project is wired this way —
`retractable-cable-spool`, `servo-steel`, `single-ball-adapter`, `plant-pot`,
and `ha-keypad/keycaps`. (`banjo-wall-mount` is modelled in Onshape, not
CadQuery, so it's excluded; `pantorouter` is a browser app with no build.)

**Single-window / tabbed.** There is one FreeCAD "hub" window; every project
opens as its own tab. The launcher is **idempotent** via a single TEMP-local
hub marker plus an inbox directory:

- First build writes `%TEMP%\freecad_viewer_hub.pid` and starts FreeCAD,
  opening that project as the first tab.
- Subsequent builds (any project) check the marker; if the hub is alive they
  drop the STEP path into `%TEMP%\freecad_viewer_inbox\` and the hub opens it
  as a **new tab** — no new window. If that project is already a tab, the
  request is a no-op and the tab's own file-watcher handles the reload.
- If the hub is gone (user closed FreeCAD, or rebooted), the stale marker is
  detected and a fresh hub is started (the inbox is cleared first so old tabs
  don't resurrect).

```powershell
# Manual launch — same idempotent rules apply
& "C:\Users\gus\Sync\Documents\Archive\3D\freecad\open_viewer.ps1" `
    -Project "C:\Users\gus\Sync\Documents\Archive\3D\<project>"
```

The launcher auto-detects the STEP file (prefers `assembly.step`, else the lone
top-level `*.step`). It starts FreeCAD detached and returns immediately; the
window stays open for the user.

**To push a design change with no user involvement** (this is the whole point):

1. Edit the project's CadQuery source under `<project>/src/`.
2. Rebuild: `py -3.12 -m src.build` (run from the project folder).
3. The build writes the STEP and calls the launcher. If a viewer was already
   up it reloads within ~1 s (mtime poll). If not, the launcher starts one.
   Either way, the agent doesn't touch FreeCAD directly.

**Do not** re-enable or call the Onshape push — it's intentionally disabled to
save API quota (see below). The build writing the STEP file IS the refresh
signal.

**Measuring / inspecting** is the user's job in the FreeCAD GUI (Measure tool,
spacebar to toggle part visibility). You don't drive that.

---

## Multiple projects (tabs in one window)

Open as many projects as you like; each becomes a **tab** in the single hub
window. Just point the launcher at each project:

```powershell
$V = "C:\Users\gus\Sync\Documents\Archive\3D\freecad\open_viewer.ps1"
& $V -Project "C:\Users\gus\Sync\Documents\Archive\3D\servo-steel"             # first tab (starts hub)
& $V -Project "C:\Users\gus\Sync\Documents\Archive\3D\retractable-cable-spool" # second tab (queued via inbox)
```

Each tab watches **only its own project's STEP file**, so rebuilding servo-steel
reloads just that tab — the spool tab is untouched (and a background reload
won't steal the tab you're currently looking at). Distinct document names
(`<project>_viewer`) keep them separate. Switch tabs along the top of the 3D
area; the isolate / show-all hotkeys act on whichever tab is active.

This works for two LLM agents too: agent A building servo-steel and agent B
building the spool both feed the same hub window, each updating its own tab.
The trade-off vs. separate windows is that you see one project at a time — if
you'd rather watch two side by side simultaneously, say so and I can add a
`-SeparateWindow` switch.

> If FreeCAD ever opens projects as floating sub-windows instead of tabs, the
> MDI is in sub-window mode — toggle it from the **Windows** menu (tabbed mode
> is the default).

---

## For a human

Open any project (run from inside the project folder — `-Project` defaults to
`$PWD`):

```powershell
& "C:\Users\gus\Sync\Documents\Archive\3D\freecad\open_viewer.ps1"
```

Or be explicit:

```powershell
$V = "C:\Users\gus\Sync\Documents\Archive\3D\freecad\open_viewer.ps1"
& $V -Project "C:\Users\gus\Sync\Documents\Archive\3D\servo-steel"
& $V -Step    "C:\Users\gus\Sync\Documents\Archive\3D\servo-steel\assembly.step"
```

In FreeCAD: **spacebar** toggles the selected part's visibility; the **Measure**
tool (Tools menu) does point/edge/plane distances. Set the mouse to match
Onshape via **Edit → Preferences → Display → Navigation → 3D Navigation →
TinkerCAD** (right-drag rotate, scroll zoom, middle-drag pan). In the same panel
set **Rotation mode → Object center** so the model orbits about its centre
(closest to Onshape) rather than the viewport centre. Both are global FreeCAD
preferences — set once, they apply to every tab and every launch.

**Viewer hotkeys** (added by the viewer, Onshape-style):

- **`I`** — isolate: hide every part except the selected one(s). Select a part
  in the tree or 3D view first, then press `I`.
- **`Shift+I`** — show all parts again (also your "undo a hide", since FreeCAD
  doesn't put visibility on the Ctrl+Z undo stack).
- **`M`** — launch the Measure tool.

To **measure point-to-point distance**: start Measure (or press `M`), click the first vertex,
then **Ctrl+click** the second (a plain click replaces the selection instead of
adding to it), and tick **Show Delta** for the X/Y/Z components. **Esc** clears
the readouts. Ctrl+click also chains edges for a perimeter total.

---

## Per-part colours (baked into the STEP)

Set colours in the **CadQuery build**, not the viewer — that way they're written
into the STEP file and show up in any STEP viewer (FreeCAD, KiCad, online
viewers), with the model as the single source of truth. Pass `color=` to each
`cq.Assembly.add(...)`:

```python
import cadquery as cq
assy = (cq.Assembly()
    .add(carriage, name="carriage", color=cq.Color("slategray"))
    .add(motor,    name="motor",    color=cq.Color(0.84, 0.37, 0.23))  # floats 0..1
)
```

`cq.Color` only takes a colour *name* or floats 0..1. For hex strings or 0..255
values, use the shared helper `cq_colors.color()` (in this folder), which wraps
all of those:

```python
# at the top of <project>/src/build.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "freecad"))
from cq_colors import color

assy = (cq.Assembly()
    .add(carriage, name="carriage", color=color("#3a7bd5"))   # hex
    .add(motor,    name="motor",    color=color((210, 94, 58)))  # 0..255
    .add(rail,     name="rail",     color=color("slategray"))    # name
)
```

`color()` accepts: `"#rrggbb"` / `"#rgb"` / `"#rrggbbaa"`, an `(r,g,b)` or
`(r,g,b,a)` tuple in either 0..1 or 0..255, or an SVG/X11 colour name.

How the viewer treats colours:

- If the STEP carries **any** colours, the viewer shows them **exactly** and
  leaves uncoloured parts at the default grey — so it's obvious which parts you
  haven't assigned yet.
- If the STEP has **no** colours at all, the viewer falls back to an automatic
  high-contrast palette so the model still reads apart. (This is why
  not-yet-converted projects still look colourful.)

So to recolour a part: change the `color=` in the build and rebuild — the open
viewer reloads with the new colour, no clicks. Setting colours by hand in the
FreeCAD GUI won't stick, because the viewer reloads from the STEP on each build.

---

## Onshape is gone

Onshape has been fully removed from every CadQuery project — no `_push_onshape`,
no `tools/onshape_*`, no credentials, no `--no-push` flag. The build writing the
STEP (and calling `show()`) is the only "publish" step now. `banjo-wall-mount`
remains an Onshape-modelled project (not CadQuery) and is left alone.

---

## Requirements / notes

- FreeCAD 1.1 at `C:\Program Files\FreeCAD 1.1\bin\freecad.exe`
  (pass `-FreeCAD <path>` to the launcher if yours differs).
- Multi-part assemblies should be exported as a `cq.Assembly` with `name=`d
  components (the projects already do this) so each part gets a tidy named,
  toggleable tree row. Single-part projects show one object.
- The viewer polls the STEP file's mtime every 1 s; any process that rewrites
  the file triggers a reload.
- The viewer turns FreeCAD's auto-recovery off (`AutoSaveEnabled=False`) so an
  unclean exit (force-kill, crash, reboot) never shows the Document Recovery
  dialog — the tabs are disposable STEP imports with nothing to recover. (Global
  pref; flip it back in Edit → Preferences → General → Document if you ever edit
  real documents in this FreeCAD.)
