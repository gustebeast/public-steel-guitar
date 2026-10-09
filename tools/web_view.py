"""The web viewer, LOCALLY: your part fresh, the surroundings from the scratch cache.

    py -3.12 -m tools.web_view                 # export, start the server if needed, open the page
    py -3.12 -m tools.web_view --cache-only    # the cached surroundings alone (seconds)
    py -3.12 -m tools.web_view --serve         # just the server, in the foreground
    py -3.12 -m tools.web_view --rig           # also refresh the animation rig

It is the same page GitHub Pages serves (docs/index.html), reading a model written to
.webview/ instead of docs/. The page watches .webview/stamp.json and reloads the model
when it changes, keeping the camera and whatever is hidden, so the loop is: edit, run
this, look. An edit to the page itself (docs/index.html) reloads the open page the same
way: nobody presses reload.

WHAT IT READS. The surroundings are the scratch cache (.scratch_cache/*.brep, written
by `tools.scratch_view --start`); the part under work is built fresh from your scope,
exactly as the scratch view does it. Each cached solid's MESH is kept in
.webview/mesh/, keyed on the solid file's size and time, so a second run meshes only
what changed. Like the scratch cache this is for LOOKING: no gate reads it.

Colours come from src.build._color_for, which costs the build module's import (over a
minute), so they are remembered per part name in .webview/colors.json and only an
unknown name pays for it.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import pathlib
import pickle
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS = ROOT / "docs"
OUT = ROOT / ".webview"
CACHE = ROOT / ".scratch_cache"
PORT = 8137
# what the server takes from .webview/ in preference to docs/
MODEL_FILES = ("assembly.glb", "assembly.geo.json", "rig.json", "stamp.json")


# ── the server ────────────────────────────────────────────────────────────────────
class _Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        name = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if name in MODEL_FILES and (OUT / name).exists():
            return str(OUT / name)
        return super().translate_path(path)

    def do_GET(self):
        # when the PAGE itself was last edited: the open page reloads itself on a change
        if self.path.split("?", 1)[0] == "/page.json":
            body = json.dumps({"t": (DOCS / "index.html").stat().st_mtime_ns}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def serve(port=PORT):
    handler = functools.partial(_Handler, directory=str(DOCS))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("web view: http://127.0.0.1:%d/   (model from %s)" % (port, OUT.name))
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def _listening(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_server(port=PORT):
    if _listening(port):
        return False
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([sys.executable, str(pathlib.Path(__file__).resolve()),
                      "--serve", "--port", str(port)],
                     cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)
    for _ in range(40):
        if _listening(port):
            return True
        time.sleep(0.1)
    raise SystemExit("web view: the server did not come up on port %d" % port)


# ── the export ────────────────────────────────────────────────────────────────────
def _colors(names):
    """{name: (r, g, b, a)}, remembered between runs; the build module is imported
    only when a name is new."""
    path = OUT / "colors.json"
    known = json.loads(path.read_text()) if path.exists() else {}
    missing = [n for n in names if n not in known]
    if missing:
        print("web view: %d part(s) with no remembered colour -- importing the build "
              "module for them (about a minute, once)" % len(missing))
        import importlib
        color_for = importlib.import_module("src.build")._color_for
        for n in missing:
            try:
                known[n] = list(color_for(n).toTuple())
            except Exception:
                known[n] = [0.8, 0.8, 0.8, 1.0]
        path.write_text(json.dumps(known))
    return {n: tuple(known[n]) for n in names}


def _cached_mesh(brep, taken, whole):
    """[(piece name, mesh)] of a cached part (web_export.pieces says when a part is
    several), itself cached on the file's size and time."""
    import cadquery as cq
    from tools.web_export import mesh_shape, pieces, TOLERANCE, ANGULAR, FORMAT
    st = brep.stat()
    key = (st.st_size, st.st_mtime_ns, TOLERANCE, ANGULAR, FORMAT, "pieces", brep.stem in whole)
    f = OUT / "mesh" / (brep.stem + ".pkl")
    if f.exists():
        try:
            k, m = pickle.loads(f.read_bytes())
            if k == key:
                return m
        except Exception:
            pass
    m = [(n, mesh_shape(s)) for n, s in
         pieces(brep.stem, cq.Shape.importBrep(str(brep)).wrapped, taken, whole)]
    m = [(n, x) for n, x in m if x is not None]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(pickle.dumps((key, m), protocol=pickle.HIGHEST_PROTOCOL))
    return m


def _piece(brep, name):
    import cadquery as cq
    from tools.web_export import pieces
    return dict(pieces(brep.stem, cq.Shape.importBrep(str(brep)).wrapped))[name]


def export_local(live=True, rig=False):
    from tools.web_export import export, mesh_shape, pieces, rig_names, _topods
    if not (CACHE / "STAMP").exists():
        raise SystemExit("web view: no scratch cache. Begin a flow first:\n"
                         "  py -3.12 -m tools.scratch_view --start")
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    live_parts, replaced = [], ()
    if live:
        try:
            from tools.scratch_view import VIEW
        except SystemExit as exc:              # no scope claimed: cached surroundings only
            print("web view: %s\n          showing the cached surroundings alone" % exc)
        else:
            live_parts = list(VIEW.live_parts())
            replaced = tuple(VIEW.replaced)
            if VIEW.pose:
                live_parts = [(n, VIEW.pose(n, w)) for n, w in live_parts]
    mine = {n for n, _ in live_parts}
    breps = [f for f in sorted(CACHE.glob("*.brep"))
             if f.stem not in mine and not (replaced and f.stem.startswith(replaced))]
    meshed, solids, base = {}, {}, {}             # base: a piece's part, for its colour
    taken = {f.stem for f in breps} | mine
    whole = rig_names(OUT / "rig.json") | rig_names(DOCS / "rig.json")
    for f in breps:
        for n, m in _cached_mesh(f, taken, whole):
            meshed[n], base[n] = m, f.stem
            solids[n] = (lambda p=f, k=n: _piece(p, k))
    for part, w in live_parts:
        for n, s in pieces(part, _topods(w), taken, whole):
            m = mesh_shape(s)
            if m is not None:
                meshed[n], base[n], solids[n] = m, part, s
    cols = _colors(sorted(set(base.values())))
    age = (time.time() - float((CACHE / "STAMP").read_text())) / 60.0
    export([(n, solids[n], cols[base[n]]) for n in meshed], OUT, meshed=meshed)
    if rig or not (OUT / "rig.json").exists():
        try:
            import tools.export_rig as ER
            ER.RIG = OUT / "rig.json"
            ER.build_rig()
        except Exception as exc:
            print("web view: no animation rig (%s) -- the page shows the model still" % exc)
    stamp = {"t": time.time(), "live": sorted(mine), "cache_age_min": round(age, 1),
             "parts": len(meshed)}
    (OUT / "stamp.json").write_text(json.dumps(stamp))
    print("web view: %d parts (%d fresh, surroundings %.0f min old) in %.1f s"
          % (len(meshed), len(mine), age, time.time() - t0))


def main(argv=None):
    ap = argparse.ArgumentParser(description="the web viewer, locally")
    ap.add_argument("--serve", action="store_true", help="run the server and nothing else")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--cache-only", action="store_true",
                    help="do not build the part under work: cached surroundings alone")
    ap.add_argument("--rig", action="store_true", help="refresh the animation rig as well")
    ap.add_argument("--no-open", action="store_true", help="do not open a browser tab")
    a = ap.parse_args(argv)
    if a.serve:
        serve(a.port)
        return 0
    export_local(live=not a.cache_only, rig=a.rig)
    started = ensure_server(a.port)
    url = "http://127.0.0.1:%d/" % a.port
    print("web view: %s%s" % (url, "" if started else "   (already open pages reload themselves)"))
    if started and not a.no_open:
        import webbrowser
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
