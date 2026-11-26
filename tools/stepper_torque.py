"""A stepper's pull-out torque at speed, what one string's move needs, and the margin between them.

    py -3.12 tools/stepper_torque.py                          the 42CM06 at 1.4 A, 24 V: curve + margins
    py -3.12 tools/stepper_torque.py --motor 17HS16-2004S1 --ma 1400
    py -3.12 tools/stepper_torque.py --t90 39,45,50 --tension 128,158 --mu-factor 1.5
    py -3.12 tools/stepper_torque.py --curve-only --ma 2500    to set beside a datasheet curve

WHY (2026-11-25): the same model was typed out by hand about five times in one day for the
open-loop motor decision (OPENLOOP_BENCH.md, "Torque budget"). This is that model, once, with a
regression test against the one published curve we have.

THE MOTOR, per phase (2-phase hybrid, 50 pole pairs for 1.8 deg, 100 for 0.9):
  ke = holding / (sqrt2 x rated current)         V·s/rad = N·m/A(peak); holding is both phases on
  back-EMF E = ke w_mech, reactance X = w_elec L, the current I (peak = sqrt2 x RMS setting)
  The bridge can put at most --vbus (peak fundamental) across the phase: |E + I(R + jX)| <= V.
  Open loop lets the load angle settle anywhere, so the pull-out torque is the best ke I cos(th)
  over the current's lead th and any |I| up to the setting. Checked against Leadshine's own 24 V /
  2.5 A curve for the 42CM06: within 8 % from 500 to 2400 rpm (tools/test_stepper_torque.py).

THE MOVE, on the instrument: a constant-acceleration triangle of --turns motor turns. The closed
loop's 39 ms is a t90; a triangle reaches 90 % at 0.776 of its length, so a t90 maps to a move of
t90 / 0.776. Need = (rotor + --j-extra) x acceleration + the raise load at the motor:
  the Tr screw self-locks iff its friction mu >= tan(lead angle) cos(15 deg); --mu-factor times that
  threshold is the friction assumed; raising takes F d2/2 tan(lead angle + atan(mu / cos 15)) through
  the belt (--belt-eff). A self-locking screw is <= 50 % efficient: the load can never go under
  F x lead / pi.
Everything here is a model: what it prints is an estimate unless a bench number replaces it.
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np

# Published figures only; "src" says where each came from.
MOTORS = {
    "42CM06": dict(holding=0.6, amps=2.5, ohm=0.9, mh=1.6, rotor_gcm2=72, step_deg=1.8,
                   src="leadshine.com 42CM06 spec, read 2026-11-25 (the official motor)"),
    "17HS16-2004S1": dict(holding=0.45, amps=2.0, ohm=1.3, mh=2.6, rotor_gcm2=54, step_deg=1.8,
                          src="StepperOnline listing, 2026-11-24 report (holding, R, L); rotor typical"),
    "17HM19-2004S": dict(holding=0.46, amps=2.0, ohm=1.45, mh=4.0, rotor_gcm2=82, step_deg=0.9,
                         src="StepperOnline listing, 2026-11-24 report; rotor typical"),
}

# Leadshine's published 42CM06 curve at 24 V, 2.5 A RMS, read off the graph 2026-11-25: (rpm, N·m)
LEADSHINE_42CM06_24V = ((500, 0.60), (1000, 0.48), (1500, 0.30), (1600, 0.285), (2000, 0.215),
                        (2400, 0.195))

T90_OF_TRIANGLE = 1.0 - math.sqrt(0.05)          # 0.776: where a triangle has done 90 %


def ke(m: dict) -> float:
    return m["holding"] / (math.sqrt(2.0) * m["amps"])


def pullout(m: dict, rpm: float, amps_rms: float, vbus: float = 24.0, steps: int = 240) -> float:
    """The most torque (N·m) the motor holds at `rpm` with the current set to `amps_rms`."""
    k = ke(m)
    wm = rpm / 60.0 * 2.0 * math.pi
    pole_pairs = 50 if m["step_deg"] >= 1.8 else 100
    e, x, r = k * wm, pole_pairs * wm * m["mh"] * 1e-3, m["ohm"]
    th = np.linspace(-math.pi / 2, math.pi / 2, 721)
    best = 0.0
    for i in np.linspace(0.0, amps_rms * math.sqrt(2.0), steps):
        ok = np.abs(e + i * np.exp(1j * th) * (r + 1j * x)) <= vbus
        if ok.any():
            best = max(best, float((k * i * np.cos(th[ok])).max()))
    return best


def screw(tension_n: float, mu_factor: float = 1.5, lead_mm: float = 2.0, d2_mm: float = 7.0,
          belt_eff: float = 0.97) -> dict:
    """The raise load at the motor (N·m) of a Tr screw at mu_factor x its self-locking friction."""
    lam = math.atan(lead_mm / (math.pi * d2_mm))
    c15 = math.cos(math.radians(15.0))
    mu0 = math.tan(lam) * c15
    mu = mu_factor * mu0
    load = tension_n * d2_mm * 1e-3 / 2.0 * math.tan(lam + math.atan(mu / c15)) / belt_eff
    return dict(lead_deg=math.degrees(lam), mu_threshold=mu0, mu=mu, load=load,
                floor=tension_n * lead_mm * 1e-3 / math.pi / belt_eff)


def move(turns: float, t90_s: float, j_kgm2: float, load: float) -> dict:
    """A triangle with this t90: its length, acceleration, peak rpm and the torque it needs."""
    t = t90_s / T90_OF_TRIANGLE
    a = 4.0 * turns / t ** 2 * 2.0 * math.pi          # rad/s^2
    return dict(t=t, accel_rev=a / (2 * math.pi), peak_rpm=2.0 * turns / t * 60.0,
                need=j_kgm2 * a + load)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    a.add_argument("--motor", default="42CM06", choices=sorted(MOTORS))
    a.add_argument("--ma", type=int, default=1400, help="the driver's RMS current setting")
    a.add_argument("--vbus", type=float, default=24.0, help="peak fundamental the bridge applies")
    a.add_argument("--turns", type=float, default=0.52, help="motor turns per whole tone (closed-loop rig: 0.52)")
    a.add_argument("--t90", default="30,39,45,50", help="ms, comma list")
    a.add_argument("--tension", default="128,158", help="N at the end of the raise, comma list")
    a.add_argument("--mu-factor", type=float, default=1.5, help="nut friction / self-locking threshold")
    a.add_argument("--j-extra", type=float, default=10.0, help="g·cm^2 of pulleys, belt and screw")
    a.add_argument("--curve-only", action="store_true")
    o = a.parse_args(argv)
    try:                                               # "N·m" on a cp1252 Windows console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    m = MOTORS[o.motor]
    amps = o.ma / 1000.0
    print("%s at %.2f A RMS, %.0f V: ke %.3f V·s/rad  (%s)" % (o.motor, amps, o.vbus, ke(m), m["src"]))
    print("pull-out, N·m: " + "  ".join("%d rpm %.3f" % (r, pullout(m, r, amps, o.vbus))
                                       for r in (250, 500, 1000, 1250, 1600, 2000, 2400)))
    if o.curve_only:
        return 0
    j = (m["rotor_gcm2"] + o.j_extra) * 1e-7
    for f in [float(x) for x in o.tension.split(",")]:
        sc = screw(f, o.mu_factor)
        print("\n%3.0f N: lead angle %.2f deg, self-locks at mu >= %.3f; assumed mu %.3f -> raise load "
              "%.3f N·m (floor %.3f)" % (f, sc["lead_deg"], sc["mu_threshold"], sc["mu"], sc["load"], sc["floor"]))
        for t90 in [float(x) / 1000.0 for x in o.t90.split(",")]:
            mv = move(o.turns, t90, j, sc["load"])
            avail = pullout(m, mv["peak_rpm"], amps, o.vbus)
            print("  t90 %3.0f ms: %3.0f ms move, %4.0f rev/s^2, peak %4.0f rpm: need %.3f, have %.3f -> %.2fx"
                  % (t90 * 1e3, mv["t"] * 1e3, mv["accel_rev"], mv["peak_rpm"], mv["need"], avail, avail / mv["need"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
