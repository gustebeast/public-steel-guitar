"""motor_ctrl R2's link frames: the host codec, and the firmware's own frame.c against it."""
import os
import random
import shutil
import subprocess

import pytest

from publicbench import frames

FW = os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "motor_ctrl")


def payloads():
    r = random.Random(7)
    yield b""
    yield b"T\n"
    yield b"\x00" * 10
    yield bytes(range(256))
    yield b"\x01" * 253 + b"\x00" + b"\x02" * 46            # a full 254-byte COBS block
    yield b"W 8000 1234abcd\n" + bytes(r.randrange(256) for _ in range(256))
    for n in (1, 2, 253, 254, 255, frames.FRAME_MAX):
        yield bytes(r.randrange(256) for _ in range(n))


def test_crc_check_value():
    assert frames.crc16(b"123456789") == 0x29B1             # CRC-16/CCITT-FALSE


def test_round_trip_and_no_zeros_inside():
    d = frames.Deframer()
    for p in payloads():
        w = frames.encode(p)
        assert w[0] == 0 and w[-1] == 0 and 0 not in w[1:-1]
        assert d.feed(w) == [p]
    assert d.bad == 0


def test_too_long_refused():
    with pytest.raises(ValueError):
        frames.encode(b"x" * (frames.FRAME_MAX + 1))


def test_every_single_byte_corruption_is_dropped():
    p = b"Q 17 123456 0 141 0102030405060708\n"
    w = frames.encode(p)
    for i in range(1, len(w) - 1):
        for flip in (0x01, 0x80, 0xFF):
            bad = bytearray(w)
            bad[i] ^= flip
            d = frames.Deframer()
            got = d.feed(bytes(bad) + frames.encode(b"T\n"))
            assert p not in got
            assert got[-1:] == [b"T\n"]                     # the next frame still lands


def test_noise_before_a_frame_is_one_bad_frame():
    d = frames.Deframer()
    assert d.feed(b"\x13\x37\xaa" + frames.encode(b"V\n")) == [b"V\n"]
    assert d.bad == 1
    assert d.feed(b"\x00\x00\x00") == [] and d.bad == 1     # idle zeros are nothing


def test_pack_lines_keeps_lines_whole():
    lines = b"".join(b"R 0 %d 141 0011223344556677\n" % i for i in range(40))
    out = frames.pack_lines(lines)
    assert b"".join(out) == lines
    assert all(len(p) <= frames.FRAME_MAX and p.endswith(b"\n") for p in out)
    page = b"W 8000 0\n" + b"\n" * 256                      # a page full of 0x0a stays one
    assert frames.pack_lines(page) == [page]


def test_link_baud_is_the_firmware_constant():
    assert frames.link_baud() == 2000000


class FakeSerial:
    def __init__(self, wire=b""):
        self.rx, self.tx, self.timeout = bytearray(wire), bytearray(), 0

    @property
    def in_waiting(self):
        return len(self.rx)

    def read(self, n):
        got = bytes(self.rx[:n])
        del self.rx[:n]
        return got

    def write(self, b):
        self.tx += b

    def reset_input_buffer(self):
        self.rx.clear()


def framed(wire=b""):
    f = frames.FramedSerial.__new__(frames.FramedSerial)
    f.ser, f.port, f.de, f.pending = FakeSerial(wire), "fake", frames.Deframer(), bytearray()
    return f


def test_framed_serial_is_a_line_stream():
    good = frames.encode(b"T 1000\nR 0 5 141 aa\n")
    bad = bytearray(frames.encode(b"T 2000\n"))
    bad[3] ^= 1
    f = framed(good + bytes(bad) + frames.encode(b"E busy\n"))
    assert f.readline() == b"T 1000\n"
    assert f.read(4096) == b"R 0 5 141 aa\nE busy\n"
    assert f.bad == 1
    f.write(b"T\n")
    assert frames.Deframer().feed(bytes(f.ser.tx)) == [b"T\n"]


@pytest.mark.skipif(not shutil.which("gcc"), reason="no native gcc")
def test_firmware_frame_c_matches(tmp_path):
    """frame.c, compiled for this computer: it encodes as the host does, and decodes the host's
    frames (good ones back whole, every corrupted one dropped and counted)."""
    harness = tmp_path / "h.c"
    harness.write_text(r'''
#include <stdio.h>
#include "frame.h"
static uint8_t in[4096], out[FRAME_WIRE], pay[FRAME_MAX];
int main(void) {
    /* stdin: mode byte 'E' then a payload -> its wire; 'D' then wire -> each payload as
       "len hex\n", then "bad N\n" */
    size_t n = fread(in, 1, sizeof in, stdin);
    if (in[0] == 'E') {
        uint32_t w = frame_encode(in + 1, (uint32_t)(n - 1), out);
        fwrite(out, 1, w, stdout);
        return w ? 0 : 1;
    }
    frame_rx_t r = {0};
    for (size_t i = 1; i < n; i++) {
        int got = frame_feed(&r, in[i], pay);
        if (got >= 0) { printf("%d ", got); for (int k = 0; k < got; k++) printf("%02x", pay[k]); printf("\n"); }
    }
    printf("bad %u\n", r.bad);
    return 0;
}
''')
    exe = tmp_path / "h"
    subprocess.run(["gcc", "-O2", "-Wall", "-Werror", "-I", FW, str(harness),
                    os.path.join(FW, "frame.c"), "-o", str(exe)], check=True)

    def run(data):
        return subprocess.run([str(exe)], input=data, capture_output=True, check=True).stdout

    wire = b""
    for p in payloads():
        assert run(b"E" + p) == frames.encode(p)
        wire += frames.encode(p)
    lines = run(b"D" + wire).decode().split("\n")
    want = ["%d %s" % (len(p), p.hex()) for p in payloads()]
    assert lines[:len(want)] == want and lines[len(want)] == "bad 0"

    p = b"Q 3 0 0 141 01\n"
    w = frames.encode(p)
    junk = b""
    for i in range(1, len(w) - 1):
        bad = bytearray(w)
        bad[i] ^= 0x10
        junk += bytes(bad)
    out = run(b"D" + junk).decode()
    assert p.hex() not in out
    assert int(out.split("bad ")[-1]) >= len(w) - 2            # a byte turned 0x00 splits one in two
