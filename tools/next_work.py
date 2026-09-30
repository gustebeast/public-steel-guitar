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


# ⚠ A COMPLETED ITEM PRINTED AS A TODO IS WORSE THAN NO TOOL AT ALL, and this one did it
# for weeks. The filter below used to remove exactly two things -- a title starting "done"
# and a title saying "not mine" -- while THIS doc marks completion with a tick, or with
# BUILT / CLOSED / LANDED / FINISHED, or by moving a section under a HISTORICAL banner. So
# the top three "open items" it printed were the bring-up pads (in, 0 unconnected), the
# converter isolation (BUILT) and a routing-speed note that had been acted on. Every tick
# read that list, and the tick prompts themselves grew stale items out of it.
# ⚠ AND IT NEVER READ THE STATE TABLE, which is where this doc's truth actually lives. The
# "## " sections are the narrative record; the table at the top is the state. A backlog
# tool that reads only the narrative is reading the history and calling it a plan.
DONE_MARKS = ("✅", "BUILT", "CLOSED", "LANDED", "FINISHED", "SUPERSEDED",
              "REVERTED", "HISTORICAL", "DO NOT RE-ISSUE", "NOT MINE", "RETIRED")
# these are PHRASES, not words, and that is deliberate. "BLOCKED" on its own matched the
# row that says "not a BLOCKED corridor" -- a sentence explaining what the problem is NOT,
# reported as an open item. A marker short enough to appear inside ordinary prose will.
OPEN_MARKS = ("STILL OPEN", "NOT STARTED", "NOT LANDED", "NOT BUILT", "BLOCKED ON",
              "FOLLOW-UP", "TODO", "IS A REGRESSION", "STILL A REGRESSION")


def _done(title, body):
    """Is this section a record of finished work rather than a task?

    The title decides; the body only decides when its FIRST non-empty line carries the
    mark, because a completion marker buried in paragraph nine is usually describing a
    sub-part rather than the section."""
    t = title.upper()
    # ~~struck through~~ is this doc's other way of saying done, and "DONE" turns up in the
    # MIDDLE of a title as often as at the start ("~~motor_ctrl~~ -- DONE, with the LED
    # buck"), so neither a prefix test nor the tick alone is enough.
    if "~~" in title or "DONE" in t or "NOT MINE" in t:
        return True
    # ⚠ ANOTHER AGENT'S NAME IN THE TITLE IS A HANDOFF, and this doc writes it as "(brenner)"
    # rather than the "not mine" the old filter looked for. Three agents share this repo and
    # only one of them is bronner; printing brenner's pi_cap brief as bronner's next task is
    # how two agents end up editing the same file from opposite ends.
    if any(("(%s)" % other).upper() in t for other in ("brenner", "branner")):
        return True
    # this doc states completion numerically too, and that phrasing is unambiguous here:
    # a board still open says "3 unconnected", never "0 unconnected".
    if "0 UNCONNECTED" in t:
        return True
    if any(m in t for m in DONE_MARKS):
        return True
    first = next((ln for ln in body.split("\n") if ln.strip()), "").upper()
    return any(m in first for m in DONE_MARKS)


def table_rows(text):
    """Rows of the current-state table that still describe something OPEN.

    The table is `| thing | state |`. A row counts as open when its state cell SAYS SO IN
    WORDS -- never merely because it carries a warning sign, which this doc uses for
    emphasis on finished work at least as often as on unfinished."""
    out = []
    for line in text.split("\n"):
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in ("thing", ""):
            continue
        state = cells[1].upper()
        if any(m in state for m in DONE_MARKS):
            continue
        if any(m in state for m in OPEN_MARKS):
            out.append((cells[0], cells[1]))
    return out


def items(path=DOC):
    """(open sections, open table rows, how many sections were hidden as complete)."""
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return [], [], 0
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
    keep = [(t, b) for t, b in out if not _done(t, b)]
    # ⚠ THE HIDDEN COUNT IS PRINTED, NOT SWALLOWED. This repo has been bitten twice by a
    # filter that removed more than its author meant -- gating optical's repairs by net
    # name nearly deleted fifteen working pieces of copper -- so this one says how much it
    # took. If that number is ever most of the backlog, the markers are wrong, not the doc.
    return keep, table_rows(text), len(out) - len(keep)


def main(argv):
    n = int(argv[1]) if len(argv) > 1 else 3
    todo, open_rows, hidden = items()
    if not todo and not open_rows:
        print("next_work: no OPEN items at %s" % DOC)
        print("           (%d section(s) read, all marked complete)" % hidden)
        return 1
    print("=" * 72)
    print(" WHILE THAT RUNS -- open items (%s)" % os.path.basename(DOC))
    print(" The route notifies when it finishes. Do NOT poll it; START one of these.")
    print("=" * 72)
    if open_rows:
        print(" FROM THE STATE TABLE -- the current truth, not the narrative:")
        for thing, state in open_rows[:n]:
            state = re.sub(r"[*`]", "", state).strip()
            print("   * %-26s %s" % (thing[:26], state[:86]))
        print("")
    for t, b in todo[:n]:
        first = next((ln for ln in b.split("\n")
                      if ln.strip() and not ln.startswith("#")), "")
        first = re.sub(r"[*`]", "", first).strip()
        print("  %-52s" % t)
        if first:
            print("      %s" % first[:100])
    if len(todo) > n:
        print("  ... and %d more section(s)" % (len(todo) - n))
    if hidden:
        print("  (%d section(s) hidden as already complete)" % hidden)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
