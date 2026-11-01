#!/usr/bin/env python3
"""Write output_panel's application over USB, through its loader (boot.c).

    python3 psgflash.py build/app.bin

Finds the board's serial port (1a86:fe0c), asks a running application to go back to the
loader, or catches the loader's window at power-up: if the board does not answer, power-cycle
it while this waits. Standard library plus pyserial."""
import binascii
import glob
import os
import sys
import time

import serial

APP = 0x8000
PAGE = 256


def port():
    for tty in glob.glob("/sys/class/tty/ttyACM*"):
        d = os.path.realpath(tty + "/device/..")
        try:
            ids = [open(os.path.join(d, f)).read().strip() for f in ("idVendor", "idProduct")]
        except OSError:
            continue
        if ids == ["1a86", "fe0c"]:
            return "/dev/" + os.path.basename(tty)
    return None


def open_port(wait):
    end = time.time() + wait
    while time.time() < end:
        p = port()
        if p:
            try:
                return serial.Serial(p, 115200, timeout=0.3, write_timeout=2)
            except (OSError, serial.SerialException):
                pass
        time.sleep(0.01)
    raise SystemExit("no board on USB: power-cycle it with this running, or check J3")


def ask(s, cmd, wait=3.0):
    s.write(cmd)
    end = time.time() + wait
    buf = b""
    while time.time() < end:
        buf += s.readline()
        if buf.endswith(b"\n"):
            return buf.decode().strip()
    raise SystemExit("no answer to %r" % cmd[:20])


def loader():
    """A serial port on the loader, held there."""
    for _ in range(4):
        s = open_port(60.0)
        try:
            s.reset_input_buffer()
            r = ask(s, b"H\n", 0.4)
        except (SystemExit, OSError, serial.SerialException):
            r = ""
        if r == "OK":
            return s
        try:
            s.write(b"B\x0a")       # an application: back to the loader
            s.close()
        except (OSError, serial.SerialException):
            pass
        time.sleep(0.5)
    raise SystemExit("the loader did not answer")


def main():
    img = open(sys.argv[1], "rb").read()
    n = len(img)
    img += b"\xff" * (-n % PAGE)
    crc = binascii.crc32(img)
    s = loader()
    print(ask(s, b"I\n"))
    if ask(s, b"E %x\n" % len(img), 15.0) != "OK":
        raise SystemExit("erase failed")
    t = time.time()
    for at in range(0, len(img), PAGE):
        p = img[at:at + PAGE]
        r = ask(s, b"W %x %x\n" % (APP + at, binascii.crc32(p)) + p)
        if r != "OK":
            raise SystemExit("page at %x: %s" % (at, r))
    r = ask(s, b"C %x %x\n" % (len(img), crc), 5.0)
    if r != "OK":
        raise SystemExit("check: " + r)
    print("wrote %d bytes in %.1f s, crc %08x" % (n, time.time() - t, crc))
    print(ask(s, b"I\n"))
    ask(s, b"G\n")
    s.close()


if __name__ == "__main__":
    main()
