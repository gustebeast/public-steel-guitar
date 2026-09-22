p = 'elec/lever_sensor.py'
s = open(p, encoding='utf-8').read()


def rep(o, n, cnt=1):
    global s
    assert s.count(o) == cnt, (o[:90], s.count(o))
    s = s.replace(o, n)


def cut(a, b, new, keep_b=True):
    global s
    i = s.index(a)
    j = s.index(b, i)
    s = s[:i] + new + (s[j:] if keep_b else s[j + len(b):])


# ── header
rep('''EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.
"""''', '''EVERY PIN NUMBER BELOW IS OFF THE DATASHEET, not a library symbol -- see the
per-part notes. Getting one wrong is the failure this file exists to prevent.

⚠ RE-SPUN 2026-09-21 TO branner's SPEC (docs/lever-sensor-respin.md), user decisions:
  * the lever bus runs at 5 V -- the 24 V buck (U1 LMR16006, L1, D1, C1-C3, R1/R2) is
    gone, and a 5 V -> 3V3 LDO (AP2112K) takes its place
  * J1 is PH again: S8B-PH-SM4-TB (LCSC C265121), SMT side entry, on the magnet face, on
    end with its mouth -X -- a different family from the 24 V XH tees, so no harness can
    put 24 V on a lever board
  * the outline is the spec's 31.0 x 21.9, trimmed at +X and at the top
The paragraph above on why PH is right again; the XH interlude it replaced is in git.
"""''')

# ── outline + frame
cut('''# ── the board ────────────────────────────────────────────────────────────────''',
    '''# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet''',
    '''# ── the board ────────────────────────────────────────────────────────────────
# ⚠ THE OUTLINE IS branner's RE-SPIN SPEC, NOT AN OUTPUT OF THIS FILE (docs/lever-sensor-
# respin.md, 2026-09-21). In the spec's frame -- origin on the MT6701, +X toward the lever,
# +Z up -- the edges are +X 3.0, top 10.1, bottom -11.8, -X -28.0: 31.0 x 21.9. This file
# works in board-local mm with the origin at the board CENTRE, so the chip sits at
# (+12.5, +0.85): 3.0 from the +X edge and 10.1 below the top.
# The -X edge is an upper bound the spec allows shrinking; it stays, because J1's plug run
# and the tunnel in the -X web are sized to it.
# ⚠ FOOTPRINTS: the MCU's QFN-28 pitch (0.4 vs 0.45) and both QFNs' exposed pads are still
# the nearest stock KiCad lands, not read off the drawings -- resolve before ordering.
MCU_FP = "Package_DFN_QFN:QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm"
SENSOR_FP = "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm"
BOARD_W, BOARD_L = 31.0, 21.9
CHIP_XY = (12.5, 0.85)        # the axle axis, in board-local mm

''')
rep('''# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector, the transceiver and the inductor qualify; every
# passive here is under 1.5.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "U2", "L1")''', '''# Anything TALLER than 1.5 mm must keep its whole footprint outside the magnet
# cap's swept circle, because the board installs by dropping straight down past
# the cap. Only the connector and the transceiver (SOIC-8, 1.75) qualify now that the
# inductor went with the buck; every passive here is under 1.5, the LDO is 1.45.
CAP_SWEEP_R = 5.66
TALL_PARTS = ("J1", "U2")''')

# ── nets
rep('''    gnd, v24, v33 = Net("GND"), Net("+24V"), Net("+3V3")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v24, v33, can_h, can_l):''', '''    gnd, v5, v33 = Net("GND"), Net("+5V"), Net("+3V3")
    can_h, can_l = Net("CAN_H"), Net("CAN_L")
    for n in (gnd, v5, v33, can_h, can_l):''')

# ── J1 + the buck -> PH + LDO
cut('''    # ⚠ XH NOW, THE SAME PART THE POWER AND TEE BOARDS USE (user, 2026-09-19). PH was''',
    '''    # ── CAN transceiver, SN65HVD230DR (LCSC C12084) ──────────────────────────''',
    '''    # PH, SMT side entry (user, 2026-09-21). Pin order is the XH trunk's (harness.XH_PINOUT)
    # so one crimp order serves every connector -- but the +V way is the 5 V LEVER bus, which
    # is why the family differs from the 24 V tees: a lever harness physically cannot mate
    # a motor tee. The footprint's two MP tabs are mechanical and carry no net.
    j1 = Part(name="S8B-PH-SM4-TB", ref_prefix="J", ref="J1", tag="J1", dest="NETLIST",
              tool="skidl", value="S8B-PH-SM4-TB",
              description="lever bus in (1-4) and out (5-8), 5 V, LCSC C265121",
              footprint="Connector_JST:JST_PH_S8B-PH-SM4-TB_1x08-1MP_P2.00mm_Horizontal",
              pins=[Pin(num=i + 1, name=n, func=P) for i, n in enumerate(
                  tuple(x + "_IN" for x in ("GND", "V5", "CAN_H", "CAN_L"))
                  + tuple(x + "_OUT" for x in ("GND", "V5", "CAN_H", "CAN_L")))])
    gnd += j1[1], j1[5]
    v5 += j1[2], j1[6]
    can_h += j1[3], j1[7]
    can_l += j1[4], j1[8]

    # ── 5 V -> 3V3, AP2112K-3.3TRG1 (LCSC C51118) ─────────────────────────────
    # Replaces the 24 V buck. SOT-23-5 (Diodes Inc DS33549): 1 IN, 2 GND, 3 EN, 4 NC,
    # 5 OUT -- the same part and pin map the output panel uses. EN tied to IN: always on.
    # 1 uF ceramic on each side is the datasheet's stability requirement. Load is ~30 mA
    # (MCU + transceiver + sensor), so it drops (5 - 3.3) x 0.03 = 0.05 W -- nothing.
    # A LINEAR regulator is also the right call beside a magnetic angle sensor: the buck
    # was the one switching node on this board, 15 mm from the MT6701.
    u1 = Part(name="AP2112K-3.3", ref_prefix="U", ref="U1", tag="U1", dest="NETLIST",
              tool="skidl", value="AP2112K-3.3TRG1",
              description="600 mA LDO, 5 V -> 3V3 (LCSC C51118)",
              footprint="Package_TO_SOT_SMD:SOT-23-5",
              pins=[Pin(num=1, name="IN", func=PWR), Pin(num=2, name="GND", func=PWR),
                    Pin(num=3, name="EN", func=I), Pin(num=4, name="NC", func=P),
                    Pin(num=5, name="OUT", func=P)])
    v5 += u1["IN"], u1["EN"]
    gnd += u1["GND"]
    v33 += u1["OUT"]
    Net("U1_NC").connect(u1["NC"])
    cin = _c("C1", "1uF", "LDO input")
    v5 += cin[1]; gnd += cin[2]
    cout = _c("C2", "1uF", "LDO output")
    v33 += cout[1]; gnd += cout[2]

''')

# ── pin every non-_r/_c ref (the buck's deletion would renumber them otherwise)
rep('''    u3 = Part(name="SN65HVD230DR", ref_prefix="U", tag="U3", dest="NETLIST",''',
    '''    # ⚠ ref= PINNED: this part has always been U2 on the board (skidl numbered it second,
    # after the buck), and with the buck gone creation order would make it U1.
    u3 = Part(name="SN65HVD230DR", ref_prefix="U", ref="U2", tag="U3", dest="NETLIST",''')
rep('''    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", tag="JP1", dest="NETLIST",''',
    '''    jp1 = Part(name="SolderJumper_2_Open", ref_prefix="JP", ref="JP1", tag="JP1", dest="NETLIST",''')
rep('''        d = Part(name="TVS", ref_prefix="D", tag=tag, dest="NETLIST", tool="skidl",''',
    '''        d = Part(name="TVS", ref_prefix="D", ref=tag, tag=tag, dest="NETLIST", tool="skidl",''')
rep('''    u2 = Part(name="CH32V203G6U6", ref_prefix="U", tag="U2", dest="NETLIST",''',
    '''    u2 = Part(name="CH32V203G6U6", ref_prefix="U", ref="U3", tag="U2", dest="NETLIST",''')
rep('''    y1 = Part(name="Crystal", ref_prefix="Y", tag="Y1", dest="NETLIST", tool="skidl",''',
    '''    y1 = Part(name="Crystal", ref_prefix="Y", ref="Y1", tag="Y1", dest="NETLIST", tool="skidl",''')
rep('''    u4 = Part(name="MT6701QT-STD", ref_prefix="U", tag="U4", dest="NETLIST",''',
    '''    u4 = Part(name="MT6701QT-STD", ref_prefix="U", ref="U4", tag="U4", dest="NETLIST",''')
rep('''    # insertion, so the leg's 24 V momentarily reaches CAN_H and CAN_L, and this
    # transceiver's bus pins are absolute-max -4..+16 V.''',
    '''    # insertion, so the leg's supply momentarily reaches CAN_H and CAN_L, and this
    # transceiver's bus pins are absolute-max -4..+16 V. (That supply is 5 V on the lever
    # bus now, inside the rating -- the clamps stay for ESD, which is what a plug on a
    # player-handled lever mostly sees.)''')
rep('''    c_bulk = _c("C10", "4.7uF", "MCU bulk", "Capacitor_SMD:C_0805_2012Metric")''',
    '''    c_bulk = _c("C10", "4.7uF", "MCU bulk -- 0402 since the re-spin (6.3 V X5R)")''')

# ── placements
cut('''    "placements": {''', '''    "cap_keepout": {''', '''    # ⚠ RE-PLACED 2026-09-21 FOR THE RE-SPIN. The circuit is the routed board's, moved
    # as a block by (+1.5, +1.45) -- the frame shift that keeps the chip on the axle in the
    # new board-centred frame -- so every relationship the CAN-fan notes below were
    # measured on (MCU beside transceiver beside crystal) is preserved exactly. What
    # changed: the buck is gone from the top, the LDO and its two caps take that corner,
    # R6 steps 0.57 -X out of the +X groove band, and the four SWD pads come in off the
    # trimmed +X edge into the top strip (one column of three plus NRST, as before).
    "placements": {
        "U4": (12.50, 0.85, 0.0),
        # SWD: SWDIO / SWCLK / GND in a row for a clip, NRST stranded (recovery only)
        "TP1": (8.00, 8.80, 0.0),     # SWDIO
        "TP2": (10.40, 8.80, 0.0),    # SWCLK
        "TP3": (8.00, 6.50, 0.0),     # GND
        "TP4": (-1.65, 8.90, 0.0),    # NRST
        # J1 on end, mouth -X at x -12.45 (3.05 in from the -X edge, the spec's figure).
        # The footprint's mouth is its local +y 4.4 and rot 270 turns that to -X, so the
        # origin sits 4.4 +X of the mouth. Its pins run along Y, pin 1 at +7.
        "J1": (-8.05, 0.00, 270.0),
        "U1": (4.00, 8.00, 0.0),
        "C1": (0.60, 8.60, 0.0),
        "C2": (0.60, 7.30, 0.0),
        "R7": (12.40, 7.15, 0.0),
        # ⚠ U3 (the MCU) AT 0 ROTATION, AND IT IS A ROUTING DECISION -- measured across all
        # four rotations on the old board (see lever_sensor()). The CAN fan (pins 19-21,
        # 0.4 pitch) closes only with the 0.50/0.25 via; see via_mm.
        "U3": (2.50, 3.00, 0.0),
        "C9": (7.00, 4.65, 0.0),
        "C8": (9.00, 4.65, 0.0),
        "R5": (12.50, 4.35, 0.0),
        "C11": (8.50, 0.85, 0.0),
        "C10": (11.00, -2.45, 0.0),
        "Y1": (0.60, -1.55, 0.0),
        # C5/C6 stay east of the crystal: moving them west measured 1 -> 5 unconnected
        "C5": (5.10, -1.05, 0.0),
        "C6": (5.10, -2.85, 0.0),
        "C7": (-1.05, 2.54, 90.0),
        "R6": (12.90, -2.47, 270.0),
        "U2": (2.00, -6.15, 0.0),
        "C4": (7.50, -4.85, 0.0),
        "R3": (7.50, -6.35, 0.0),
        "R4": (11.00, -4.30, 0.0),
        "JP1": (11.00, -6.25, 0.0),
        "D2": (7.30, -8.35, 0.0),
        "D3": (10.10, -8.35, 0.0),
    },
''')

# ── the buck-era plane notes, the J1.5 THT exception, the keep-outs
cut('''    # THE GROUND PLANE IS WHY THIS BOARD IS FOUR LAYERS. BOM.md says so outright:''',
    '''    "zones": [("GND", "In1.Cu", 0.3), ("GND", "B.Cu", 0.3)],''',
    '''    # FOUR LAYERS: an unbroken GND plane on In1 under a magnetic angle sensor, and the
    # layer set the 0.4 mm-pitch MCU's escape needs. (It was first argued against the 24 V
    # buck's switching loop; the buck is gone and the plane's other two jobs remain.)
''')
rep('''    # ⚠ J1.5 REACHES THE PLANE THROUGH ITS OWN BARREL. The XH is a THROUGH-HOLE part,
    # so its ground pin is plated through every layer and is already connected to the
    # In1 plane by existing -- a stitching via beside it would add copper that joins
    # nothing new. It arrived as "no room for a stitching via beside J1.5" only because
    # the connector now sits against the -X edge with the mounting boss on one side and
    # the board edge on the other, and layout stops rather than silently leave a SURFACE
    # pad on the pour alone. That stop is right in general and does not apply to a pad
    # with its own hole. Same reasoning as output_panel's USB shield tabs.
    "stitch_exceptions": ("J1.5",),
''', '''    # (No stitch exceptions: J1 is SMT again, so its GND pads get vias like every other.)
''')
rep('''    "groove_keepout_x": 1.85,
    "groove_exempt": ["U4", "J1"],
    "conn_keepout": {"box": [-14.0, -3.25, -11.0, 11.0], "exempt": ["J1", "U4"]},''',
    '''    "groove_keepout_x": 1.85,
    "groove_exempt": ["U4", "J1"],
    # J1's zone (spec rule 4): its body, its solder tabs and the mated plug's 3.6 run past
    # the mouth, over J1's length -- x -16.05..-3.85 here, clipped to the board.
    "conn_keepout": {"box": [-15.5, -9.95, -3.85, 9.95], "exempt": ["J1", "U4"]},''')

open(p, 'w', encoding='utf-8').write(s)
print('lever ok')
