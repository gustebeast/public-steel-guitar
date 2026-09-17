"""Checks a netlist must pass that nothing else in this pipeline can see.

⚠ EVERY CHECK IN HERE EXISTS BECAUSE A REAL FAULT GOT PAST EVERY OTHER ONE. DRC compares
copper against the netlist, so it is blind to anything wrong IN the netlist; ERC checks
pin drive types, so it is blind to topology; the router routes whatever it is handed.
A netlist that is internally consistent and describes a board that cannot work passes
all three in silence.
"""
import os
import re


def grounds_meet(path, declared_split=None):
    """Every return net must actually reach the others.

    ⚠ TWO GROUND NETS THAT NEVER MEET IS INVISIBLE TO THIS WHOLE PIPELINE. Each net is
    internally connected, so the ratsnest is empty and DRC is silent; the router routes
    both without complaint; ERC sees two power nets, each properly driven; the fab builds
    exactly what it was sent. The board does not work and the first evidence is a bench.

    Found on the OPTICAL board 2026-09-17: PWR_GND carried the buck, the 24 V inlet and
    the emitter switch; GND carried every load; no component in the netlist had a pin on
    both, so the buck's return path to its own loads was open. Then found again
    immediately on the OUTPUT PANEL, which is why this lives in a shared module instead
    of in the board that happened to be looked at first.

    A deliberate split PASSES, as long as it is finished: a net tie or a 0R is a
    component with a pin on each net, so the two land in one group. A split with nothing
    between them does not.

    ⚠ `declared_split` IS FOR A SPLIT THE BOARD MEANS AND CANNOT CLOSE ON ITS OWN, and
    it is deliberately awkward to use: it takes the reason, it must name the groups
    exactly, and it PRINTS on every run. The output panel is the case it exists for --
    its 24 V return is chopped by ten stepper drivers and it keeps that off the audio
    reference on purpose, intending the two to meet "at the instrument's star point".
    Turning that into a build failure would be wrong; letting it pass in silence would
    be worse, because a star point that is documented and does not exist is still an
    open return. The board states the claim, the check repeats it out loud, and whoever
    reads the build output can go and check that the star point is real.
    """
    txt = open(path, encoding="utf-8").read()
    of_net, by_part = {}, {}
    for blk in re.finditer(r'\(net\s+\(code \d+\)\s+\(name "([^"]+)"\).*?'
                           r'(?=\(net\s+\(code|\Z)', txt, re.S):
        for ref, _pin in re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)',
                                    blk.group(0)):
            of_net.setdefault(blk.group(1), set()).add(ref)
            by_part.setdefault(ref, set()).add(blk.group(1))
    grounds = sorted(n for n in of_net
                     if re.fullmatch(r"(GND|VSS|[A-Z0-9]+_GND|[AD]GND)", n))
    if len(grounds) < 2:
        return len(grounds)
    par = {g: g for g in grounds}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for nets in by_part.values():
        touched = [n for n in nets if n in par]
        for other in touched[1:]:
            par[find(other)] = find(touched[0])
    groups = {}
    for g in grounds:
        groups.setdefault(find(g), []).append(g)
    if len(groups) != 1:
        shape = " | ".join("+".join(sorted(v)) for v in sorted(
            groups.values(), key=lambda v: sorted(v)))
        if declared_split and declared_split.get("shape") == shape:
            print("  !! %s: return nets DELIBERATELY SPLIT (%s) -- %s"
                  % (os.path.basename(path), shape, declared_split["why"]))
            return len(grounds)
        raise AssertionError(
            "%s: the return nets do not all meet -- %s. Each group is internally "
            "connected, so DRC, the router and the ratsnest will all be silent and the "
            "board will not work. Join them with a net tie or a 0R (a component with a "
            "pin on each), or make them one net."
            % (path, " | ".join("+".join(sorted(v)) for v in groups.values())))
    return len(grounds)


def classify_violations(drc_json, declared):
    """Split DRC violations into the ones a board DECLARES and the rest.

    ⚠ A COUNT IS NOT A CHECK, AND THIS EXISTS BECAUSE I PROVED THAT ON MYSELF. The
    optical board declares twenty courtyard overlaps -- an emitter between its own two
    photodiodes, ten times -- and for weeks the pipeline reported "20 violations" and
    everyone, including me, read that as "the expected ones". Then a hand placement put
    a capacitor across the MCU's courtyard and two test pads, the report said 23, and
    the only reason it was caught was that somebody happened to list them.

    THE DECLARATION IS BY SHAPE, NOT BY NUMBER. `declared` is a predicate taking the
    sorted pair of footprint references; a violation it accepts is expected however many
    there are, and a violation it rejects is a fault even if the total is unchanged. A
    twenty-first triplet overlap is fine; a first C112/U6 overlap is not, and counting
    cannot tell them apart.
    """
    import re as _re
    ok, bad = [], []
    for v in drc_json.get("violations", []):
        refs = tuple(sorted(_re.sub(r"^Footprint ", "", i.get("description", ""))
                            for i in v.get("items", [])))
        (ok if declared(v.get("type"), refs) else bad).append((v.get("type"), refs))
    return ok, bad


def optical_declared(vtype, refs):
    """The optical board's sensing cell: an IR emitter between its own two detectors.

    Declared because it cannot be loosened -- PD_DY is an optical parameter before it is
    a placement one, and widening it would let the cover shade the detectors it exists to
    protect. Measured: courtyards overlap 0.390 mm, BODIES clear by 0.350 and copper by
    0.200, against a 0.127 rule. Only this shape, and only between a D and its OWN PDs.
    """
    import re as _re
    if vtype != "courtyards_overlap" or len(refs) != 2:
        return False
    m = [_re.fullmatch(r"(D|PD)(\d+)([AB]?)", r) for r in refs]
    if not all(m):
        return False
    kinds = {x.group(1) for x in m}
    return kinds == {"D", "PD"} and m[0].group(2) == m[1].group(2)
