#!/usr/bin/env python3
"""The lever board's SWD image: the loader, the application at APP_AT and the loader's record of
it at REC_AT (ldr.h), so the first boot after `make swd` starts the application. The file stops
after the record: the config page (slot, calibration) is not in it.

    python3 image.py build/boot.bin build/lever.bin build/full.bin
"""
import os
import re
import sys
import zlib


def ldr_h():
    t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ldr.h")).read()
    k = {}
    for name, v in re.findall(r"^#define\s+(\w+)\s+(0x[0-9A-Fa-f]+|\d+)u?\b", t, re.M):
        k[name] = int(v, 0)
    return k


def main(boot, app, out):
    k = ldr_h()
    b, a = open(boot, "rb").read(), open(app, "rb").read()
    app_max = k["REC_AT"] - k["APP_AT"]
    assert len(b) <= k["LDR_MAX"], "the loader is %d bytes, over LDR_MAX" % len(b)
    assert len(a) <= app_max, "the application is %d bytes, over APP_MAX" % len(a)
    c = zlib.crc32(a)
    rec = b"".join(v.to_bytes(4, "little") for v in (k["REC_MAGIC"], len(a), c, c ^ 0xFFFFFFFF))
    img = b.ljust(k["APP_AT"], b"\xff") + a
    img = img.ljust(k["REC_AT"], b"\xff") + rec
    open(out, "wb").write(img)
    print("%s: loader %d, application %d (crc %08x), %d bytes" % (out, len(b), len(a), c, len(img)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
