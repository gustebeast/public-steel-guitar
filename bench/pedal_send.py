"""Stream an expression pedal to the Pi's publicbench.pedaldrive (user, 2026-11-11).

Runs on the computer the pedal is plugged into (the Mac: ~/pedal-stream, its own venv with
mido + python-rtmidi):

    ./venv/bin/python pedal_send.py                      LEHLE DUAL EXPRESSION, CC 11
    ./venv/bin/python pedal_send.py --cc 12 --host 192.168.1.50

Each datagram is "<seq> <value 0..1>": on every change, and again every KEEPALIVE_S so the Pi
knows the link is alive (it holds the motor when it hears nothing for half a second).
"""
import argparse
import socket
import time

import mido

KEEPALIVE_S = 0.1


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--host", default="public-steel-guitar.local")
    a.add_argument("--port", type=int, default=5005)
    a.add_argument("--input", default="LEHLE DUAL EXPRESSION")
    a.add_argument("--cc", type=int, default=11)
    # THIS PEDAL READS BACKWARDS for the Pi's mapping (user, 2026-11-11), so it is inverted by
    # default; --no-invert sends it as it comes
    a.add_argument("--no-invert", dest="invert", action="store_false", help="send the CC as it comes")
    o = a.parse_args()
    addr = (socket.gethostbyname(o.host), o.port)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq, v, last = 0, None, 0.0
    print("%s CC %d -> %s:%d" % (o.input, o.cc, *addr), flush=True)
    with mido.open_input(o.input) as port:
        while True:
            for msg in port.iter_pending():
                if msg.type == "control_change" and msg.control == o.cc:
                    v = msg.value / 127.0
                    if o.invert:
                        v = 1.0 - v
                    seq += 1
                    s.sendto(b"%d %.4f" % (seq, v), addr)
                    last = time.monotonic()
            if v is not None and time.monotonic() - last > KEEPALIVE_S:
                seq += 1
                s.sendto(b"%d %.4f" % (seq, v), addr)
                last = time.monotonic()
            time.sleep(0.001)


if __name__ == "__main__":
    main()
