"""Publish the web-preview to the orphan `gh-pages` branch (force-push).

Regenerates docs/assembly.glb, then publishes the docs/ folder (index.html +
assembly.glb) to gh-pages as a SINGLE orphan commit that is force-pushed each
time. Because every publish REPLACES gh-pages with a parentless commit, the
~28 MB binary never accumulates in history — the old blob becomes unreferenced
and is reclaimed by git gc. `main` stays code-only.

  py -3.12 -m tools.publish_preview        # regen GLB + force-push gh-pages

A full `py -3.12 -m src.build` calls push_gh_pages() automatically (non-fatal).

ONE-TIME GitHub setup: Settings > Pages > Build and deployment > Source =
"Deploy from a branch", Branch = `gh-pages` / `(root)`. Until that toggle is
flipped Pages keeps serving docs/ from main; this script's push just pre-stages
the branch (harmless).

Guarded: only publishes from the `main` branch, so agent worktrees on agent/*
branches never publish. Set PSG_NO_PUBLISH=1 to skip entirely.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"


def _git(*args: str, env=None, check=True) -> str:
    r = subprocess.run(["git", *args], cwd=str(REPO), env=env,
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}\n{r.stderr.strip()}")
    return r.stdout.strip()


GITHUB_FILE_LIMIT = 100 * 2**20          # GitHub's hard per-file limit is 100 MiB


def _oversize(files):
    """[(path, bytes)] for every file GitHub would refuse."""
    return [(f, f.stat().st_size) for f in files if f.stat().st_size > GITHUB_FILE_LIMIT]


def _heaviest_families(glb, top=6):
    """Rank a binary glTF's parts by the geometry bytes they own, indices stripped.

    Sized from each ACCESSOR (count x component size x components). Not from its
    bufferView: the exporter packs every part into a few shared views, so a
    view's length is the whole buffer for all of them -- attributing that per part
    reports tens of gigabytes for a 100 MB file."""
    import collections, json, re, struct
    data = glb.read_bytes()
    jlen, _ = struct.unpack_from("<I4s", data, 12)
    g = json.loads(data[20:20 + jlen])
    acc, meshes, nodes = g["accessors"], g.get("meshes", []), g.get("nodes", [])
    cs = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
    fam, cnt = collections.Counter(), collections.Counter()
    for n in nodes:
        if "mesh" not in n:
            continue
        refs = set()
        for pr in meshes[n["mesh"]]["primitives"]:
            refs |= set(pr.get("attributes", {}).values())
            if "indices" in pr:
                refs.add(pr["indices"])
        f = re.sub(r"(_\d+)+$", "", n.get("name", "?"))
        fam[f] += sum(acc[a]["count"] * cs[acc[a]["componentType"]] * nc[acc[a]["type"]]
                      for a in refs)
        cnt[f] += 1
    return [(f, b, cnt[f]) for f, b in fam.most_common(top)]


def push_gh_pages(build_n: int | None = None, remote: str = "origin",
                  branch: str = "gh-pages") -> bool:
    """Force-push the current docs/ contents to `remote`/`branch` as one orphan
    commit. Returns True if pushed, False if skipped (opted out / not on main).
    Never touches the working tree, index, or HEAD (uses a throwaway index)."""
    if os.environ.get("PSG_NO_PUBLISH"):
        print("web preview: PSG_NO_PUBLISH set -> skip publish")
        return False
    cur = _git("rev-parse", "--abbrev-ref", "HEAD")
    if cur != "main":
        print(f"web preview: on '{cur}', not main -> skip publish")
        return False

    files = sorted(p for p in DOCS.iterdir() if p.is_file())
    if not files:
        print("web preview: docs/ is empty -> nothing to publish")
        return False

    # GitHub refuses any file over 100 MiB outright. Check BEFORE pushing: a doomed
    # push used to fail deep inside `git push`, and the caller's non-fatal wrapper
    # reported it as "publish skipped" -- so build #620's viewer silently stopped
    # updating while the build itself exited 0. Say exactly what is too big and what
    # is making it big, then skip the upload that cannot succeed.
    offenders = _oversize(files)
    if offenders:
        bar = "!" * 72
        print(bar)
        print("web preview: NOT PUBLISHED -- a file exceeds GitHub's 100 MiB limit:")
        for f, size in offenders:
            print(f"    {f.name}: {size / 2**20:.1f} MiB  (limit {GITHUB_FILE_LIMIT / 2**20:.0f} MiB)")
            if f.suffix == ".glb":
                for fam, b, k in _heaviest_families(f):
                    print(f"      {b / 2**20:7.2f} MiB  {fam} (x{k})")
        print("The gh-pages viewer is still showing the LAST published build.")
        print(bar)
        return False

    # A private index file so the real index / staged changes are untouched.
    idx = REPO / ".git" / "tmp-ghpages.index"
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    try:
        _git("read-tree", "--empty", env=env)
        for f in files:                                   # served at the branch root
            blob = _git("hash-object", "-w", "--", str(f), env=env)
            _git("update-index", "--add", "--cacheinfo",
                 f"100644,{blob},{f.name}", env=env)
        tree = _git("write-tree", env=env)
        msg = f"web preview{f' (build #{build_n})' if build_n else ''}"
        commit = _git("commit-tree", tree, "-m", msg, env=env)   # no -p => orphan
        _git("push", "--force", remote, f"{commit}:refs/heads/{branch}")
    finally:
        idx.unlink(missing_ok=True)
    print(f"web preview: force-pushed docs/ -> {remote}/{branch}"
          f"{f' (build #{build_n})' if build_n else ''}")
    return True


def main() -> None:
    from tools.export_glb import build_glb
    from tools.export_rig import build_rig
    build_glb()
    build_rig()
    push_gh_pages()


if __name__ == "__main__":
    main()
