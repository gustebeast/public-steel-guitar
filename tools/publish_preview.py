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
    build_glb()
    push_gh_pages()


if __name__ == "__main__":
    main()
