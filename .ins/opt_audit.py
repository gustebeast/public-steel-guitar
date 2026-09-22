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


SEC = {0: (1, 2, 3), 1: (14, 13, 12), 2: (8, 9, 10), 3: (7, 6, 5)}
for ch in range(20):
    i, side = ch // 2 + 1, "AB"[ch % 2]
    q = ch // 4 + 1
    out_p, inn_p, inp_p = SEC[ch % 4]
    k, s = ch // 4, ch % 4 + 1
    pd = "PD%d%s" % (i, side)
    summ, out = "TIA_IN_%d%s" % (i, side), "TIA_OUT_%d%s" % (i, side)
    chk(net_of(pd, 2) == summ, "%s cathode (pad 2) not on %s: %s" % (pd, summ, net_of(pd, 2)))
    chk(net_of(pd, 1) == "MID", "%s anode not on MID" % pd)
    chk(net_of("U%d" % q, inn_p) == summ, "%s: U%d IN- %d not on summing node" % (pd, q, inn_p))
    chk(net_of("U%d" % q, inp_p) == "MID", "U%d IN+ %d not on MID" % (q, inp_p))
    chk(net_of("U%d" % q, out_p) == out, "U%d OUT %d not %s" % (q, out_p, out))
    n = "%d%d" % (q, ch % 4 + 1)
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
