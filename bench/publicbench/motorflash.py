"""Write motor_ctrl R2's firmware over J4 (U7's CH340C), hands-free. `make REV=2 usb` / `isp`.

    python3 -m publicbench.motorflash build/r2/main.bin        the application, through boot.c
    python3 -m publicbench.motorflash --rom build/r2/boot.bin  the loader, through WCH's ROM

The application goes in through the loader (firmware/output_panel/boot.c, its H/I/E/W/C/G lines,
as usbflash.py does for R1) inside frames (frames.py). To reach the loader: ask a running
application ("B"), and if nothing answers, pulse reset through U7 and catch the loader's 1.5 s
window -- a hung application needs no hand on the board.

--rom is the way back with nothing working: U7 holds BOOT0 high across a reset, so the chip
starts in WCH's ROM loader on USART1, and wchisp writes over the same port (-s). Then a reset
with BOOT0 low starts the new loader.

MOTOR_PORT=/dev/ttyUSBn picks the port when the search finds the wrong one."""
from __future__ import annotations

import argparse
import binascii
import subprocess
import sys
import time

from . import frames

APP = 0x8000
PAGE = 256


def ask(s, cmd: bytes, wait=3.0) -> str:
    s.write(cmd)
    end = time.monotonic() + wait
    buf = b""
    while time.monotonic() < end:
        buf += s.readline()
        if buf.endswith(b"\n"):
            return buf.decode("ascii", "replace").strip()
    raise SystemExit("no answer to %r" % cmd[:20])


def _hello(s, wait) -> bool:
    try:
        s.reset_input_buffer()
        return ask(s, b"H\n", wait) == "OK"
    except SystemExit:
        return False


def loader(s):
    """Hold the board in its loader: already there, asked back, or reset into its window."""
    if _hello(s, 0.3):
        return
    s.write(b"B\n")                     # a running application: back to the loader
    time.sleep(0.05)
    if _hello(s, 0.3):
        return
    for _ in range(3):                  # hung, or no application: reset and catch the window
        s.reset()
        end = time.monotonic() + 1.4
        while time.monotonic() < end:
            if _hello(s, 0.1):
                return
    raise SystemExit("the loader did not answer on %s" % s.port)


def write_app(s, img: bytes):
    n = len(img)
    img += b"\xff" * (-n % PAGE)
    crc = binascii.crc32(img)
    loader(s)
    print(ask(s, b"I\n"))
    if ask(s, b"E %x\n" % len(img), 15.0) != "OK":
        raise SystemExit("erase failed")
    t = time.monotonic()
    for at in range(0, len(img), PAGE):
        p = img[at:at + PAGE]
        r = ask(s, b"W %x %x\n" % (APP + at, binascii.crc32(p)) + p)   # one frame: line + page
        if r != "OK":
            raise SystemExit("page at %x: %s" % (at, r))
    r = ask(s, b"C %x %x\n" % (len(img), crc), 5.0)
    if r != "OK":
        raise SystemExit("check: " + r)
    print("wrote %d bytes in %.1f s, crc %08x, %d bad frames" % (n, time.monotonic() - t, crc, s.bad))
    print(ask(s, b"I\n"))
    s.write(b"G\n")


def write_rom(port: str, image: str):
    s = frames.FramedSerial(port)
    s.rom()
    s.close()                           # the close raises both lines together: nothing happens
    # the .bin, never the .elf: wchisp sizes its erase from the file
    r = subprocess.run(["wchisp", "-s", "-p", port, "flash", image])
    s = frames.FramedSerial(port)
    s.reset()                           # BOOT0 low: the new loader
    s.close()
    if r.returncode:
        raise SystemExit("wchisp failed (%d)" % r.returncode)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("image")
    a.add_argument("--rom", action="store_true", help="write through WCH's ROM loader (boot.bin)")
    a.add_argument("--port")
    o = a.parse_args(argv)
    port = o.port or frames.find_r2_port()
    if not port:
        raise SystemExit("no R2 motor board: no CH340 outside a hub on ttyUSB (MOTOR_PORT=...)")
    if o.rom:
        write_rom(port, o.image)
        return 0
    s = frames.FramedSerial(port, timeout=0.3, write_timeout=2)
    try:
        write_app(s, open(o.image, "rb").read())
    finally:
        s.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
