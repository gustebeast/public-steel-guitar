"""PROOF that kept's tokens are not too loose (lead, 2026-11-23): an edit a result depends on must
change its key, or a stale part comes back with every gate green.

Since b98aef2 a nested `kept` call, a weak map and numpy's index helpers fingerprint by TOKEN.
That is only safe if what they stand for is still hashed some other way:
  - a nested kept(inner, x): the OUTER function reads `inner` (a global, or a module's attribute),
    so inner's code and the constants it reads are in the outer key;
  - a weak memo: the function that fills it on a miss is read by the code that reads the memo.
Each case writes small probe modules into a scratch folder inside this repo (project code, keyed
by content), fingerprints the outer function in a FRESH interpreter (as a real edit is seen: the
next build), edits the probe, fingerprints again, and asserts the key moved. The last cases
assert the opposite: a memo filling up while a build runs must NOT move a key -- a weak map or a
kept.Memo; a plain dict global is hashed by value and does move (the last case shows it).

    py -3.12 tools/check_kept_keys.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

INNER = '''
SCALE = {scale}


def inner(x):
    return x {op} SCALE
'''

OUTER_NAME = '''
from cadkit.kept import kept
from probe_inner import inner


def outer(x):
    return kept(inner, x) * 2
'''

OUTER_ATTR = '''
from cadkit.kept import kept
import probe_inner as I


def outer(x):
    return kept(I.inner, x) * 2
'''

OUTER_LOCAL_IMPORT = '''
from cadkit.kept import kept


def outer(x):
    from probe_inner import inner
    return kept(inner, x) * 2
'''

MEMO = '''
import weakref

from cadkit.kept import Memo

K = {k}
_M = {memo}


class Box:
    def __init__(self, v):
        self.v = v


def produce(o):
    return o.v {op} K


def get(o):
    key = {key}
    try:
        return _M[key]
    except KeyError:
        _M[key] = w = produce(o)
        return w


def outer(o):
    return get(o) + 1
'''

# a fresh interpreter: fingerprint `outer`, optionally after a memo has filled, print the key
PROBE = '''
import sys
sys.path.insert(0, {repo_parent!r}); sys.path.insert(0, {probe!r})
from cadkit import kept as K
import {mod} as M
args = {args}
print("KEY", K.fingerprint(M.outer, *args))
if {fill}:
    for v in range(50):                            # the memo fills, as a build would fill it
        M.get(M.Box(v)) if hasattr(M, "get") else None
    print("KEY", K.fingerprint(M.outer, *args))
'''


def _key(probe, mod, args="(3,)", fill=False):
    code = PROBE.format(repo_parent=os.path.dirname(REPO), probe=probe, mod=mod, args=args, fill=fill)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=REPO)
    keys = [ln.split()[1] for ln in r.stdout.splitlines() if ln.startswith("KEY ")]
    if not keys:
        raise RuntimeError("probe failed:\n" + r.stdout[-2000:] + r.stderr[-3000:])
    return keys


def _write(probe, name, text):
    with open(os.path.join(probe, name + ".py"), "w", encoding="utf-8", newline="") as fh:
        fh.write(textwrap.dedent(text))


def main() -> int:
    probe = tempfile.mkdtemp(prefix="_keyprobe_", dir=HERE)
    fails = []

    def check(what, before, after, want_change=True):
        moved = before != after
        ok = moved == want_change
        print(f"{'PASS' if ok else 'FAIL'}  {what}: key {'moved' if moved else 'unchanged'}"
              f" ({before[:10]} -> {after[:10]})", flush=True)
        if not ok:
            fails.append(what)

    try:
        for label, outer in (("outer reads inner by name", OUTER_NAME),
                             ("outer reads inner as a module attribute", OUTER_ATTR),
                             ("outer imports inner inside its body", OUTER_LOCAL_IMPORT)):
            _write(probe, "probe_outer", outer)
            _write(probe, "probe_inner", INNER.format(scale=1.0, op="+"))
            k0 = _key(probe, "probe_outer")[0]
            _write(probe, "probe_inner", INNER.format(scale=1.0, op="-"))      # inner's BODY
            k1 = _key(probe, "probe_outer")[0]
            check(f"nested kept, {label}: inner's body edited", k0, k1)
            _write(probe, "probe_inner", INNER.format(scale=2.0, op="-"))      # inner's CONSTANT
            k2 = _key(probe, "probe_outer")[0]
            check(f"nested kept, {label}: a constant inner reads edited", k1, k2)
            k3 = _key(probe, "probe_outer")[0]
            check(f"nested kept, {label}: nothing edited", k2, k3, want_change=False)

        box = "(M.Box(3),)"
        for label, memo, key in (("weak memo", "weakref.WeakKeyDictionary()", "o"),
                                 ("kept.Memo", "Memo()", "o.v")):
            def mk(k, op):
                return MEMO.format(k=k, op=op, memo=memo, key=key)
            _write(probe, "probe_memo", mk(1.0, "+"))
            k0 = _key(probe, "probe_memo", box)[0]
            _write(probe, "probe_memo", mk(1.0, "*"))                          # the producer's BODY
            k1 = _key(probe, "probe_memo", box)[0]
            check(f"{label}: its producing function's body edited", k0, k1)
            _write(probe, "probe_memo", mk(2.0, "*"))                          # a constant it reads
            k2 = _key(probe, "probe_memo", box)[0]
            check(f"{label}: a constant the producer reads edited", k1, k2)
            a, b = _key(probe, "probe_memo", box, fill=True)
            check(f"{label}: the memo fills while the process runs", a, b, want_change=False)
        # WHY kept.Memo exists: a plain dict memo is hashed by its contents, so it moves as it fills
        _write(probe, "probe_memo", MEMO.format(k=2.0, op="*", memo="{}", key="o.v"))
        a, b = _key(probe, "probe_memo", box, fill=True)
        check("plain dict memo (use kept.Memo): moves as it fills", a, b, want_change=True)
    finally:
        shutil.rmtree(probe, ignore_errors=True)

    print("ALL PASS" if not fails else f"{len(fails)} FAIL(S): " + "; ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
