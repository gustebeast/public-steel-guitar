"""Run one bench scenario and print what it found.

    python3 -m psgbench.bench step --sim
    python3 -m psgbench.bench sizes --motor 1 --string 3 --counts 400 --limit 2000 \\
        --link motor:/dev/ttyACM0 --optical /dev/ttyACM1,/dev/ttyACM2
    python3 -m psgbench.bench repeat --motor 1 --counts 400 --limit 500 --link can:can0 --wav take.wav

--link    motor:<port>   through the motor controller's USB (firmware/motor_ctrl)
          can:<channel>  through a USB-CAN adapter (socketcan)
--optical <control port>,<sample port>   the optical board (firmware/optical); --string says
          which string to listen to
--wav     a recording made some other way. It has to START when this program says "recording",
          to within what you can tolerate in the delay figures: nothing else lines it up.
--limit   the furthest, in encoder counts from where the motor stands, that this run may
          send it. Required with real hardware. The run is refused whole if it would go past.
--out     a folder: the raw recording, encoder readings and commands are saved there (.npz),
          so a run can be measured again later without being run again.
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np

from . import scenarios
from .run import run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenario", choices=sorted(scenarios.SCENARIOS))
    ap.add_argument("--sim", action="store_true", help="a pretend motor and string, no hardware")
    ap.add_argument("--link")
    ap.add_argument("--optical")
    ap.add_argument("--wav")
    ap.add_argument("--motor", type=int, default=1)
    ap.add_argument("--string", type=int, default=1)
    ap.add_argument("--counts", type=int, default=400, help="the base step d, encoder counts")
    ap.add_argument("--rpm", type=int, default=600)
    ap.add_argument("--acc", type=int, default=0)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--hz", type=float, help="the string's pitch, if the guess is wrong")
    ap.add_argument("--tol", type=float, default=3.0, help="cents that count as settled")
    ap.add_argument("--poll", type=float, default=500.0, help="encoder readings a second")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    moves, reach = scenarios.plan(a.scenario, a.motor, a.counts, a.rpm, a.acc)
    sim = opt = None
    if a.sim:
        from .link import CanLink
        from .servo import Servo
        from .sim import SimServo, string_audio
        sim = SimServo(can_id=a.motor); sim.start()
        link = CanLink(channel="psg-sim", interface="virtual")
        Servo(link, a.motor).enable(); time.sleep(0.05)
        limit = a.limit if a.limit is not None else reach
    else:
        if not a.link or a.limit is None:
            ap.error("real hardware needs --link and --limit")
        kind, _, where = a.link.partition(":")
        if kind == "motor":
            from .link import MotorCtrlLink
            link = MotorCtrlLink(where)
        elif kind == "can":
            from .link import CanLink
            link = CanLink(channel=where, interface="socketcan")
        else:
            ap.error("--link is motor:<port> or can:<channel>")
        limit = a.limit
        if a.optical:
            from .optical import OpticalLink, string_inputs
            opt = OpticalLink(*a.optical.split(","))
            opt.select([string_inputs(a.string)[0]])
        elif not a.wav:
            ap.error("nothing to listen with: --optical or --wav")

    print("%s: %d moves, reaching %d counts from the start (limit %d)" % (a.scenario, len(moves), reach, limit))
    print("recording", flush=True)
    wall = time.monotonic()
    rec = run(link, moves, limit, poll_hz=a.poll, listen=(a.motor,),
              tail=10.0 if a.scenario == "hold" else scenarios.REST + 0.1)
    # Every scenario ends where it began ON PAPER. A motor that was sent on before it had
    # arrived may not agree, so look, say so, and put it back.
    from .servo import Servo
    pos = rec.positions.get(a.motor, [])
    if pos:
        s = Servo(link, a.motor)
        off = s.position() - pos[0][1]
        if abs(off) > 16:
            print("NOTE: the motor ended %d counts from where it began; sending it back" % off)
            s.move_abs(pos[0][1], a.rpm, a.acc)
            time.sleep(1.0)
            print("      now %d counts off" % (s.position() - pos[0][1]))
    else:
        print("NOTE: the motor never answered a position request")

    if sim:
        sr = 48000.0
        t0, audio = rec.t_start, string_audio(sim.history, rec.t_start, rec.t_end, sr)
        sim.stop()
    elif opt:
        from .optical import string_signal
        blocks = opt.take()
        first, audio, _diff = string_signal(blocks, a.string)
        sr, t0 = 48000.0, opt.time_of(first)
        if any(b[1] & 1 for b in blocks):
            print("NOTE: the optical board dropped samples during this run")
        opt.close()
    else:
        from scipy.io import wavfile
        sr, audio = wavfile.read(a.wav)
        audio = audio if audio.ndim == 1 else audio[:, 0]
        sr, t0 = float(sr), wall
    link.close()

    if a.out:
        import os
        os.makedirs(a.out, exist_ok=True)
        path = os.path.join(a.out, "%s-m%d-%s.npz" % (a.scenario, a.motor, time.strftime("%Y%m%d-%H%M%S")))
        np.savez_compressed(
            path, audio=np.asarray(audio, dtype=np.float32), sr=sr, t0=t0, t_start=rec.t_start, t_end=rec.t_end,
            sent=np.array(rec.sent), positions=np.array(rec.positions.get(a.motor, []), dtype=float),
            arrived=np.array(rec.arrived.get(a.motor, []), dtype=float),
            moves=np.array([(m.t, m.motor, m.counts, m.rpm, m.acc, m.absolute) for m in moves], dtype=float))
        print("saved", path)

    res = scenarios.analyze(a.scenario, rec, a.motor, t0, sr, audio, a.hz, a.tol)
    print(scenarios.report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
