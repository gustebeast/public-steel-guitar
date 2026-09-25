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


# The BOM's "Package" column is prose, so it is compared through a small table of what
# each spelling MEANS as a footprint-name fragment. Anything not listed is skipped rather
# than guessed -- a check that cries wolf gets switched off.
BOM_PKG = {
    "LQFP176": "LQFP-176", "USB-C": "USB_C_Receptacle", "XH-SM-4": "JST_XH_S4B-XH-SM4",
    "SOIC-14": "SOIC-14", "QFN-24": "HVQFN-24", "SOT-223": "SOT-223",
    "SOT-23-5": "SOT-23-5", "SOT-23-6": "SOT-23-6", "SOT-23": "SOT-23",
    "SOT-563": "SOT-563", "3225": "Crystal_SMD_3225", "4040": "L_Sunlord_SWPA40", "RNX-12": "Texas_RNX0012",
    "0402": "_0402_", "0603": "_0603_", "0805": "_0805_", "1206": "_1206_",
    "0805 (opto)": "_0805_",
}


def bom_packages(path):
    """ref -> the package BOM.md's optical table claims, keyed on each row's FIRST ref."""
    lines = open(path, encoding="utf-8").read().split(chr(10))
    i = next(k for k, l in enumerate(lines) if l.startswith("| Qty | Ref | Part / role"))
    out = {}
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        c = [x.strip() for x in l.split("|")]
        if len(c) < 6:
            continue
        first = re.split(r"[,/ ]", c[2].replace(chr(0x2013), "-"))[0].split("-")[0]
        if first:
            out[first] = c[4]
    return out


def netlist_footprints(stem):
    """ref -> footprint name, without the library prefix."""
    txt = open(stem + ".net", encoding="utf-8").read()
    return {m.group(1): m.group(2).split(":", 1)[-1] for m in re.finditer(
        r'\(ref "([^"]+)"\)\s*\(value "[^"]*"\)\s*'
        r'\(description "[^"]*"\)\s*\(footprint "([^"]*)"\)', txt)}


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
        if cad_code == "NONE":
            # Bare copper -- a test pad or a net tie. The CAD places it because it takes
            # board area; the fab never sees it because there is no part to source. Both
            # halves agreeing that there is nothing to order IS agreement.
            continue
        if net_code is None and cad_code is None:
            continue                            # both say open
        if net_code != cad_code:
            bad.append((ref, rec[0], cad_code, val, net_code))
    # ⚠ AND BOM.md'S PACKAGE COLUMN, which is the THIRD place every part is described
    # and the only one a human reads. Two rows were wrong on 2026-09-17: U8 said
    # SOT-23-5 when the AMS1117 is a SOT-223 tab package nearly twice the size, and U10
    # said SOT-563 when the part ordered is SOT-23-6. Nothing else could see either --
    # the CAD and the netlist agreed with each other, and only the prose disagreed.
    fps = netlist_footprints(stem)
    pkg_bad = []
    for ref, want in bom_packages(os.path.join(ROOT, "BOM.md")).items():
        key = BOM_PKG.get(want)
        if ref in fps and key and key not in fps[ref]:
            pkg_bad.append((ref, want, fps[ref]))

    if not bad and not pkg_bad:
        print("optical: CAD table, netlist and BOM.md all agree (%d parts)" % len(net))
        return 0
    if pkg_bad:
        print("optical: %d BOM.md row(s) whose package is not the footprint" % len(pkg_bad))
        for ref, want, got in pkg_bad:
            print("  %-5s BOM says %-14s footprint is %s" % (ref, want, got))
        print()
    if not bad:
        return 1
    print("optical: %d part(s) where the CAD and the netlist name DIFFERENT parts\n" % len(bad))
    print("  %-5s %-22s %-10s %-22s %s" % ("ref", "CAD says", "code", "netlist says", "code"))
    for ref, cm, cc, nv, nc in bad:
        print("  %-5s %-22s %-10s %-22s %s" % (ref, cm, cc or "-", nv, nc or "-"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
