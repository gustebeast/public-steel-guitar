"""Print the open work items, so a route launch cannot end in idling.

⚠ WHY THIS EXISTS. A ~30 minute route is dead time, and the failure it invites is not
forgetting that a backlog exists -- it is CHECKING THE ROUTE instead of working. The route
already notifies on completion, so polling it buys nothing and costs the whole window.

So this is chained onto every route launch:

    cd <worktree> && ( ...finish.py... & ) ; cd <worktree> && py -3.12 tools/next_work.py

⚠ THE SECOND `cd` IS NOT OPTIONAL. The shell's cwd resets between the chained halves,
so without it the reminder runs in the wrong worktree and dies with 'No such file' --
which is exactly how it failed the first time it was used.

The backlog then lands in the same tool output as the launch, which is read, rather than in
a prompt read once at the start. The rule that goes with it: the turn that launches a route
must also START the next item -- not name it, start it.

usage: next_work.py [n]        # n = how many open items to show (default 3)
"""
import os
import re
import sys

DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "docs", "bronner-work-items.md")


def items(path=DOC):
    """(title, body) for each '## ' section that is not the Done list."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return []
    out, title, body = [], None, []
    for line in text.split("\n"):
        if line.startswith("## "):
            if title is not None:
                out.append((title, "\n".join(body).strip()))
            title, body = line[3:].strip(), []
        elif title is not None:
            body.append(line)
    if title is not None:
        out.append((title, "\n".join(body).strip()))
    # "Done this session" is a record, not a backlog; so is anything handed to another agent
    return [(t, b) for t, b in out
            if not t.lower().startswith("done")
            and "not mine" not in t.lower()]


def main(argv):
    n = int(argv[1]) if len(argv) > 1 else 3
    todo = items()
    if not todo:
        print("next_work: no backlog found at %s" % DOC)
        return 1
    print("=" * 72)
    print(" WHILE THAT RUNS -- open items (%s)" % os.path.basename(DOC))
    print(" The route notifies when it finishes. Do NOT poll it; START one of these.")
    print("=" * 72)
    for t, b in todo[:n]:
        first = next((ln for ln in b.split("\n")
                      if ln.strip() and not ln.startswith("#")), "")
        first = re.sub(r"[*`]", "", first).strip()
        print("  %-52s" % t)
        if first:
            print("      %s" % first[:100])
    if len(todo) > n:
        print("  ... and %d more" % (len(todo) - n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
