"""Write a lever board's application over bus B, through its CAN loader (firmware/lever_sensor/
ldr.h). `make can SLOT=n` in firmware/lever_sensor.

    python3 -m publicbench.leverflash <slot> build/lever.bin

Asks the running application to restart in its loader (CMD 'B'); a board already in its loader
(a failed update, or a bad image) answers the loader's 'I' straight away. Then erase, the pages
with a CRC each, the whole image's CRC (which writes the record the loader starts it by), and
'G'. It is done when the board says HELLO from its application again. Through motor_ctrl
(MotorCtrlLink, bus B = its bus 1)."""
from __future__ import annotations

import argparse
import sys
import time
import zlib

from .levers import K, Levers


def to_loader(lv: Levers, slot: int, timeout: float = 3.0):
    """The board's loader, answering; returns its 'I' reply."""
    try:
        lv.command(slot, "B")
    except TimeoutError:
        pass                                    # in its loader already, or not there at all
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            r = lv.ldr(slot, "I", timeout=0.2)
            if r.ok:
                return r
        except TimeoutError:
            pass
    raise SystemExit("lever slot %d: no loader answered" % slot)


def write(lv: Levers, slot: int, img: bytes, log=print):
    page = K["LDR_PAGE"]
    if not img or len(img) > K["REC_AT"] - K["APP_AT"]:
        raise SystemExit("image is %d bytes; the application area is %d" % (len(img), K["REC_AT"] - K["APP_AT"]))
    r = to_loader(lv, slot)
    log("slot %d: loader v%d, application %s" % (slot, r.more[0], "ok" if r.more[1] else "none"))
    t0 = time.monotonic()
    if not lv.ldr(slot, "E", len(img).to_bytes(4, "little"), timeout=5.0).ok:
        raise SystemExit("erase refused")
    padded = img + b"\xff" * (-len(img) % page)
    for no in range(len(padded) // page):
        p = padded[no * page:(no + 1) * page]
        lv.update()
        n = len(lv.replies)
        lv._send(K["ID_LDR"] + slot, b"W" + no.to_bytes(2, "little") + zlib.crc32(p).to_bytes(4, "little"))
        for k in range(0, page, 8):
            lv._send(K["ID_LDR_D"] + slot, p[k:k + 8])
        r = lv.ldr_wait(slot, "W", n, 2.0)
        if not r.ok or int.from_bytes(r.more[:2], "little") != no:
            raise SystemExit("page %d refused" % no)
    crc = zlib.crc32(img)
    if not lv.ldr(slot, "C", len(img).to_bytes(3, "little") + crc.to_bytes(4, "little"), timeout=2.0).ok:
        raise SystemExit("the image's CRC did not match on the board")
    log("wrote %d bytes in %.1f s, crc %08x" % (len(img), time.monotonic() - t0, crc))
    t1 = time.monotonic()
    lv.ldr(slot, "G")

    def back():
        lv.update()
        return next((h for h in lv.hello.values() if h.slot == slot and h.mode == 0 and h.t >= t1), None)
    if lv.link.wait(back, 3.0) is None:
        raise SystemExit("slot %d did not come back from its application" % slot)
    log("slot %d running the new application" % slot)


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument("slot", type=int)
    a.add_argument("image")
    o = a.parse_args(argv)
    from .link import MotorCtrlLink
    link = MotorCtrlLink()
    try:
        write(Levers(link, bus=1), o.slot, open(o.image, "rb").read())
    finally:
        link.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
