"""Module-level code nothing calls -- the drift the other checkers cannot see.

    py -3.12 -m tools.check_dead            # report
    py -3.12 -m tools.check_dead --baseline # rewrite the allow-list below

Geometry gates measure the MODEL. Nothing measured the SOURCE, so retired parts left
their builders behind: when the electronics tray, the Teensy and the CAN tees moved,
nine functions and a gate rule stayed, still compiling, still read by the next person
as if they were live. This finds a definition no name in the repo mentions again.

A name counts as USED if it appears anywhere outside its own `def` line -- any .py in
src/tools/elec/cadkit, any .md, any .json. That deliberately over-counts: string
dispatch (build.py names parts as text), an agent scope registered by name, and a
symbol only a doc mentions all read as live. A DEAD verdict therefore means nothing
in the project refers to it at all, which is a strong claim, not a style opinion.

Exit code = how many dead definitions are NOT in KNOWN below, so a checker run fails
only when the count GROWS. Deliberate exceptions (re-export facades, entry points a
tool calls by path) belong in KNOWN with the reason written down.
"""
import ast
import os
import re
import sys

# Where DEFINITIONS are judged. cadkit is deliberately absent: it is vendored into ten
# projects, so a helper unused HERE may be the only thing another project calls. Its
# text is still read for USES below.
DEF_ROOTS = ("src", "tools", "elec")
USE_ROOTS = DEF_ROOTS + ("cadkit",)
TEXT_EXT = (".py", ".md", ".json")

# Definitions that are unreferenced ON PURPOSE. Each one needs its reason, because the
# next person to read this list has to be able to tell a facade from a leftover.
KNOWN = {
    # AGENT SCOPE ENTRY POINTS. agent_sync registers a scope by dotted path, and that
    # registry lives in .git/agent-sync/scopes.json -- outside every file this scans, so
    # a live scope reads as dead. Deleting one silently un-scopes an agent's branch.
    "lever_components": "src/build.py -- scope entry point (agent_sync scopes.json)",
    "lkl_vkl_components": "src/build.py -- scope entry point, branner's levers round",
    "body_work_components": "src/build.py -- scope entry point, bronner",
    "pedal_bar_work_components": "src/build.py -- scope entry point, branner",
}


def _sources():
    out = []
    for root in USE_ROOTS:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
            for f in filenames:
                if f.endswith(TEXT_EXT):
                    out.append(os.path.join(dirpath, f))
    for f in os.listdir("."):
        if f.endswith(".md"):
            out.append(f)
    return out


def scan():
    """[(path, lineno, name)] for every module-level def nothing else mentions."""
    files = _sources()
    text = {}
    for p in files:
        with open(p, encoding="utf-8", errors="replace") as fh:
            text[p] = fh.read()
    defs = []
    for p, src in text.items():
        if not p.endswith(".py") or not p.startswith(DEF_ROOTS):
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as e:                     # a broken file is not our report
            print(f"  (skipped {p}: {e})")
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs.append((p, node.lineno, node.name))
    dead = []
    for p, lineno, name in defs:
        pat = re.compile(r"\b%s\b" % re.escape(name))
        if sum(len(pat.findall(s)) for s in text.values()) <= 1:
            dead.append((p, lineno, name))
    return sorted(dead)


def main():
    dead = scan()
    new = [d for d in dead if d[2] not in KNOWN]
    if "--baseline" in sys.argv:
        for p, lineno, name in dead:
            print(f'    "{name}": "{p}:{lineno} -- WHY it stays",')
        return 0
    for p, lineno, name in new:
        print(f"  DEAD  {p}:{lineno}  {name}() -- nothing in the repo names it")
    kept = len(dead) - len(new)
    print(f"check_dead: {len(new)} unreferenced definition(s)"
          + (f", {kept} allow-listed" if kept else ""))
    return len(new)


if __name__ == "__main__":
    sys.exit(main())
