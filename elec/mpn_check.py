"""Does the CAD's sourcing table still agree with the netlist?

⚠ THE TWO HALVES OF THIS PROJECT NAME THE SAME PART TWICE AND NOTHING MADE THEM AGREE.
`src/optical_pickup.py` carries an MPN table so the CAD can price and envelope what it
places; `elec/optical.py` carries the part again so the netlist and the fab BOM can name
it. They are edited on different days for different reasons, and when they drift apart
the BOARD is right and the BOM is wrong -- which is the expensive direction, because the
BOM is what gets ordered.

Found on 2026-09-17, by running this for the first time:

  D8, D9   The CAD's exact-ref table had D8 and D9 as an output-panel relay flyback and
           an output clamp, both OPEN. On THIS board D8 and D9 are IR EMITTERS. The
           exact-ref table exists precisely because reference designators are not a
           clean namespace -- and then it collided across BOARDS instead of within one.
           Two of the ten emitters would have been quoted as unresolved SOD-523 diodes.

  Y1, Y2   Both still mapped to X322525MSB4SI (C13740), the 25 MHz part the 2026-09-17
           datasheet audit REPLACED: Y1 is TX322525M4LBDD2T and Y2 is K3A260002010, a
           26 MHz part with the ESR the USB334x requires. The audit fixed the netlist
           and left the CAD table saying "confirm vs USB3343".

Neither is visible to DRC, to the netlist checks, or to the CAD's own asserts, because
each file is internally consistent. Only the comparison sees it.

Usage:  py -3.12 elec/mpn_check.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import fab                                      # noqa: E402  (the value -> LCSC table)
from src import optical_pickup as cad           # noqa: E402


def netlist_codes(stem):
    """ref -> (value, LCSC code or None) as the FAB will read it."""
    txt = open(stem + ".net", encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'\(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', txt):
        out[m.group(1)] = (m.group(2), fab.LCSC.get(m.group(2)))
    return out


def main():
    stem = os.path.join(HERE, "out", "optical")
    if not os.path.isfile(stem + ".net"):
        raise SystemExit("no %s.net -- generate the netlist first" % stem)
    net = netlist_codes(stem)
    bad = []
    for p in cad.PARTS:
        ref = p["ref"]
        if ref not in net:
            continue                            # modelled but not on this schematic
        val, net_code = net[ref]
        rec = cad.mpn(p)
        cad_code = rec[1] or None
        if cad_code == "BASIC":
            continue                            # a generic passive class, priced not sourced
        if net_code is None and cad_code is None:
            continue                            # both say open
        if net_code != cad_code:
            bad.append((ref, rec[0], cad_code, val, net_code))
    if not bad:
        print("optical: CAD sourcing table agrees with the netlist (%d parts)" % len(net))
        return 0
    print("optical: %d part(s) where the CAD and the netlist name DIFFERENT parts\n" % len(bad))
    print("  %-5s %-22s %-10s %-22s %s" % ("ref", "CAD says", "code", "netlist says", "code"))
    for ref, cm, cc, nv, nc in bad:
        print("  %-5s %-22s %-10s %-22s %s" % (ref, cm, cc or "-", nv, nc or "-"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
