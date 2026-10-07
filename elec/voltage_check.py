"""Voltage on every pin against its rating -- five boards, from their netlists.

    py -3.12 elec/voltage_check.py                 # all five, writes the report
    py -3.12 elec/voltage_check.py motor_ctrl      # one board, findings to stdout only
    py -3.12 elec/voltage_check.py --declare       # ALSO write elec/volts/<board>.json
    py -3.12 elec/voltage_check.py --elec <dir>    # another worktree's elec/

Written by the pre-order review of 2026-10-06 (as research/review/voltage_check.py) and
brought into the repo the same day, because cadkit's A16 asks every board for exactly what
this computes: `--declare` writes each board's quality.net_volts and quality.pin_volts to
elec/volts/<board>.json, and the generators load that file into BOARD_NOTES. So the
declarations are never typed: a net's level changes in SEEDS here, a rating in
voltage_ratings.json, and the file is written again. It reads each board's netlist and
fab.py's part tables, so the order after any change is: generator, this, generator.

WHAT IT IS FOR. cadkit/PCB_QUALITY.md has M4 (capacitor ratings) and M5 (absolute ratings)
as MANUAL items: a reader signs that every part survives its rail. Nothing computes it. This
does: it gives every net a worst-case voltage, looks up every pin's rating by the LCSC code the
part is ordered under, and lists what is over, what is under-derated, and what could not be
checked. It reads the netlist and fab.py's part tables and nothing else of the board, so it
runs on any board the generators emit.

THREE VOLTAGES PER NET, because "worst case" is three different questions:
    v    steady worst case      supply tolerance, regulator tolerance. Derating is judged on this.
    vt   worst case transient   what the rail's clamp lets through, a live-plug ring, load-release
                                overshoot. Absolute maxima are judged on this.
    vf   credible single fault  a neighbouring conductor shorted on, a regulator failed short,
                                phantom power on the jack. Reported separately: FAULT, not FAIL.
plus `lo`, the most negative the net goes (only where something can pull it below ground).

HOW A NET GETS ITS NUMBERS. Rails are SEEDED in `SEEDS` below from their sources, each with a
written reason. Everything else is PROPAGATED from the netlist:
  * through a resistor, ferrite, fuse or inductor a net inherits the upstream level (an upper
    bound: a pull-up to 5 V makes the net a 5 V net);
  * a net held by resistors to ground and to ONE other net is a divider and gets the divided
    value, from the resistor values in the netlist;
  * an IC output pin can reach its own supply, so the net is at least that;
  * relay contacts, analog switches and pot terminals pass a level through.
A net nothing explains is reported UNRESOLVED rather than guessed.

WHAT IS JUDGED.
  FAIL      steady worst case exceeds an absolute maximum or a rated voltage/power/current.
  SUSPECT   the transient level exceeds it; or steady exceeds the RECOMMENDED limit; or a
            capacitor is under-derated (class-II ceramic above 60 % of rating on a rail of
            12 V or more, anything above 80 %); or a resistor/fuse/contact is above 80 % of
            rating; or a clamp's stand-off is below the rail it sits on.
  FAULT     only the single-fault level exceeds the rating.
  UNVERIFIED no rating could be read for the pin (see the ratings file for why).

Ratings live beside this file in voltage_ratings.json, keyed by LCSC code, each with the
document and page it was read from. A board change that introduces a new code shows up as
UNVERIFIED until someone adds the entry.

PROMOTING IT. Each check returns (subject, verdict, text) like a cadkit quality rule; the
board-specific part is SEEDS / models, which is what BOARD_NOTES["quality"] would carry.

Exit status: the number of FAILs.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import math
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ELEC = HERE
OUT = os.path.join(HERE, "out", "volts")              # the report and the per-pin tables
DECL = os.path.join(HERE, "volts")                    # what the generators load (tracked)
LEG = ("leg_pogo_male_bottom", "leg_pogo_male_top", "leg_pogo_female_bottom", "leg_pogo_female_top")
BOARDS = ("can_tee", "pi_cap", "motor_ctrl", "output_panel", "optical", "lever_sensor") + LEG
ORDER = ("output_panel", "motor_ctrl", "pi_cap", "optical", "can_tee", "lever_sensor") + LEG   # sources before sinks
GNDS = ("GND", "PWR_GND")
EPS = 1e-6

RAT = json.load(io.open(os.path.join(HERE, "voltage_ratings.json"), encoding="utf-8"))
PARTS = RAT["parts"]
BRICK = RAT["system"]["brick"]
RAIL_TVS = PARTS[RAT["system"]["rail_tvs"]]

# ── THE 24 V RAIL ─────────────────────────────────────────────────────────────────────────
# steady: the brief's 24 V + 10 %. The brick itself is +/-3 % (24.72 V); the extra is room for
#         stepper regeneration lifting the rail below anything that clamps it.
# transient: the rail clamp's voltage AT THE MOST CURRENT THIS RAIL CAN BE HANDED, which is
#         the brick's own rated output. The clamp's catalogue VC is at its rated pulse (10.3 A
#         for the SMAJ24A) and nothing on this rail can supply that: the brick limits at its
#         rating, and a stepper returns at most the current it was driven with, which came out
#         of the same budget. Linear between maximum breakdown and VC, so a max-breakdown unit
#         carrying 6.67 A stands at 35.6 V. `V24_VC` keeps the catalogue point, and
#         `tvs_amps_at()` says how many amps of surge reach a given rating.
#         (The clamp was an SMAJ30A until the review: 36.8 V before it did anything at all.)
V24_STEADY = BRICK["vnom"] * 1.10
V24_SUSTAIN = RAIL_TVS["vbr_max"]
V24_VC = RAIL_TVS["vc"]
V24_CLAMP = V24_SUSTAIN + (V24_VC - V24_SUSTAIN) * min(1.0, BRICK["i"] / RAIL_TVS["ipp"])
V24_BRICK = BRICK["vnom"] * (1 + BRICK["tol"])
V24_LIVE_PLUG = 2 * V24_BRICK                 # an undamped LC ring toward twice the source


def tvs_amps_at(volts):
    """Surge current at which the rail TVS (max-breakdown unit) lets the rail reach `volts`."""
    t = RAIL_TVS
    return max(0.0, (volts - t["vbr_max"]) / (t["vc"] - t["vbr_max"]) * t["ipp"])


CAN_TVS = PARTS["C14486"]                     # NUP2105L across bus A at motor_ctrl


RAIL24 = dict(v=V24_STEADY, vt=V24_CLAMP,
              why="24 V +10 %% steady (brick is +/-3 %%: %.2f V; OVP trips at up to %.1f V); "
                  "transient = the %s clamp at the brick's %.2f A, the most this rail can be "
                  "handed: %.1f V (breakdown %.1f-%.1f V; its catalogue VC is %.1f V at %.1f A)"
                  % (V24_BRICK, BRICK["vnom"] * BRICK["ovp_max_frac"], RAIL_TVS["mpn"], BRICK["i"],
                     V24_CLAMP, RAIL_TVS["vbr_min"], RAIL_TVS["vbr_max"], V24_VC, RAIL_TVS["ipp"]))
CAN_A = dict(v=5.0, vt=CAN_TVS["vbr_max"], vf=V24_STEADY,
             why="bus A: dominant level of a 5 V transceiver in a SERVO42D (assumed, not known); "
                 "transient = the NUP2105L's maximum breakdown either way (24 V stand-off, so the "
                 "+24 V conductor beside it in the same 4-wire trunk is a level it stands, not one "
                 "it clamps); FAULT = that conductor shorted on")

CAN_B = dict(v=5.0, vt=7.8, why="bus B: 5 V nodes; nothing above 5 V in its cable; transient = the "
                                 "ESD5B5.0 clamps' maximum breakdown (motor_ctrl D4 / D5, and each lever board's own)")

# net -> spec.  ("abs", {...}) | ("like", net, dv) | ("ratio", net, k) | ("buck", ic, top, bot)
#               | ("ldo", ic) | ("from", board, net)        -- last element is always the reason
SEEDS = {
    "can_tee": {
        "+24V": ("abs", RAIL24),
        "CAN_H": ("abs", CAN_A), "CAN_L": ("abs", CAN_A),
    },
    "motor_ctrl": {
        # ⚠ THE RAIL'S TRANSIENT COVERS WHAT THE BRICK AND THE MOTORS CAN DO. A LIVE PLUG IS
        # SEPARATE: its current is set by the lead and the capacitors. Worked in
        # motor_ctrl.py at F1 (lead 0.3-2 uH, 30-120 mohm, into C1 and through F1's
        # 0.49 ohm into U5's 9 uF): 34.2 V on the rail and 31.0 V at U5's VIN in the worst corner,
        # both under the 35.6 V declared here, so the rail's figure stands for it too.
        "+24V": ("abs", RAIL24),
        "SW": ("like", "+24V", 0.0, "buck switch node: VIN while the high side is on"),
        "SW5": ("like", "+24V_BUCK", 0.0, "buck switch node: VIN while the high side is on"),
        "+3V3": ("buck", "U1", "R1", "R2", "LMR16006: VFB max x (1 + top/bot), 1 % resistors; "
                                           "+5 % load-release overshoot as the transient"),
        "+5V_RAW": ("buck", "U5", "R10", "R11",
                    "LMR33630: VFB max x (1 + top/bot), 1 % resistors; +5 % overshoot; FAULT = "
                    "U5's high side fails short and D9 (SMBJ5.0A) clamps at its VC while F1 clears",
                    {"vf": PARTS["C83333"]["vc"]}),
        "CANA_H": ("abs", CAN_A), "CANA_L": ("abs", CAN_A),
        "CANB_H": ("abs", CAN_B), "CANB_L": ("abs", CAN_B),
        "PWR_SW_UP": ("from", "output_panel", "SW_SENSE", "the power button's throw, from output_panel"),
        "PWR_SW_DN": ("from", "output_panel", "SW_SENSE", "the power button's throw, from output_panel"),
        "VBUS_NC": ("abs", dict(v=5.25, vt=5.5, why="USB VBUS on the lead from the Pi; lands on a lone pad")),
    },
    "lever_sensor": {
        "+5V": ("from", "motor_ctrl", "+5V_BUSB", "bus B's 5 V from motor_ctrl J2 / J6, behind its switch"),
        "+3V3": ("ldo", "U1", "AP2112K-3.3: 3.3 V +1.5 %; +3 % transient"),
        "CAN_H": ("abs", CAN_B), "CAN_L": ("abs", CAN_B),
    },
    **{leg: {
        "+5V": ("from", "motor_ctrl", "+5V_BUSB", "bus B's 5 V from motor_ctrl J2 / J6, behind its switch"),
        "CAN_H": ("abs", CAN_B), "CAN_L": ("abs", CAN_B),
    } for leg in LEG},
    "pi_cap": {
        "+24V_LED": ("from", "motor_ctrl", "+24V_LED", "lighting bus from motor_ctrl J7, after F3"),
        "+5V_PI": ("from", "motor_ctrl", "+5V", "the Pi's 5 V from motor_ctrl J5"),
        "+3V3_PI": ("abs", dict(v=3.3 * 1.05, vt=3.3 * 1.08,
                                why="Raspberry Pi 3V3 rail, taken as 3.3 V +5 % (assumed; the Pi's "
                                    "PMIC tolerance was not looked up)")),
        "PWR_SW_UP": ("from", "output_panel", "SW_SENSE", "the power button's throw, from output_panel"),
        "PWR_SW_DN": ("from", "output_panel", "SW_SENSE", "the power button's throw, from output_panel"),
    },
    "output_panel": {
        "+24V": ("abs", RAIL24),
        "+24V_IN": ("abs", dict(v=V24_STEADY, vt=max(V24_CLAMP, V24_LIVE_PLUG),
                                why="inlet, ahead of the switch: steady as the rail; transient = a "
                                    "live plug ringing toward 2 x %.2f V into C55's 100 nF with "
                                    "Q2 off (D6 is on the far side of Q2)" % V24_BRICK)),
        "SW": ("like", "+24V", 0.0, "buck switch node: VIN while the high side is on"),
        "V5_PRE": ("buck", "U5", "R11", "R12", "LMR16006: VFB max x (1 + top/bot), 1 % resistors; "
                                               "+5 % overshoot"),
        "+3V3": ("ldo", "U6", "AP2112K-3.3: 3.3 V +1.5 %; +3 % transient"),
        "VMID": ("ratio", "+5V", 0.5, "R17/R18 mid-rail"),
        "SW_SENSE": ("abs", dict(v=PARTS["C248313"]["vz_max"], vt=PARTS["C248313"]["vz_max"] + 0.2,
                                 why="clamped by D8 (BZT52C10T, VZ max 10.6 V) behind R33+R34 = 9.4 k; "
                                     "+0.2 V for its 20 ohm at the transient current")),
        "RELAY_COIL": ("like", "+5V", 1.25, "coil turn-off: +5V plus D4's forward drop (1.25 V max)"),
        "AUDIO_PROC": ("abs", dict(lo=-3.0, v=3.0, vt=3.0, why="PCM5102A line out, 2.1 Vrms ground-centred")),
        "DAC_OUT_R": ("abs", dict(lo=-3.0, v=3.0, vt=3.0, why="PCM5102A line out, 2.1 Vrms ground-centred")),
        "DAC_FILT": ("abs", dict(lo=-3.0, v=3.0, vt=3.0, why="PCM5102A line out behind 470R")),
        "DAC_R_FILT": ("abs", dict(lo=-3.0, v=3.0, vt=3.0, why="PCM5102A line out behind 470R")),
        "DAC_ATT": ("abs", dict(lo=-1.5, v=1.5, vt=1.5, why="DAC out / 2 (R14, R15)")),
        "RING_ATT": ("abs", dict(lo=-1.5, v=1.5, vt=1.5, why="DAC out / 2 (R24, R25)")),
        "DIRECT_AC": ("abs", dict(lo=-2.6, v=2.6, vt=2.6, why="pickup buffer, AC-coupled to 0 V: +/- half the 5 V rail")),
        "AUDIO_SEL": ("abs", dict(lo=-2.6, v=2.6, vt=2.6, why="relay common: either source, 0 V referenced")),
        "RING_SEL": ("abs", dict(lo=-2.6, v=2.6, vt=2.6, why="relay common: either source, 0 V referenced")),
        "OUT_BUF_IN": ("like", "+5V", 0.0, "AC-coupled onto VMID: VMID +/- 2.6 V, bounded by the 5 V rail"),
        "RING_BUF_IN": ("like", "+5V", 0.0, "AC-coupled onto VMID: VMID +/- 2.6 V, bounded by the 5 V rail"),
        "PICKUP_IN": ("like", "+5V", 0.0, "AC-coupled onto VMID; a magnetic pickup is volts at most"),
        "PICKUP_HOT": ("abs", dict(lo=-5.0, v=5.0, vt=5.0, why="magnetic pickup at the screw terminal: "
                                                              "assumed under 5 V peak (external, unverifiable)")),
        "ADC_IN": ("like", "+5V", 0.0, "AC-coupled ADC input, biased inside the PCM1808; bounded by VCC"),
        # 48 V phantom is 48 +/-4 V behind 6.81 k per leg (IEC 61938 P48); the bleed resistor
        # loads it, so the jack contact sits at 52 x 100k / (100k + 6.81k).
        "JACK_TIP": ("abs", dict(lo=-2.6, v=2.6, vt=2.6, vf=52.0 * 100e3 / (100e3 + 6.81e3),
                                 why="output behind its DC block; FAULT = 48 V phantom (52 V max) from a mixer's "
                                     "XLR input through its 6.81 k, loaded by the 100 k bleed")),
        "JACK_RING": ("abs", dict(lo=-2.6, v=2.6, vt=2.6, vf=52.0 * 100e3 / (100e3 + 6.81e3),
                                  why="as JACK_TIP: a TRS ring lands on XLR pin 3")),
        # A phantom-powered input adds one more event here: the insertion edge through C1 lifts
        # this node until D5 breaks down (5.8-7.8 V) for C1's charging time, 6.81 k x 2.2 uF =
        # 15 ms at under 8 mA. It is milliseconds and milliamps, so it is not carried as a level.
        "OUT_BLOCKED": ("like", "+5V", 0.0, "op-amp side of the DC block, behind R9: the buffer's own rail"),
        "RING_BLOCKED": ("like", "+5V", 0.0, "op-amp side of the DC block, behind R20: the buffer's own rail"),
        "DAC_VNEG": ("abs", dict(lo=-3.4, v=0.0, vt=0.0, why="PCM5102A charge-pump negative rail")),
        "DAC_CAPM": ("abs", dict(lo=-3.4, v=0.0, vt=0.0, why="PCM5102A flying cap, negative side")),
        "THRU_DP": ("abs", dict(v=3.6, vt=3.6, vf=5.25, why="USB 2.0 data pass-through; FAULT = VBUS in the connector")),
        "THRU_DM": ("abs", dict(v=3.6, vt=3.6, vf=5.25, why="USB 2.0 data pass-through; FAULT = VBUS in the connector")),
        "VBUS_PANEL_NC": ("abs", dict(v=5.25, vt=5.5, why="host VBUS on the cable; pads only (no PD negotiation: 5k1 on CC)")),
        "VBUS_PI_NC": ("abs", dict(v=5.25, vt=5.5, why="host VBUS on the cable; pads only")),
        "VBUS_UP_NC": ("abs", dict(v=5.25, vt=5.5, why="host VBUS on the cable; pads only")),
    },
    "optical": {
        "V24_IN": ("from", "output_panel", "+24V_OPT",
                   "24 V from output_panel J9, after its F1. A live plug does not ring here: U13's 5 uF "
                   "sits behind R44's 2 ohm, four times the 0.45 ohm of a 1 uH lead into it"),
        "SW": ("like", "+24V", 0.0, "buck switch node: VIN while the high side is on"),
        "V5_PRE": ("buck", "U13", "R40", "R41", "LMR33630: VFB max x (1 + top/bot), 1 % resistors; +5 % overshoot"),
        "+3V3D": ("ldo", "U8", "AP2114H-3.3: 3.3 V +1.5 %; +3 % transient"),
        "+3V3A": ("ldo", "U9", "TPS7A2033: 3.3 V +1.5 % (assumed); +3 % transient"),
        "LED_ROW": ("like", "V5_PRE", 0.0, "emitter cathodes: float up to the anode rail when Q1 is off"),
        "VBUS": ("abs", dict(v=5.25, vt=5.5, why="USB VBUS from the hub port (output_panel +5V) or any host: 5.25 V max")),
        "USB_CC1": ("abs", dict(v=5.25, vt=5.5, why="host Rp pull-up to VBUS")),
        "USB_CC2": ("abs", dict(v=5.25, vt=5.5, why="host Rp pull-up to VBUS")),
    },
}

# (ref regex, pin regex, spec) -- for nets that have no stable name, picked by a pin on them
PIN_SEEDS = {
    "pi_cap": [(r"^J1$", r".*", ("like", "+3V3_PI", 0.0, "Raspberry Pi GPIO: 3.3 V CMOS"))],
    "output_panel": [(r"^J[1-3]$", r"^[AB]5$", ("abs", dict(v=5.25, vt=5.5, why="USB-C CC: a host's Rp pull-up to VBUS")))],
}



# ── REVIEWER'S NOTES: what a finding means, printed under it ──────────────────────────────
# Keyed (ref, severity). These are judgement, not arithmetic -- delete one when its finding
# goes away (the script says when a note no longer matches anything).
REVIEW_NOTES = {
    "can_tee": {
        ("J1", "SUSPECT"): "The boards' own figure. JST's 3 A is per contact with AWG22 at room temperature; "
                           "nothing but harness resistance shares the current between the two feeds.",
    },
    "motor_ctrl": {
        ("D9", "SUSPECT"): "The NOMINAL rail (5.02 V) is already above the 5.0 V stand-off. It costs leakage "
                           "(up to 0.8 mA at 25 C, more hot), not function: breakdown starts at 6.4 V.",
        ("U6", "FAULT"): "Single fault, by design: U5 shorted, D9 holds the 5 V rail at up to 9.2 V while F1 clears. "
                         "That is above this switch's 7 V and above whatever the Pi accepts on its 5 V pins.",
        ("U4", "FAULT"): "Same event as U6, seen through R18/R19: microamps into the pin.",
    },
    "output_panel": {
        ("D5", "SUSPECT"): "Only with the 5 V rail at the top of its tolerance AND the buffer clipped to the rail. Ignore.",
        ("J6", "SUSPECT"): "A connector's working voltage against a microsecond ring: not a real exposure. The current "
                           "line is the brick's full 6.67 A; the instrument's own budget is 3.5 A (47 %).",
    },
    "optical": {
    },
}

# ── LOAD MODELS: what a low-value resistor actually carries ───────────────────────────────
# A resistor's dissipation is bounded by (its nets' extremes)^2 / R. Where that bound is under
# half the rating nothing more is needed. Where it is not, the real load has to be SAID --
# ("v", volts across) or ("i", amps through), with the reason. Missing = UNVERIFIED.
def _vod(L, R):
    return PARTS["C12084"]["vod_max"]


RES_MODEL = {
    "can_tee": {"R1": ("v", _vod, "CAN termination: SN65HVD230 dominant VOD max 3 V, 100 % dominant")},
    "motor_ctrl": {"R23": ("i", 0.8, "U5's input at 15 W out, the figure F1 is sized on"),
                   "R5": ("v", lambda L, R: PARTS["C22433320"]["vod_max"],
                          "CAN termination: TCAN3413 dominant VOD max 3 V, 100 % dominant")},
    "lever_sensor": {
        "R4": ("v", _vod, "CAN termination, switched in on the last board only: SN65HVD230 dominant VOD "
                          "max 3 V, 100 % dominant"),
        "R8": ("i", 0.08, "in series with the LDO's input: the board's whole draw, 80 mA by its own budget (CH32V203 + "
                          "SN65HVD230 dominant + MT6701)"),
    },
    "pi_cap": {r: ("i", 0.016, "series termination into a CMOS input; worst case the Pi pin's 16 mA "
                               "drive into a shorted line") for r in ("R1", "R2", "R3", "R4")},
    "output_panel": {
        "R5": ("i", lambda L, R: L("RELAY")["v"] / (R("R5") + R("R36")), "gate series: only R36's pull-down current"),
        "R9": ("v", lambda L, R: L("+5V")["v"] / 2, "output series behind a DC block: at most half the rail, as a "
                                                    "square wave into a shorted jack"),
        "R20": ("v", lambda L, R: L("+5V")["v"] / 2, "as R9; a TS plug shorts ring to sleeve"),
        "R13": ("i", lambda L, R: 3.0 / (R("R13") + R("R14") + R("R15")), "DAC peak into the 20 k attenuator"),
        "R23": ("i", lambda L, R: 3.0 / (R("R23") + R("R24") + R("R25")), "DAC peak into the 20 k attenuator"),
        "R33": ("v", lambda L, R: L("+24V_IN")["v"] / 2, "button held: R33+R34 across the inlet, half each"),
        "R34": ("v", lambda L, R: L("+24V_IN")["v"] / 2, "button held: R33+R34 across the inlet, half each"),
    },
    "optical": {
        "R36": ("i", lambda L, R: L("LED_GATE")["v"] / (R("R36") + R("R38")), "gate series: only R38's pull-down current"),
        "R42": ("i", 0.001, "MID reference: the photodiodes' microamps; 1 mA allowed"),
        "R43": ("i", 0.05, "bead damper in series with C134: ripple current only; 50 mA allowed"),
        "R44": ("i", 0.26, "buck input current, the board's own declared 0.26 A"),
    },
}

# capacitors that are not to ground and whose stress is NOT the difference of their nets' extremes
CAP_ACROSS = {
    "output_panel": {
        "C48": ("div", "+24V_IN", "R32", "R31", "gate-source: the R32/(R31+R32) share of the inlet with Q3 on"),
        "C4": ("fixed", 7.0, "bootstrap: CB-SW, held by the LMR16006 (abs max 7 V)"),
        "C32": ("fixed", 3.5, "charge-pump flying capacitor: one supply's worth"),
    },
    "motor_ctrl": {
        "C3": ("fixed", 7.0, "bootstrap: CB-SW, held by the LMR16006 (abs max 7 V)"),
        "C20": ("fixed", 5.5, "bootstrap: BOOT-SW, held by the LMR33630 (abs max 5.5 V)"),
    },
    "optical": {"C163": ("fixed", 5.5, "bootstrap: BOOT-SW, held by the LMR33630 (abs max 5.5 V)")},
}

# MOSFET gate-source stress where the bound from the nets is not the real one
FET_VGS = {
    "output_panel": {"Q2": ("div", "+24V_IN", "R32", "R31", "gate divider: Vgs = -Vin x R32/(R31+R32)")},
}

# zener dissipation: (source net, series resistors)
ZENER_FEED = {"output_panel": {"D8": ("+24V_IN", ("R33", "R34"))}}

# ── CURRENTS: (ref, contacts or None, amps, where the number comes from) ──────────────────
# The amps are the boards' OWN declared figures (BOARD_NOTES["quality"]["power_paths"] in the
# generators) unless the note says otherwise; this only sets them beside the part's rating.
CURRENTS = {
    "can_tee": [
        ("J1", 1, 3.0, "trunk +24 V on ONE contact per way: can_tee.py declares 3.0 A through the tee "
                       "(output_panel J7 and motor_ctrl J1 each declare 2.9 A into an end tee)"),
        ("J2", 1, 0.58, "one motor's drop: a tenth of the 5.8 A the two feeds declare for ten motors slewing"),
        ("SW1", None, PARTS["C12084"]["vod_max"] / 120.0, "terminator switch: VOD max 3 V / 120 ohm while dominant"),
    ],
    "motor_ctrl": [
        ("J3", 2, 5.24, "24 V in on two contacts: output_panel.py's ten-motor figure for this feed"),
        ("J1", 1, 2.9, "bus A west feed, one contact (motor_ctrl.py power_paths)"),
        ("J7", 1, 1.70, "lighting bus, every zone full white"),
        ("J5", 2, 3.0, "5 V to the Pi on two contacts"),
        ("J2", 1, 0.57, "bus B 5 V, the TPS2553's maximum limit"),
        ("J6", 1, 0.57, "bus B 5 V, the TPS2553's maximum limit"),
        ("F1", None, 0.8, "U5's input at 15 W out (motor_ctrl.py: 69-78 % across the input range)"),
        ("F2", None, 3.0, "U5's output to the Pi"),
        ("F3", None, 1.70, "lighting bus"),
        ("L2", None, 3.0, "U5's rated output; its high-side limit is up to 5.05 A (p.6)"),
        ("L1", None, 0.25, "3V3 load"),
    ],
    "pi_cap": [
        ("J2", 2, 3.0, "5 V to the Pi on two contacts"),
        ("J4", 1, 1.70, "lighting bus in"),
        ("J3", 1, 1.70, "to fret_led_key"),
        ("J6", 1, 0.77, "to foot_led_a"),
        ("J5", 1, 0.57, "UI ribbon 3V3, the TPS2553's maximum limit"),
        ("J1", 2, 3.0, "5 V into the Pi on header pins 2 and 4"),
    ],
    "output_panel": [
        ("J6", 1, 6.67, "the brick's full rated output against the jack's 7.5 A (the instrument is budgeted 3.5 A)"),
        ("J7", 1, 2.9, "motor trunk head, ONE contact (output_panel.py: 2.9 A with ten motors moving)"),
        ("J10", 2, 5.24, "feed 2 on two contacts, ten motors (output_panel.py; 3.8 A once the brick's 6.67 A is the limit)"),
        ("J9", 1, 0.26, "optical board"),
        ("F1", None, 0.26, "optical board's declared input current"),
        ("FB1", None, 0.3, "board 5 V"),
        ("L1", None, 0.3, "board 5 V"),
        ("Q2", None, 6.67, "the brick's full output through the switch"),
    ],
    "optical": [
        ("J2", 1, 0.26, "24 V in"),
        ("L1", None, 1.07, "buck peak (optical.py power_paths)"),
        ("FB1", None, 0.17, "analog LDO feed"),
    ],
}


# ── netlist + BOM ─────────────────────────────────────────────────────────────────────────
def load_board(elec, board):
    s = io.open(os.path.join(elec, "out", board + ".net"), encoding="utf-8").read()
    comps = {}
    for blk in s[s.index("(components"):s.index("(nets")].split("(comp\n")[1:]:
        ref = re.search(r'\(ref "([^"]+)"', blk).group(1)
        val = re.search(r'\(value "([^"]*)"', blk).group(1)
        fp = re.search(r'\(footprint "([^"]*)"', blk)
        de = re.search(r'\(description "([^"]*)"', blk)
        comps[ref] = dict(value=val, fp=fp.group(1).split(":")[-1] if fp else "",
                          desc=de.group(1) if de else "", pins={}, code=None)
    nets = {}
    for blk in s[s.index("(nets"):].split("(net\n")[1:]:
        name = re.search(r'\(name "([^"]*)"', blk).group(1)
        nodes = re.findall(r'\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk)
        nets[name] = nodes
        for r, p in nodes:
            comps[r]["pins"][p] = name
    # Which LCSC code each part is ordered as: fab.py's two tables, the ones the fab BOM is
    # itself written from -- so a part changed in a generator is judged as the new part
    # straight away, not after the package has been rebuilt. The BOM on disk is read only
    # for a part the tables do not name (and for another worktree's elec/, as it stands).
    import fab
    for c in comps.values():
        c["code"] = fab.LCSC.get(c["value"]) or fab.PASSIVES.get((c["value"], "Capacitor_SMD:" + c["fp"]))             or fab.PASSIVES.get((c["value"], "Resistor_SMD:" + c["fp"])) or fab.PASSIVES.get((c["value"], c["fp"]))
    bom = os.path.join(elec, "out", "fab", board, board + "-bom.csv")
    if os.path.exists(bom):
        for row in list(csv.reader(io.open(bom, encoding="utf-8")))[1:]:
            for r in row[1].split(","):
                if r.strip() in comps and not comps[r.strip()]["code"]:
                    comps[r.strip()]["code"] = row[3].strip()
    return comps, nets


def part_of(c):
    return PARTS.get(c["code"]) if c["code"] else None


def kind_of(ref, c):
    p = part_of(c)
    if p:
        return p["kind"]
    if ref.startswith("TP"):
        return "tp"
    if ref.startswith("JP"):
        return "jumper"
    return "unknown"


_MULT = {"R": 1.0, "k": 1e3, "K": 1e3, "M": 1e6}


def ohms(ref, c):
    p = part_of(c)
    if p and p.get("ohm") is not None:
        return p["ohm"]
    m = re.match(r"^(\d+)([RkKM])(\d*)", c["value"])
    if m:
        return float(m.group(1) + "." + (m.group(3) or "0")) * _MULT[m.group(2)]
    return None


PASS2 = ("res", "fuse", "bead", "ind")


class Board:
    def __init__(self, elec, name, done):
        self.name = name
        self.comps, self.nets = load_board(elec, name)
        self.done = done                  # boards already resolved, for ("from", ...)
        self.L = {}                       # net -> level dict
        self.unresolved = []
        self.rows = []                    # per-pin rows
        self.finds = []                   # (severity, ref, text)
        self.resolve()

    # -- levels ----------------------------------------------------------------------------
    def R(self, ref):
        return ohms(ref, self.comps[ref])

    def lvl(self, net):
        return self.L[net]

    @staticmethod
    def mk(lo=0.0, v=0.0, vt=None, vf=None, why="", nc=False):
        vt = v if vt is None else max(vt, v)
        vf = vt if vf is None else max(vf, vt)
        return dict(lo=lo, v=v, vt=vt, vf=vf, why=why, nc=nc)

    def from_spec(self, spec):
        """A level dict, or None if it leans on a net not resolved yet."""
        kind = spec[0]
        extra = spec[-1] if isinstance(spec[-1], dict) and kind != "abs" else {}
        why = spec[-2] if extra else spec[-1]
        if kind == "abs":
            d = dict(spec[1])
            return self.mk(**d)
        if kind == "from":
            src = self.done[spec[1]].L[spec[2]]
            return self.mk(lo=src["lo"], v=src["v"], vt=src["vt"], vf=src["vf"],
                           why="%s [%s.%s: %s]" % (spec[3], spec[1], spec[2], src["why"]))
        if kind == "like":
            if spec[1] not in self.L:
                return None
            s, dv = self.L[spec[1]], spec[2]
            return self.mk(lo=0.0, v=s["v"] + dv, vt=s["vt"] + dv,
                           vf=max(s["vf"] + dv, extra.get("vf", 0.0)), why=why + " [= %s%+g]" % (spec[1], dv))
        if kind == "ratio":
            if spec[1] not in self.L:
                return None
            s, k = self.L[spec[1]], spec[2]
            return self.mk(v=s["v"] * k, vt=s["vt"] * k, vf=s["vf"] * k, why=why)
        if kind == "buck":
            ic = part_of(self.comps[spec[1]])
            v = ic["vfb_max"] * (1 + self.R(spec[2]) * 1.01 / (self.R(spec[3]) * 0.99))
            return self.mk(v=v, vt=v * 1.05, vf=extra.get("vf"),
                           why="%s: %.3f V x (1 + %s/%s) -> %.2f V max" % (why, ic["vfb_max"], spec[2], spec[3], v))
        if kind == "ldo":
            ic = part_of(self.comps[spec[1]])
            v = ic["vout"] * (1 + ic["vout_tol"])
            return self.mk(v=v, vt=v * 1.03, why=spec[2])
        raise ValueError(spec)

    def pinspec(self, ref, pin):
        """(spec dict or None, part) for an IC-like pin, with the default and supply rule applied."""
        c = self.comps[ref]
        p = part_of(c)
        if not p or p["kind"] != "ic":
            return None, p
        ps = p["pins"].get(pin)
        if ps is None and "default" in p:
            net = c["pins"].get(pin)
            supnets = {c["pins"].get(sp) for sp in p.get("supply", {}).values()}
            if net in GNDS:
                ps = {"n": "VSS", "gnd": True}
            elif net in supnets:
                ps = {"n": "VDD", "max": p["supply_max"], "rec": p.get("supply_rec")}
            else:
                ps = p["default"]
        return ps, p

    def supply_net(self, ref, name):
        c = self.comps[ref]
        p = part_of(c)
        pin = p.get("supply", {}).get(name)
        return c["pins"].get(pin) if pin else None

    def pass_groups(self, ref):
        p = part_of(self.comps[ref])
        if p and p.get("pass"):
            return p["pass"]
        if ref.startswith("JP"):
            return [sorted(self.comps[ref]["pins"])]
        return []

    def try_auto(self, net, strict):
        nodes = self.nets[net]
        cands, unknown, strong, driven = [], False, False, False
        res_gnd, res_other = [], collections.defaultdict(list)

        soft = []                          # levels that only arrive through a resistor

        def see(other, how, resistive=False):
            nonlocal unknown
            if other in self.L:
                cands.append((self.L[other], how))
                if resistive:
                    soft.append(self.L[other])
            else:
                unknown = True

        for ref, pin in nodes:
            c = self.comps[ref]
            k = kind_of(ref, c)
            if k in PASS2 and len(c["pins"]) == 2:
                other = [n for p_, n in c["pins"].items() if p_ != pin][0]
                if other == net:
                    continue
                if other in GNDS:
                    if k == "res":
                        res_gnd.append(self.R(ref))
                    continue
                if k == "res":
                    res_other[other].append(self.R(ref))
                else:
                    strong = True
                see(other, "through " + ref, k == "res")
            for grp in self.pass_groups(ref):
                if pin in grp:
                    strong = True
                    for q in grp:
                        other = c["pins"].get(q)
                        if q != pin and other and other != net and other not in GNDS:
                            see(other, "through " + ref)
            if k == "ic":
                ps, part = self.pinspec(ref, pin)
                if ps is None:
                    continue
                if "internal" in ps:
                    v = ps["internal"]
                    cands.append((self.mk(lo=min(v, 0.0), v=max(v, 0.0),
                                          why="generated inside %s (%s)" % (ref, ps["n"])), ref))
                    strong = True
                if ps.get("boot"):
                    swn = self.supply_net(ref, "SW")
                    off = float(str(ps["max"]).split("+")[1])
                    if swn in self.L:
                        s = self.L[swn]
                        cands.append((self.mk(v=s["v"] + off, vt=s["vt"] + off,
                                              why="bootstrap: %s + %g V, held by %s" % (swn, off, ref)), ref))
                    else:
                        unknown = True
                    strong = True
                sup = ps.get("drv")
                if not sup and ps.get("ac_in"):
                    sup = re.match(r"[A-Za-z0-9_.]+", str(ps["max"])).group(0)
                if sup:
                    sn = self.supply_net(ref, sup)
                    if sn in self.L:
                        s = self.L[sn]
                        cands.append((self.mk(v=s["v"], vt=s["vt"], vf=s["vf"],
                                              why="%s.%s (%s) can reach its supply %s" % (ref, pin, ps["n"], sn)), ref))
                    else:
                        unknown = True
                    if not ps.get("weak") and not ps.get("ac_in"):
                        strong = True
                        driven = True
        if len(nodes) == 1 and not cands:
            return self.mk(why="not connected", nc=True)
        if res_gnd and len(res_other) == 1 and not strong:
            x = list(res_other)[0]
            if x in self.L:
                rg = 1 / sum(1 / r for r in res_gnd)
                rx = 1 / sum(1 / r for r in res_other[x])
                k = rg / (rg + rx)
                s = self.L[x]
                lv = self.mk(v=s["v"] * k, vt=s["vt"] * k, vf=s["vf"] * k,
                             why="divider off %s: x %.4f" % (x, k))
                lv["rsrc"] = rx
                return lv
            if strict:
                return None
        if unknown and strict:
            return None
        if cands:
            return self.mk(lo=0.0,
                           v=max(c_[0]["v"] for c_ in cands), vt=max(c_[0]["vt"] for c_ in cands),
                           # a FAULT level reaching a DRIVEN net through a resistor is the resistor's
                           # problem (its dissipation is judged), not the net's: the driver holds it
                           vf=max((c_[0]["vt"] if (driven and any(c_[0] is s_ for s_ in soft)) else c_[0]["vf"])
                                  for c_ in cands),
                           why="; ".join(sorted({"%s" % (c_[0]["why"] if c_[1] == "" else
                                                         ("%s" % c_[1] if str(c_[1]).startswith("through") else c_[0]["why"]))
                                                 for c_ in cands}))[:160])
        if res_gnd:
            return self.mk(why="pulled to ground")
        return None

    def resolve(self):
        for g in GNDS:
            if g in self.nets:
                self.L[g] = self.mk(why="ground")
        seeds = dict(SEEDS.get(self.name, {}))
        for net, nodes in self.nets.items():            # pin-pattern seeds
            if net in seeds or net in self.L:
                continue
            for rre, pre, spec in PIN_SEEDS.get(self.name, []):
                if any(re.match(rre, r) and re.match(pre, p) for r, p in nodes):
                    seeds[net] = spec
        for net in seeds:
            if net not in self.nets:
                raise SystemExit("%s: seeded net %s is not in the netlist -- the board changed" % (self.name, net))
        todo = [n for n in self.nets if n not in self.L]
        while todo:
            progress = False
            for strict in (True, False):
                for net in list(todo):
                    lv = self.from_spec(seeds[net]) if net in seeds else self.try_auto(net, strict)
                    if lv is not None:
                        self.L[net] = lv
                        todo.remove(net)
                        progress = True
                        if not strict:
                            break
                if progress:
                    break
            if not progress:
                break
        for net in todo:
            self.unresolved.append(net)
            self.L[net] = self.mk(why="UNRESOLVED: nothing in the netlist sets this net")
            self.L[net]["unres"] = True

    # -- judging ---------------------------------------------------------------------------
    def expr(self, ref, e, field=None):
        """(limit at steady, at transient, at fault). A limit written against the IC's own
        supply ("VIN+0.3") moves with that supply, so each level is judged against its own."""
        if e is None:
            return None
        if isinstance(e, (int, float)):
            return (e, e, e)
        m = re.fullmatch(r"([A-Za-z0-9_.]+)\+([\d.]+)", e)
        s = self.L[self.supply_net(ref, m.group(1))]
        off = float(m.group(2))
        return (s["v"] + off, s["vt"] + off, s["vf"] + off)

    @staticmethod
    def judge(v, vt, vf, mx, rec=None, lo=0.0, mn=None):
        m0, m1, m2 = mx if isinstance(mx, tuple) else (mx, mx, mx)
        if v > m0 + EPS:
            return "FAIL"
        if vt > m1 + EPS:
            return "SUSPECT"
        if rec is not None and v > rec + EPS:
            return "SUSPECT"
        if mn is not None and lo < mn - EPS:
            return "SUSPECT"
        if vf > m2 + EPS:
            return "FAULT"
        return "OK"

    def row(self, ref, pin, name, net, v, vt, vf, rating, rkind, verdict, note="", margin=None):
        c = self.comps[ref]
        p = part_of(c)
        if margin is None and isinstance(rating, (int, float)) and vt is not None:
            margin = rating - vt
        self.rows.append(dict(
            board=self.name, ref=ref, pin=pin, name=name, net=net, v=v, vt=vt, vf=vf,
            rating=rating, rkind=rkind, verdict=verdict, note=note, margin=margin,
            two=(p or {}).get("kind") in ("cap", "res", "diode", "tvs", "zener", "led", "pd"),
            code=c["code"] or "", mpn=(p or {}).get("mpn", c["value"]),
            src=(p or {}).get("src", "no LCSC code / no rating applies")))

    def find(self, sev, ref, text):
        self.finds.append((sev, ref, text))

    def across(self, ref):
        """(v, vt, vf, how) across a two-terminal part."""
        c = self.comps[ref]
        (p1, n1), (p2, n2) = sorted(c["pins"].items())[:2]
        a, b = self.L[n1], self.L[n2]
        ov = CAP_ACROSS.get(self.name, {}).get(ref)
        if ov:
            if ov[0] == "fixed":
                return ov[1], ov[1], ov[1], ov[2]
            if ov[0] == "div":
                k = self.R(ov[2]) / (self.R(ov[2]) + self.R(ov[3]))
                s = self.L[ov[1]]
                return s["v"] * k, s["vt"] * k, s["vf"] * k, ov[4]
        if n1 in GNDS or n2 in GNDS:
            s = b if n1 in GNDS else a
            return max(s["v"], -s["lo"]), max(s["vt"], -s["lo"]), max(s["vf"], -s["lo"]), "to ground"
        f = lambda k: max(a[k] - b["lo"], b[k] - a["lo"])
        return f("v"), f("vt"), f("vf"), "bound: one end at its highest, the other at its lowest"

    def check(self):
        for ref in sorted(self.comps, key=lambda r: (re.sub(r"\d.*", "", r), int(re.sub(r"\D", "", r) or 0), r)):
            c = self.comps[ref]
            k = kind_of(ref, c)
            p = part_of(c)
            getattr(self, "chk_" + k, self.chk_unknown)(ref, c, p)
        self.chk_currents()
        for net in self.unresolved:
            self.find("UNVERIFIED", "-", "net %s is UNRESOLVED (%s): seed it" % (
                net, " ".join("%s.%s" % n for n in self.nets[net])))

    def pins_sorted(self, c):
        return sorted(c["pins"].items(), key=lambda kv: (len(kv[0]), kv[0]))

    def chk_unknown(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            sev = "UNVERIFIED" if s["vt"] > 0 else "OK"
            self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], None, "none", sev,
                     "no rating in voltage_ratings.json for %s (%s)" % (c["code"] or "no LCSC code", c["value"]))
        if any(self.L[n]["vt"] > 0 for n in c["pins"].values()):
            self.find("UNVERIFIED", ref, "%s (%s): no rating entry" % (c["value"], c["code"]))

    def chk_tp(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            self.row(ref, pin, "pad", net, s["v"], s["vt"], s["vf"], None, "n/a", "OK", "bare copper")

    chk_jumper = chk_tp

    def chk_xtal(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], None, "n/a", "OK", "no voltage rating applies")

    def chk_cap(self, ref, c, p):
        v, vt, vf, how = self.across(ref)
        rated = p["v"]
        frac = v / rated
        cls2 = p["diel"] in ("X5R", "X7R")
        sev, note = "OK", how
        if v > rated + EPS:
            sev, note = "FAIL", "%.1f V steady across a %g V part" % (v, rated)
        elif vt > rated + EPS:
            sev, note = "SUSPECT", "transient %.1f V across a %g V part" % (vt, rated)
        elif frac > 0.8 or (cls2 and frac > 0.6 and v >= 12):
            sev, note = "SUSPECT", "%.0f %% of rating steady (%s %s %s)" % (frac * 100, p["c"], p["diel"], p["case"])
        elif vf > rated + EPS:
            sev, note = "FAULT", "fault level %.1f V across a %g V part" % (vf, rated)
        if cls2 and frac >= 0.4 and sev == "OK":
            note += "; %s %s at %.0f %% of rating: expect a large DC-bias capacitance loss" % (p["diel"], p["case"], frac * 100)
        for pin, net in self.pins_sorted(c):
            self.row(ref, pin, "across", net, v, vt, vf, rated, "rated V", sev, note)
        if sev != "OK":
            self.find(sev, ref, "%s %s %s %gV (%s) on %s: %s" % (
                p["c"], p["diel"], p["case"], rated, c["code"], "/".join(c["pins"].values()), note))

    def chk_res(self, ref, c, p):
        v, vt, vf, how = self.across(ref)
        r = p["ohm"]
        sev, note = "OK", ""
        if vt > p["v"] + EPS:
            sev, note = ("FAIL" if v > p["v"] + EPS else "SUSPECT"), "%.1f V across a %g V element" % (vt, p["v"])
        pw = None
        if r and r > 0:
            bound = v * v / r
            led = self.led_series(ref)
            model = RES_MODEL.get(self.name, {}).get(ref)
            if led:
                i = led[1]
                pw = i * i * r
                note2 = "LED ballast: %.1f mA at 100 %% duty -> %.0f mW of %.0f mW (%.0f mW at 50 %% duty)" % (
                    i * 1e3, pw * 1e3, p["p"] * 1e3, pw * 500)
            elif model:
                val = model[1](self.lvl_fn, self.R) if callable(model[1]) else model[1]
                pw = (val * val / r) if model[0] == "v" else (val * val * r)
                note2 = "%.1f mW of %.0f mW -- %s" % (pw * 1e3, p["p"] * 1e3, model[2])
            elif bound <= 0.5 * p["p"]:
                pw = bound
                note2 = "<= %.1f mW of %.0f mW (bound: full net swing across it)" % (pw * 1e3, p["p"] * 1e3)
            else:
                note2 = "bound %.0f mW exceeds half the %.0f mW rating and no load model is declared" % (
                    bound * 1e3, p["p"] * 1e3)
                if sev == "OK":
                    sev = "UNVERIFIED"
            if pw is not None:
                if pw > p["p"] + EPS:
                    sev = "FAIL" if not led else "SUSPECT"
                elif pw > 0.8 * p["p"] and sev == "OK":
                    sev = "SUSPECT"
            note = (note + "; " if note else "") + note2
            if sev == "OK" and vf > vt + EPS and (vf * vf / r) > p["p"]:
                sev = "FAULT"
                note += "; under the fault level %.1f V it dissipates up to %.1f W" % (vf, vf * vf / r)
            elif sev == "OK" and vf > p["v"] + EPS:
                sev = "FAULT"
                note += "; the fault level %.1f V is over its %g V element rating" % (vf, p["v"])
        for pin, net in self.pins_sorted(c):
            self.row(ref, pin, "across", net, v, vt, vf, p["v"], "element V", sev, note)
        if sev != "OK":
            self.find(sev, ref, "%s %s %.0f mW (%s) %s-%s: %s" % (
                c["value"], p["case"], p["p"] * 1e3, c["code"], *list(c["pins"].values())[:2], note))

    def lvl_fn(self, net):
        return self.L[net]

    def led_series(self, ref):
        """(led ref, amps) if this resistor feeds exactly one LED from a rail."""
        c = self.comps[ref]
        for pin, net in c["pins"].items():
            others = [(r, q) for r, q in self.nets[net] if r != ref]
            if len(others) == 1 and kind_of(others[0][0], self.comps[others[0][0]]) == "led":
                led = part_of(self.comps[others[0][0]])
                rail = [n for q, n in c["pins"].items() if q != pin][0]
                return others[0][0], (self.L[rail]["v"] - led["vf"]) / self.R(ref)
        return None

    def chk_conn(self, ref, c, p):
        worst = "OK"
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            if p["v"] is None:
                sev = "UNVERIFIED" if s["vf"] > 0 else "OK"
                self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], None, "none", sev, "no voltage rating published")
            else:
                pk = p.get("v_peak", p["v"])           # the maker's withstand figure, if it gives one
                sev = self.judge(s["v"], s["vt"], s["vf"], (p["v"], pk, pk))
                self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], p["v"], "rated V", sev)
            if sev != "OK" and worst == "OK":
                worst = sev
                self.find(sev, ref, "%s (%s) pin %s on %s: %.1f / %.1f / %.1f V (steady/transient/fault) against %s" % (
                    c["value"], c["code"], pin, net, s["v"], s["vt"], s["vf"],
                    ("%g V" % p["v"]) if p["v"] else "no published voltage rating"))

    def chk_fuse(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            sev = self.judge(s["v"], s["vt"], s["vf"], p["v"])
            self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], p["v"], "rated V", sev, "voltage it must interrupt")
            if sev != "OK":
                self.find(sev, ref, "fuse %s on %s: %.1f V against %g V" % (c["value"], net, s["vt"], p["v"]))

    def chk_bead(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], None, "n/a", "OK", "no voltage rating applies; current checked below")

    chk_ind = chk_bead

    def chk_switch(self, ref, c, p):
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            pk = p.get("v_peak", p["v"])               # not switching: its non-switch rating
            sev = self.judge(s["v"], s["vt"], s["vf"], (p["v"], pk, pk))
            self.row(ref, pin, "", net, s["v"], s["vt"], s["vf"], p["v"], "rated V", sev)
            if sev != "OK":
                self.find(sev, ref, "%s on %s: %.1f / %.1f / %.1f V against %g V" % (
                    c["value"], net, s["v"], s["vt"], s["vf"], p["v"]))

    def chk_relay(self, ref, c, p):
        coil = [c["pins"][q] for q in p["coil"]]
        hi = min(self.L[n]["vt"] for n in coil)        # the supply side; the other end is the driver's
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            if pin in p["coil"]:
                sev = self.judge(hi, hi, hi, p["coil_max"])
                self.row(ref, pin, "coil", net, hi, hi, hi, p["coil_max"], "coil max", sev,
                         "coil sees its supply, %.2f V (the turn-off spike is across the driver, not the coil)" % hi)
            else:
                sev = self.judge(max(s["v"], -s["lo"]), max(s["vt"], -s["lo"]), s["vf"], p["contact_v"])
                self.row(ref, pin, "contact", net, s["v"], s["vt"], s["vf"], p["contact_v"], "switching V", sev)
            if sev != "OK":
                self.find(sev, ref, "relay pin %s on %s: %.1f V" % (pin, net, s["vt"]))

    def k_a(self, c, p):
        inv = {v: k for k, v in p["pins"].items()}
        return c["pins"][inv["K"]], c["pins"][inv["A"]], inv

    def chk_diode(self, ref, c, p):
        kn, an, inv = self.k_a(c, p)
        k, a = self.L[kn], self.L[an]
        v, vt, vf = k["v"] - a["lo"], k["vt"] - a["lo"], k["vf"] - a["lo"]
        sev = self.judge(v, vt, vf, p["vr"])
        note = "reverse voltage, cathode %s to anode %s" % (kn, an)
        if sev == "SUSPECT" and kn in self.L and k["vt"] >= V24_CLAMP - EPS:
            note += "; the rail clamp reaches %g V at about %.1f A of surge" % (p["vr"], tvs_amps_at(p["vr"]))
        for pin, net in self.pins_sorted(c):
            self.row(ref, pin, "K" if pin == inv["K"] else "A", net, v, vt, vf, p["vr"], "VRRM", sev, note)
        if sev != "OK":
            self.find(sev, ref, "%s (%s) VR %g V: %.1f V steady, %.1f V transient -- %s" % (
                c["value"], c["code"], p["vr"], v, vt, note))

    def chk_tvs(self, ref, c, p):
        nets = [n for _, n in self.pins_sorted(c)]
        hot = [n for n in nets if n not in GNDS]
        net = hot[0] if hot else nets[0]
        s = self.L[net]
        v = max(s["v"], -s["lo"]) if p["bidir"] else s["v"]
        sev, note = "OK", "stand-off %g V against the net's steady %.2f V" % (p["vrwm"], v)
        if v > p["vbr_min"] + EPS:
            sev, note = "FAIL", "steady %.2f V is above its minimum breakdown %g V: it conducts continuously" % (v, p["vbr_min"])
        elif v > p["vrwm"] + EPS:
            sev = "SUSPECT"
            note = "steady %.2f V is above its %g V stand-off (breakdown from %g V): leakage%s, no margin" % (
                v, p["vrwm"], p["vbr_min"], (" up to %g uA at stand-off" % p["ir_ua"]) if p.get("ir_ua") else "")
        elif s["vf"] > p["vbr_min"] and s["vf"] > s["vt"] + EPS:
            sev = "FAULT"
            note = ("a sustained %.1f V fault on %s drives it into breakdown with nothing limiting the current "
                    "(rated %s)" % (s["vf"], net, "%g mW continuous" % (p["p_cont"] * 1e3) if p.get("p_cont") else "for pulses only"))
        for pin, n in self.pins_sorted(c):
            self.row(ref, pin, "", n, s["v"], s["vt"], s["vf"], p["vrwm"], "stand-off (vs steady)", sev, note,
                     margin=p["vrwm"] - v)
        if sev != "OK":
            self.find(sev, ref, "%s (%s) on %s: %s" % (c["value"], c["code"], net, note))

    def chk_zener(self, ref, c, p):
        kn, an, inv = self.k_a(c, p)
        feed = ZENER_FEED.get(self.name, {}).get(ref)
        sev, note = "UNVERIFIED", "no feed declared for this zener"
        if feed:
            rs = sum(self.R(r) for r in feed[1])
            s = self.L[feed[0]]
            pw = (s["v"] - p["vz_min"]) / rs * p["vz_max"]
            pwt = (s["vt"] - p["vz_min"]) / rs * p["vz_max"]
            sev = "FAIL" if pw > p["p"] else ("SUSPECT" if pwt > p["p"] else "OK")
            note = "%.0f mW steady, %.0f mW at the transient, of %.0f mW (fed from %s through %.1f k)" % (
                pw * 1e3, pwt * 1e3, p["p"] * 1e3, feed[0], rs / 1e3)
        for pin, net in self.pins_sorted(c):
            s2 = self.L[net]
            self.row(ref, pin, "K" if pin == inv["K"] else "A", net, s2["v"], s2["vt"], s2["vf"], None, "power", sev, note)
        if sev != "OK":
            self.find(sev, ref, "%s: %s" % (c["value"], note))

    def chk_led(self, ref, c, p):
        kn, an, inv = self.k_a(c, p)
        i = None
        for r, q in self.nets[an]:
            if r != ref and kind_of(r, self.comps[r]) == "res":
                rail = [n for q2, n in self.comps[r]["pins"].items() if q2 != q][0]
                i = (self.L[rail]["v"] - p["vf"]) / self.R(r)
        if i is None:
            sev, note = "UNVERIFIED", "no ballast found"
        else:
            sev = "FAIL" if i > p["if"] else ("SUSPECT" if i > 0.8 * p["if"] else "OK")
            note = "%.1f mA of %.0f mA DC, %.0f mW of %.0f mW (VF typ %.1f V)" % (
                i * 1e3, p["if"] * 1e3, i * p["vf"] * 1e3, p["p"] * 1e3, p["vf"])
        for pin, net in self.pins_sorted(c):
            s = self.L[net]
            self.row(ref, pin, "K" if pin == inv["K"] else "A", net, s["v"], s["vt"], s["vf"], None, "IF", sev, note)
        if sev != "OK":
            self.find(sev, ref, "%s: %s" % (c["value"], note))

    def chk_pd(self, ref, c, p):
        kn, an, inv = self.k_a(c, p)
        k, a = self.L[kn], self.L[an]
        v = max(k["vt"] - a["lo"], a["vt"] - k["lo"])
        sev = self.judge(v, v, v, p["vr"])
        for pin, net in self.pins_sorted(c):
            self.row(ref, pin, "K" if pin == inv["K"] else "A", net, v, v, v, p["vr"], "VR", sev,
                     "bound: either net at its highest, the other at 0")
        if sev != "OK":
            self.find(sev, ref, "photodiode reverse %.1f V against %g V" % (v, p["vr"]))

    def chk_fet(self, ref, c, p):
        inv = {v: k for k, v in p["pins"].items()}
        g, d, s = (self.L[c["pins"][inv[x]]] for x in "GDS")
        vds = [max(d[k] - s["lo"], s[k] - d["lo"]) for k in ("v", "vt", "vf")]
        ov = FET_VGS.get(self.name, {}).get(ref)
        if ov:
            kk = self.R(ov[2]) / (self.R(ov[2]) + self.R(ov[3]))
            src = self.L[ov[1]]
            vgs = [src[k] * kk for k in ("v", "vt", "vf")]
            how = ov[4]
        else:
            vgs = [max(g[k] - s["lo"], s[k] - g["lo"]) for k in ("v", "vt", "vf")]
            how = "bound: gate net at its highest with the source at its lowest"
        sd = self.judge(*vds, p["vds"])
        sg = self.judge(*vgs, p["vgs"])
        for pin, net in self.pins_sorted(c):
            nm = p["pins"][pin]
            if nm == "G":
                self.row(ref, pin, "G", net, *vgs, p["vgs"], "VGS", sg, how)
            elif nm == "D":
                self.row(ref, pin, "D", net, *vds, p["vds"], "VDS", sd, "drain-source, either polarity")
            else:
                self.row(ref, pin, "S", net, self.L[net]["v"], self.L[net]["vt"], self.L[net]["vf"], None, "n/a", "OK", "reference terminal")
        if sd != "OK":
            self.find(sd, ref, "%s (%s) VDS %.1f / %.1f V against %g V" % (c["value"], c["code"], vds[0], vds[1], p["vds"]))
        if sg != "OK":
            self.find(sg, ref, "%s (%s) VGS %.1f / %.1f V against +/-%g V -- %s" % (c["value"], c["code"], vgs[0], vgs[1], p["vgs"], how))

    def chk_ic(self, ref, c, p):
        agg = collections.OrderedDict()
        for pin, net in self.pins_sorted(c):
            ps, _ = self.pinspec(ref, pin)
            s = self.L[net]
            if ps is None:
                self.row(ref, pin, "?", net, s["v"], s["vt"], s["vf"], None, "none",
                         "OK" if s.get("nc") else "UNVERIFIED", "pin not in the ratings entry")
                if not s.get("nc"):
                    self.find("UNVERIFIED", ref, "%s pin %s on %s: not in the ratings entry for %s" % (c["value"], pin, net, c["code"]))
                continue
            name = ps.get("n", "")
            if ps.get("gnd") and net in GNDS:
                self.row(ref, pin, name, net, 0.0, 0.0, 0.0, None, "n/a", "OK", "ground")
                continue
            if ps.get("boot"):
                self.row(ref, pin, name, net, s["v"], s["vt"], s["vf"], None, "n/a", "OK",
                         "bootstrap node, rated %s and set by the IC itself" % ps["max"])
                continue
            lim = self.expr(ref, ps.get("max"))
            mx = lim[1] if lim else None
            if mx is None:
                if "internal" in ps or s.get("nc") or name == "NC":
                    self.row(ref, pin, name, net, s["v"], s["vt"], s["vf"], None, "n/a", "OK",
                             "generated inside the IC" if "internal" in ps else "not connected")
                else:
                    self.row(ref, pin, name, net, s["v"], s["vt"], s["vf"], None, "none", "UNVERIFIED", "no rating for this pin")
                    self.find("UNVERIFIED", ref, "%s pin %s (%s) on %s: no rating" % (c["value"], pin, name, net))
                continue
            sev = self.judge(s["v"], s["vt"], s["vf"], lim, ps.get("rec"), s["lo"], ps.get("min"))
            if s.get("unres"):
                sev = "UNVERIFIED"
            note = ""
            if isinstance(ps.get("max"), str):
                note = "abs max %s" % ps["max"]
            if ps.get("rec_only"):
                note = "operating limit (no abs max published)"
            if ps.get("rec") is not None:
                note += ("; " if note else "") + "recommended max %g V" % ps["rec"]
            if ps.get("note"):
                note += "; " + ps["note"]
            if sev in ("SUSPECT", "FAIL") and s["vt"] > mx and s["vt"] >= V24_CLAMP - EPS and mx > V24_SUSTAIN:
                note += "; the rail clamp reaches %g V at about %.1f A of surge" % (mx, tvs_amps_at(mx))
            if sev == "SUSPECT" and s["vt"] <= mx + EPS and ps.get("rec") is not None and s["v"] > ps["rec"]:
                note += "; steady %.2f V is above the recommended maximum" % s["v"]
            if sev != "OK" and s.get("rsrc"):
                over = (s["vf"] - lim[2]) if sev == "FAULT" else (s["vt"] - mx)
                note += "; it arrives through %.0f k, so about %.0f uA into the pin's clamp" % (s["rsrc"] / 1e3, over / s["rsrc"] * 1e6)
            if sev == "SUSPECT" and ps.get("min") is not None and s["lo"] < ps["min"]:
                note += "; net goes to %.1f V, below the %.1f V minimum" % (s["lo"], ps["min"])
            self.row(ref, pin, name, net, s["v"], s["vt"], s["vf"], mx, "abs max" if not ps.get("rec_only") else "operating", sev, note)
            if sev != "OK":
                shown = lim[2] if sev == "FAULT" else mx
                agg.setdefault(sev, []).append("pin %s %s on %s: %.2f steady / %.2f transient%s against %.2f V%s" % (
                    pin, name, net, s["v"], s["vt"], (" / %.2f fault" % s["vf"]) if s["vf"] > s["vt"] + EPS else "",
                    shown, (" (%s)" % note) if note else ""))
        for sev, items in agg.items():
            self.find(sev, ref, "%s (%s) -- %s" % (c["value"], c["code"], "; ".join(items)))

    def chk_currents(self):
        for ref, n, amps, why in CURRENTS.get(self.name, []):
            c = self.comps[ref]
            p = part_of(c)
            k = p["kind"]
            if k == "conn":
                if p["i"] is None:
                    self.find("UNVERIFIED", ref, "%s: no current rating" % c["value"])
                    continue
                lim, what = p["i"] * n, "%d x %g A contact%s" % (n, p["i"], "s" if n > 1 else "")
                thr = 0.8
            elif k == "fuse":
                lim, what, thr = p["i"], "%g A fuse" % p["i"], 0.75
            elif k == "bead":
                lim, what, thr = p["i"], "%g A rated" % p["i"], 0.8
            elif k == "ind":
                lim, what, thr = min(p["isat"], p["itemp"]), "min(Isat %g, Itemp %g) A" % (p["isat"], p["itemp"]), 0.8
            elif k == "switch":
                lim, what, thr = p["i"], "%g mA non-switch rating (it is set with the bus idle%s)" % (
                    p["i"] * 1e3, "; %g mA while switching" % (p["i_sw"] * 1e3) if p.get("i_sw") else ""), 0.8
            elif k == "fet":
                lim, what, thr = p["id"], "ID %g A" % p["id"], 0.8
            else:
                continue
            frac = amps / lim
            sev = "FAIL" if frac > 1 + EPS else ("SUSPECT" if frac >= thr - EPS else "OK")
            text = "%s (%s) carries %.3g A against %s = %.0f %% -- %s" % (c["value"], c["code"], amps, what, frac * 100, why)
            self.currents.append((ref, amps, lim, frac, sev, text))
            if sev != "OK":
                self.find(sev, ref, "CURRENT: " + text)

    currents = None


# ── report ────────────────────────────────────────────────────────────────────────────────
def fnum(x):
    return "" if x is None else ("%.2f" % x)


def git_head(elec):
    try:
        return subprocess.check_output(["git", "-C", elec, "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


SEV_ORDER = ("FAIL", "SUSPECT", "FAULT", "UNVERIFIED")


def run(elec, names, write):
    done, out = {}, []
    for name in ORDER:                                  # every board resolves: sinks need sources
        b = Board(elec, name, done)
        b.currents = []
        b.check()
        done[name] = b
    head = git_head(elec)
    W = out.append
    W("# Voltage on every pin against its rating")
    W("")
    W("Generated by `elec/voltage_check.py` from the netlists and fab BOMs in "
      "`%s` at commit `%s`. Ratings: `voltage_ratings.json` (keyed by LCSC code, each with its source). "
      "Do not edit this file; edit the seeds in the script or the ratings and run it again." % (
          os.path.relpath(elec, os.path.join(HERE, "..", "..")).replace("\\", "/"), head))
    W("")
    W("Three levels per net: **steady** worst case (derating is judged on it), **transient** worst case "
      "(absolute maxima are judged on it) and a credible **single fault**. FAIL = steady over a rating. "
      "SUSPECT = transient over a rating, steady over a recommended limit, or under-derated. "
      "FAULT = only the single-fault level is over. UNVERIFIED = no rating could be read.")
    W("")
    W("## The 24 V rail, as assumed")
    W("")
    W("| level | volts | basis |")
    W("|---|---|---|")
    W("| brick, in tolerance | %.2f | %s |" % (V24_BRICK, BRICK["src"]))
    W("| steady worst case | %.1f | 24 V + 10 %% (the brief's figure): tolerance plus regeneration lifting the rail below any clamp |" % V24_STEADY)
    W("| brick OVP ceiling | %.1f | 135 %% of rated, hiccup |" % (BRICK["vnom"] * BRICK["ovp_max_frac"]))
    W("| clamp does nothing below | %.1f to %.1f | the rail clamp's breakdown at 1 mA (D8 on motor_ctrl, D6 on output_panel): regeneration can hold the rail anywhere under this |" % (RAIL_TVS["vbr_min"], RAIL_TVS["vbr_max"]))
    W("| transient worst case | %.1f | %s at the brick's %.2f A, the most the rail can be handed. Its catalogue VC is %.1f V at %.1f A (10/1000 us); linear in between, about %.2f A of surge per volt above %.1f V |" % (
        V24_CLAMP, RAIL_TVS["mpn"], BRICK["i"], V24_VC, RAIL_TVS["ipp"], RAIL_TVS["ipp"] / (V24_VC - V24_SUSTAIN), V24_SUSTAIN))
    W("| live plug, undamped | %.1f | twice the brick: only where a connector feeds bare ceramic (output_panel +24V_IN) |" % V24_LIVE_PLUG)
    W("")
    W("## Summary")
    W("")
    W("| board | parts | pins | rated and checked | no rating applies | UNVERIFIED | FAIL | SUSPECT | FAULT |")
    W("|---|---|---|---|---|---|---|---|---|")
    total_fail = 0
    stats = {}
    for name in BOARDS:
        b = done[name]
        n = len(b.rows)
        unv = sum(1 for r in b.rows if r["verdict"] == "UNVERIFIED")
        na = sum(1 for r in b.rows if r["rkind"] == "n/a")
        chk = n - unv - na
        cnt = collections.Counter(s for s, _, _ in b.finds)
        total_fail += cnt["FAIL"]
        stats[name] = (n, chk, na, unv, cnt)
        W("| %s | %d | %d | %d | %d | %d | %d | %d | %d |" % (
            name, len(b.comps), n, chk, na, unv, cnt["FAIL"], cnt["SUSPECT"], cnt["FAULT"]))
    W("")
    W("\"No rating applies\" is ground pins, bare test pads, crystals, ferrite/inductor terminals (their check is current), "
      "and nodes an IC generates for itself. The FAIL/SUSPECT/FAULT columns count findings (a part, not a pin).")
    W("")
    W("## What this does not cover")
    W("")
    for line in (
        "Pin maps are the netlists' own: a part wired to the wrong pin is rated as if the pin were right (pinout is a separate check).",
        "5 V-tolerant (FT) pins are not credited on either MCU or the hub; every I/O is held to VDD + 0.3 V (CH32V307), 4.0 V (STM32H743) or VDD33 + 0.4 V (CH334).",
        "Below-ground excursions are carried only where seeded (the DAC's ground-centred output, the charge pump, the jack). Ground shift along the motor trunk, ESD and buck switch-node undershoot are not modelled.",
        "Currents are the boards' own declared figures set beside the part's rating; they are not re-derived here.",
        "Bus A's level assumes a 5 V transceiver inside the SERVO42D; the Pi's 3V3 tolerance and its GPIO limits were not looked up; the pickup input is assumed under 5 V peak.",
        "Capacitor value strings understate three parts and the script uses the ordered code, not the string: '22uF/16V' C45783, '10uF/16V' C15850 and '1uF/16V' C52923 are all 25 V parts.",
        "Every 24 V capacitor is a 50 V part: 53 % at the 26.4 V steady case (inside the 60 % line), 74 % at the 36.8 V the clamp allows indefinitely. The X5R/X7R ones lose a large share of their value at that bias, most in 0402 and 0805.",
    ):
        W("- " + line)
    W("")
    used_notes = set()
    for name in BOARDS:
        b = done[name]
        W("## %s" % name)
        W("")
        for sev in SEV_ORDER:
            items = [(r, t) for s, r, t in b.finds if s == sev]
            W("### %s (%d)" % (sev, len(items)))
            W("")
            if not items:
                W("None.")
            # fold identical findings that differ only in ref
            folded = collections.OrderedDict()
            for r, t in items:
                key = re.sub(r"\b[A-Za-z_$+0-9]*\d+[A-Za-z_0-9]*\b", "#", t)
                folded.setdefault(key, []).append((r, t))
            notes = REVIEW_NOTES.get(name, {})
            said = set()
            for key, grp in folded.items():
                refs = [g[0] for g in grp]
                if len(grp) > 3:
                    W("- **%s** (%d parts: %s ... %s) -- e.g. %s" % (refs[0], len(refs), refs[0], refs[-1], grp[0][1]))
                else:
                    for r, t in grp:
                        W("- **%s** -- %s" % (r, t))
                for r in refs:
                    if (r, sev) in notes and (r, sev) not in said:
                        said.add((r, sev))
                        used_notes.add((name, r, sev))
                        W("  - *note:* %s" % notes[(r, sev)])
            W("")
        W("### Currents")
        W("")
        if b.currents:
            W("| ref | amps | limit | use | verdict | basis |")
            W("|---|---|---|---|---|---|")
            for ref, amps, lim, frac, sev, text in b.currents:
                W("| %s | %.3g | %.3g | %.0f %% | %s | %s |" % (ref, amps, lim, frac * 100, sev, text.split(" -- ", 1)[1]))
        W("")
        W("### Net levels and where they come from")
        W("")
        W("| net | lo | steady | transient | fault | basis |")
        W("|---|---|---|---|---|---|")
        shown = 0
        seeded = set(SEEDS.get(name, {}))
        for net in sorted(b.L, key=lambda n: (-b.L[n]["vt"], n)):
            s = b.L[net]
            if s.get("nc") or net in GNDS:
                continue
            if net not in seeded and s["vt"] < 5.6 and not s.get("unres") and s["lo"] >= 0:
                continue                  # the propagated low-voltage signal nets are in the CSV
            W("| %s | %s | %.2f | %.2f | %s | %s |" % (
                net, ("%.1f" % s["lo"]) if s["lo"] else "", s["v"], s["vt"],
                ("%.2f" % s["vf"]) if s["vf"] > s["vt"] + EPS else "", s["why"].replace("|", "/")))
            shown += 1
        W("")
        W("(seeded nets and every net above 5.6 V; all %d nets are in `voltage_pins_%s.csv`)" % (len(b.L), name))
        W("")
        W("### Smallest margins")
        W("")
        W("Margin = rating minus the TRANSIENT level (a clamp's stand-off: minus the STEADY level). "
          "Two-terminal parts are shown once, with the voltage ACROSS them; identical cases are folded.")
        W("")
        W("| ref | pin | net | steady | transient | fault | rating | kind | margin | verdict | note |")
        W("|---|---|---|---|---|---|---|---|---|---|---|")
        rated = sorted((r for r in b.rows if r["margin"] is not None), key=lambda r: r["margin"])
        groups, seen_ref = collections.OrderedDict(), set()
        for r in rated:
            if r["two"]:
                if r["ref"] in seen_ref:
                    continue
                seen_ref.add(r["ref"])
            sig = (r["mpn"], r["name"], round(r["margin"], 2), r["verdict"], round(r["vt"], 2))
            groups.setdefault(sig, []).append(r)
        for k, grp in enumerate(groups.values()):
            if k >= 40:
                break
            r = grp[0]
            more = (" (+%d alike: %s)" % (len(grp) - 1, ", ".join(sorted({g["ref"] for g in grp[1:]})[:6]) +
                                            (" ..." if len({g["ref"] for g in grp[1:]}) > 6 else ""))) if len(grp) > 1 else ""
            W("| %s | %s | %s | %s | %s | %s | %s | %s | %.2f | %s | %s |" % (
                r["ref"], r["pin"] + (" " + r["name"] if r["name"] else ""), r["net"], fnum(r["v"]), fnum(r["vt"]),
                fnum(r["vf"]) if r["vf"] > r["vt"] + EPS else "", fnum(r["rating"]), r["rkind"], r["margin"],
                r["verdict"], ((r["mpn"] + ": " + r["note"]).replace("|", "/")[:170] + more)))
        W("")
        W("(the 40 tightest distinct cases; the full per-pin table, %d rows sorted by margin, is `voltage_pins_%s.csv`)" % (len(b.rows), name))
        W("")
        if write:
            os.makedirs(OUT, exist_ok=True)
            path = os.path.join(OUT, "voltage_pins_%s.csv" % name)
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["ref", "pin", "pin_name", "net", "v_steady", "v_transient", "v_fault", "rating",
                            "rating_kind", "margin", "verdict", "note", "lcsc", "mpn", "net_basis", "rating_source"])
                for r in sorted(b.rows, key=lambda r: (r["margin"] is None, r["margin"] if r["margin"] is not None else 0)):
                    w.writerow([r["ref"], r["pin"], r["name"], r["net"], fnum(r["v"]), fnum(r["vt"]), fnum(r["vf"]),
                                fnum(r["rating"]), r["rkind"], fnum(r["margin"]), r["verdict"], r["note"], r["code"],
                                r["mpn"], b.L[r["net"]]["why"], r["src"]])
    stale = [(bn, r, sv) for bn, d_ in REVIEW_NOTES.items() for (r, sv) in d_ if (bn, r, sv) not in used_notes]
    for bn, r, sv in stale:
        print("stale reviewer note: %s %s %s no longer matches a finding -- delete it" % (bn, r, sv))
    return "\n".join(out) + "\n", total_fail, done, stats


def declare(b):
    """One board's A16 declarations (cadkit PCB_QUALITY.md A16) from a checked Board:
    {"net_volts": {...}, "pin_volts": {...}}.

    A net gets its steady and transient levels and the reason it has them. A pin gets the
    rating it was judged against, by ref.pin. A16 compares a pin's rating with its NET's
    level to ground, which is the same comparison as this script's for every rating that is
    one to ground. Where it is not -- a bootstrap pin rated to the switch node, a part
    judged on the voltage across it and standing above ground -- the pin is declared to
    have no net-to-ground rating and the `why` carries the stress and the limit it WAS
    judged on here. A pin this script could not rate is left out, so A16 fails on it."""
    def n3(x):
        return round(float(x) + 0.0, 3)
    nets = {}
    for net, s in sorted(b.L.items()):
        if net in GNDS:
            nets[net] = 0
            continue
        if s.get("unres"):
            continue                                   # undeclared: A16 says so
        v = max(s["v"], -s["lo"])
        d = {"v": n3(v), "why": s["why"]}
        if max(s["vt"], -s["lo"]) > v + EPS:
            d["peak"] = n3(max(s["vt"], -s["lo"]))
        nets[net] = d
    pins = {}
    for r in b.rows:
        key = "%s.%s" % (r["ref"], r["pin"])
        s = b.L[r["net"]]
        if r["net"] in GNDS:
            continue                                   # a 0 V net: A16 does not grade it
        nv, npk = max(s["v"], -s["lo"]), max(s["vt"], -s["lo"])
        c = b.comps[r["ref"]]
        p = part_of(c)
        kind = kind_of(r["ref"], c)
        src = "%s (%s): %s" % (r["mpn"], r["code"] or "no LCSC code", r["src"])
        rating = r["rating"]
        if r["verdict"] == "UNVERIFIED" and not isinstance(rating, (int, float)):
            continue
        if kind == "tvs":
            pins[key] = {
                "max": p["vbr_min"], "peak": "none", "src": src,
                "why": "this part IS the clamp on %s: it stands %g V (where its leakage is "
                       "specified) and starts to conduct at %g V, the figure a steady level "
                       "must stay under" % (r["net"], p["vrwm"], p["vbr_min"])}
            continue
        if not isinstance(rating, (int, float)):
            pins[key] = {"max": "none", "src": src,
                         "why": r["note"] or "no voltage rating applies to a %s" % kind}
            continue
        pk = (p or {}).get("v_peak") if kind in ("conn", "switch") else None
        if pk is not None and rating + EPS >= nv:
            pins[key] = {"max": n3(rating), "peak": n3(pk), "src": "%s -- %s" % (r["rkind"], src)}
        elif rating + EPS >= nv and rating + EPS >= npk:
            pins[key] = {"max": n3(rating), "src": "%s -- %s" % (r["rkind"], src)}
        elif r["verdict"] in ("OK", "FAULT"):
            pins[key] = {
                "max": "none", "src": src,
                "why": "its %s limit (%.4g V) is not one to ground: it was judged on %.4g V "
                       "steady, %.4g V transient%s"
                       % (r["rkind"], rating, r["v"], r["vt"],
                          " -- " + r["note"] if r["note"] else "")}
        else:                                          # over: let A16 say so
            pins[key] = {"max": n3(rating), "src": "%s -- %s" % (r["rkind"], src)}
    return {"net_volts": nets, "pin_volts": pins}


def main(argv):
    elec = DEFAULT_ELEC
    if "--elec" in argv:
        i = argv.index("--elec")
        elec = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    names = [a for a in argv if not a.startswith("-")] or list(BOARDS)
    write = set(names) == set(BOARDS)
    text, fails, done, stats = run(elec, names, write)
    if write:
        os.makedirs(OUT, exist_ok=True)
        with io.open(os.path.join(OUT, "voltage_ratings.md"), "w", encoding="utf-8") as fh:
            fh.write(text)
    if "--declare" in argv:
        os.makedirs(DECL, exist_ok=True)
        for name in names:
            with io.open(os.path.join(DECL, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(declare(done[name]), fh, indent=1, sort_keys=True, ensure_ascii=False)
                fh.write("\n")
    for name in names:
        b = done[name]
        n, chk, na, unv, cnt = stats[name]
        print("%-13s %4d pins: %4d checked, %3d n/a, %3d unverified | FAIL %d  SUSPECT %d  FAULT %d  UNVERIFIED %d" % (
            name, n, chk, na, unv, cnt["FAIL"], cnt["SUSPECT"], cnt["FAULT"], cnt["UNVERIFIED"]))
        if "-v" in argv or not write:
            for sev in SEV_ORDER:
                for s, r, t in b.finds:
                    if s == sev:
                        print("   %-10s %-6s %s" % (s, r, t))
    return fails


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
