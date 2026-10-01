"""Audit the optical board's signal chain straight off the generated netlist."""
import re
import sys

t = open('elec/out/optical.net', encoding='utf-8').read()
nets = {}
for m in re.finditer(r'\(net\s*\(code "?\d+"?\)\s*\(name "([^"]+)"\)(.*?)(?=\(net\s*\(code|\Z)', t, re.S):
    nets[m.group(1)] = set(re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', m.group(2)))
pin2net = {}
for n, ns in nets.items():
    for rp in ns:
        pin2net[rp] = n
fails = []


def chk(cond, msg):
    if not cond:
        fails.append(msg)


def net_of(ref, pin):
    return pin2net.get((ref, str(pin)))


# ⚠ TEN DUALS, NOT FIVE QUADS (2026-09-24). This audited U1-U5 as TLV9064s with SOIC-14
# pin numbers and Rf<quad><section> naming, and after the dual conversion every one of its
# twenty channels reported five failures -- a hundred lines of false alarm. An audit that
# is wrong about the design it audits is worse than no audit, because it teaches you to
# scroll past it, and the next real failure scrolls past with it.
# Same shape as the two other stale-derivative bugs this board has produced: O_HOLE_X0/X1
# outliving the comb, and ADC_BUS_CH's measured value outliving its name.
# VSSOP-8 dual: 1 OUT_A, 2 IN-_A, 3 IN+_A, 4 V-, 5 IN+_B, 6 IN-_B, 7 OUT_B, 8 V+.
# One package per string, U21..U30; section A takes the +Y detector, B the -Y one.
SEC = {"A": (1, 2, 3), "B": (7, 6, 5)}                # (out, in-, in+)
for ch in range(20):
    i, side = ch // 2 + 1, "AB"[ch % 2]
    q = 20 + i                                        # U21..U30, one dual per string
    out_p, inn_p, inp_p = SEC[side]
    # ⚠ REVERSED WITHIN THE CONVERTER, and this said ch % 4 + 1 until now. The
    # generator flipped it on 2026-09-24 (elec/optical.py, 's_in = 4 - ch % 4') so the
    # sources' north-to-south order matches the sinks' east-to-west order and the four
    # runs of a group stop crossing. The audit kept the old convention and reported all
    # TWENTY channels as 'Ci not fed from TIA_OUT' -- which is the exact failure this
    # file's own header warns about, one design change later: an audit that is wrong
    # about the design it audits teaches you to scroll past it.
    k, s = ch // 4, 4 - ch % 4
    pd = "PD%d%s" % (i, side)
    summ, out = "TIA_IN_%d%s" % (i, side), "TIA_OUT_%d%s" % (i, side)
    chk(net_of(pd, 2) == summ, "%s cathode (pad 2) not on %s: %s" % (pd, summ, net_of(pd, 2)))
    chk(net_of(pd, 1) == "MID", "%s anode not on MID" % pd)
    chk(net_of("U%d" % q, inn_p) == summ, "%s: U%d IN- %d not on summing node" % (pd, q, inn_p))
    chk(net_of("U%d" % q, inp_p) == "MID", "U%d IN+ %d not on MID" % (q, inp_p))
    chk(net_of("U%d" % q, out_p) == out, "U%d OUT %d not %s" % (q, out_p, out))
    n = "%d%s" % (i, side)                            # Rf1A / Cf1A, the CAD's scheme
    chk({net_of("Rf" + n, 1), net_of("Rf" + n, 2)} == {summ, out}, "Rf%s not across the TIA" % n)
    chk({net_of("Cf" + n, 1), net_of("Cf" + n, 2)} == {summ, out}, "Cf%s not across the TIA" % n)
    ci = "Ci%d%d" % (k + 1, s)
    chk(net_of(ci, 1) == out, "%s not fed from %s" % (ci, out))
    adc = "U%d" % (14 + k)
    chk(net_of(adc, 4 + 2 * s) == net_of(ci, 2), "%s IN%dP not on %s" % (adc, s, ci))
    cm = "Cm%d%d" % (k + 1, s)
    chk(net_of(adc, 5 + 2 * s) == net_of(cm, 1) and net_of(cm, 2) == "GND", "%s IN%dM not grounded through %s" % (adc, s, cm))
for k in range(5):
    adc, t_ = "U%d" % (14 + k), k + 1
    chk(net_of(adc, 1) == "+3V3A", "%s AVDD" % adc)
    chk(net_of(adc, 19) == "+3V3D", "%s IOVDD" % adc)
    chk(net_of(adc, 4) == "GND" and net_of(adc, 25) == "GND", "%s grounds" % adc)
    chk(net_of(adc, 22) == "SAI_SCK" and net_of(adc, 23) == "SAI_FS", "%s clocks" % adc)
    chk(net_of(adc, 21) == "SAI_SD%d" % t_, "%s SDOUT lane" % adc)
    chk(net_of(adc, 14) == "+3V3D", "%s SHDNZ not tied to IOVDD" % adc)
    bus = "I2C2"
    chk(net_of(adc, 17) == bus + "_SCL" and net_of(adc, 18) == bus + "_SDA", "%s I2C" % adc)
    addr = (net_of(adc, 15), net_of(adc, 16))
    print(adc, "addr straps", addr, "bus", bus)
    for rail, pin in (("ADC%d_AREG" % t_, 2), ("ADC%d_VREF" % t_, 3), ("ADC%d_DREG" % t_, 24)):
        chk(net_of(adc, pin) == rail, "%s pin %d not %s" % (adc, pin, rail))
        caps = [r for r, p in nets[rail] if r.startswith("Cs")]
        chk(caps, "%s has no capacitor" % rail)
# MCU side
mcu = {n: sorted(p for r, p in ns if r == "U6") for n, ns in nets.items()}
for n in ("SAI_SCK", "SAI_FS", "SAI_SD1", "SAI_SD2", "SAI_SD3", "SAI_SD4", "SAI_SD5",
          "I2C2_SCL", "I2C2_SDA", "LED_GATE"):
    chk(len(mcu.get(n, [])) == 1, "%s does not reach U6 exactly once: %s" % (n, mcu.get(n)))
    print("%-10s U6 pin %s" % (n, mcu.get(n)))
# every ADC-address pair unique per bus
seen = {}
for k in range(5):
    chk((net_of("U%d" % (14 + k), 15), net_of("U%d" % (14 + k), 16)) == ("GND", "GND"),
        "U%d address straps not both GND (broadcast scheme)" % (14 + k))
# USB path
for n in ("USB_DP", "USB_DM"):
    print(n, sorted(nets.get(n, [])))
print("FAILS:", len(fails))
for f in fails:
    print("  ", f)
sys.exit(1 if fails else 0)
