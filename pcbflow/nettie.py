"""nettie.py -- what a net tie is, for every reader of a board's nets.

A net tie (ref NT<n>: the Kelvin sense ties of 2026-11-20, NT11 / NT12 / NT205 ...) is copper,
not a part. The nets on its two sides are one conductor at one voltage, and it has no rating
of its own. Two readers need exactly that and once disagreed:

  quality A16 (5b2cdbd) walked ties so PB_VCC_K inherited PB_VCC's declared voltage, while
  elec/voltage_check.py did not -- PA_VCC_K read 0 V there, U13.23's "VCC+4" rating resolved
  to 4 V, and --declare wrote it into volts/brain_board.json (brain_board, 2026-11-22).

So both ask this module, and test_nettie.py pins the answer:

    is_net_tie(ref)              NT followed by a digit (NTC1, a thermistor, is not one)
    tie_groups(tie_nets)         {net: frozenset of every net joined to it through ties}
"""
import re

_NET_TIE = re.compile(r"NT\d")


def is_net_tie(ref):
    """True for a net tie's reference designator."""
    return bool(_NET_TIE.match(ref or ""))


def tie_groups(tie_nets):
    """{net: frozenset(joined nets)} from {tie ref: [nets on its pads]}; only refs that are net ties
    count, and a chain of ties is one group. A net on no tie is absent."""
    up = {}

    def f(a):
        up.setdefault(a, a)
        while up[a] != a:
            up[a] = up[up[a]]
            a = up[a]
        return a
    for ref, nets in tie_nets.items():
        nets = [n for n in nets if n]
        if not is_net_tie(ref) or not nets:
            continue
        for n in nets[1:]:
            up[f(n)] = f(nets[0])
        f(nets[0])
    groups = {}
    for n in up:
        groups.setdefault(f(n), set()).add(n)
    return {n: frozenset(groups[f(n)]) for n in up}
