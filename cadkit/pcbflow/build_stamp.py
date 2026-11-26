"""A board's build stamp: what it was built FROM, by content hash, so a check run on it can say
when those inputs have moved on (no pcbnew; layout, eco, quality, finish and rasterpath use it).

    stamp(stem)         write <stem>.build.json at layout time: the hashes of inputs(stem)
    restamp(stem, key)  a later build step rewrote one input (eco.py: the notes) -- take its new hash
    check(stem, say)    compare; say a loud STALE BOARD / UNSTAMPED BOARD line. Returns
                        "current" | "stale" | "unstamped"

The inputs, each by sha256 of its bytes (never mtime -- a sync or checkout touches mtimes and a
copy keeps none):
    source    the board's generator, elec/<name>.py, when the stem sits in elec/out/ (or
              $PCBFLOW_SOURCE names it)
    notes     <stem>.board.json        net   <stem>.net
    intent    <dir>/flow/intent.json   (a place_flow board)
    pcbflow   every pcbflow/*.py, hashed together -- the tool the board was built with

⚠ WHY (lead 2026-11-25): an A34 audit ran on elec/out boards laid out 2026-10-07 .. 11-01
against generators last changed 11-24, and reported lever_sensor's R3 / R4 0.32 from SW1 --
a placement the source no longer had (R3 had moved ~20 mm). Nothing said the boards were old.
"""
import glob
import hashlib
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return None


def _tree():
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        if os.path.basename(p).startswith("test_"):
            continue
        h.update(os.path.basename(p).encode())
        with open(p, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()[:16]


def _source(stem):
    env = os.environ.get("PCBFLOW_SOURCE")
    if env:
        return os.path.abspath(env)
    d, name = os.path.split(os.path.abspath(stem))
    if os.path.basename(d).lower() == "out":
        p = os.path.join(os.path.dirname(d), name + ".py")
        if os.path.isfile(p):
            return p
    return None


def inputs(stem):
    """{key: [path, sha]} for every input this board has."""
    out = {}
    src = _source(stem)
    if src:
        out["source"] = [src, _sha(src)]
    for key, ext in (("notes", ".board.json"), ("net", ".net")):
        if os.path.isfile(stem + ext):
            out[key] = [stem + ext, _sha(stem + ext)]
    it = os.path.join(os.path.dirname(os.path.abspath(stem)), "flow", "intent.json")
    if os.path.isfile(it):
        out["intent"] = [it, _sha(it)]
    out["pcbflow"] = [HERE, _tree()]
    return out


def stamp(stem):
    rec = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "inputs": inputs(stem)}
    with open(stem + ".build.json", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return rec


def restamp(stem, key):
    """A build step after layout rewrote input `key` itself (eco.py writes the notes): the
    stamp takes its new hash, so the step's own write is not read as the board going stale."""
    try:
        rec = json.load(open(stem + ".build.json", encoding="utf-8"))
    except (OSError, ValueError):
        return None
    now = inputs(stem)
    if key in now:
        rec["inputs"][key] = now[key]
        rec.setdefault("restamped", []).append([key, time.strftime("%Y-%m-%d %H:%M:%S")])
        with open(stem + ".build.json", "w", encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)
    return rec


def check(stem, say=print):
    name = os.path.basename(stem)
    try:
        rec = json.load(open(stem + ".build.json", encoding="utf-8"))
    except (OSError, ValueError):
        say(" !! UNSTAMPED BOARD: %s has no build stamp (%s.build.json) -- it was laid out before "
            "stamps, so nothing here can say it matches its source. Re-run its flow before "
            "trusting a finding on it." % (name, name))
        return "unstamped"
    was, now = rec.get("inputs", {}), inputs(stem)
    moved = [k for k in now if k in was and was[k][1] != now[k][1]]
    gone = [k for k in was if k not in now and k != "pcbflow"]
    if not moved and not gone:
        return "current"
    parts = ["%s (%s)" % (k, os.path.basename(now[k][0]) if k != "pcbflow" else "cadkit pcbflow")
             for k in moved] + ["%s (missing)" % k for k in gone]
    only_tool = moved == ["pcbflow"] and not gone
    say(" !! STALE BOARD: %s was built %s from inputs that have changed since: %s. %s"
        % (name, rec.get("built", "?"), ", ".join(parts),
           "Only the tool moved: findings from a rule that changed may differ on a rebuild."
           if only_tool else "Its findings describe an OLD board -- re-run its flow first."))
    return "stale"
