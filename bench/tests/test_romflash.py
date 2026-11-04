"""romflash against pretend boards: the straight pair's line timing, the open's glitch, and both
ROMs' framing (WCH serial ISP for output_panel, ST's USART bootloader for optical). No hardware."""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from publicbench import romflash as R          # noqa: E402

NRST_RISE = 0.003          # R6 10k into C54 100 nF to the threshold, generously: 3 ms


class Clock:
    def __init__(self):
        self.t = 0.0

    def sleep(self, s):
        self.t += s


class Board:
    """A straight pair: DTR# asserted lifts BOOT0 at once; RTS# asserted holds NRST, which rises
    NRST_RISE after it lets go. The chip samples BOOT0 when NRST is up: ROM or the application."""

    def __init__(self, rom, clock):
        self.rom, self.clock = rom, clock
        self.boot0, self.reset, self.released_at = False, False, None
        self.mode = "app"
        self.events = []            # (t, dtr, rts)
        self.rx = bytearray()

    def set(self, dtr, rts):
        self._settle()
        self.events.append((self.clock.t, dtr, rts))
        if rts and not self.reset:
            self.reset, self.mode, self.released_at = True, "reset", None
        elif not rts and self.reset:
            self.reset, self.released_at = False, self.clock.t
        self.boot0 = dtr

    def _settle(self):
        """NRST reaches the threshold NRST_RISE after release: BOOT0 is sampled THEN."""
        if self.released_at is not None and self.clock.t >= self.released_at + NRST_RISE:
            self.mode = "rom" if self.boot0_at_rise else "app"
            self.released_at = None

    @property
    def boot0_at_rise(self):
        # the last DTR state set at or before the rise
        rise = self.released_at + NRST_RISE
        st = [d for t, d, _ in self.events if t <= rise]
        return st[-1] if st else False

    # the port side
    def write(self, data):
        self._settle()
        if self.mode == "rom":
            self.rx += self.rom.feed(bytes(data), self)
        return len(data)

    def read(self, n):
        self._settle()
        out, self.rx[:] = bytes(self.rx[:n]), self.rx[n:]
        return out


class WchRom:
    """The CH32V307's serial ISP as wchisp documents it, written from the protocol, not R's code."""

    def __init__(self, chip=0x70, typ=0x17, uid=bytes([0x31, 0x52, 0xA7, 0x09, 0xCC, 0x48, 0xBC, 0xAB])):
        self.chip, self.typ, self.uid = chip, typ, uid
        self.flash = bytearray(b"\xa5" * 0x10000)       # old contents
        self.buf = b""
        self.unlocked = self.committed = False
        self.erased = 0
        self.ended = False

    def key(self):
        s = sum(self.uid) & 0xFF
        return [s] * 7 + [(s + self.chip) & 0xFF]

    def reply(self, c, payload, status=0):
        h = bytes([c, status]) + struct.pack("<H", len(payload))
        return b"\x55\xaa" + h + payload + bytes([(sum(h) + sum(payload)) & 0xFF])

    def feed(self, data, board):
        self.buf += data
        out = b""
        while len(self.buf) >= 6:
            assert self.buf[:2] == b"\x57\xab"
            n = struct.unpack("<H", self.buf[3:5])[0]
            if len(self.buf) < 6 + n:
                break
            raw, cs, self.buf = self.buf[2:5 + n], self.buf[5 + n], self.buf[6 + n:]
            assert cs == sum(raw) & 0xFF, "request checksum"
            out += self.do(raw[0], raw[3:], board)
        return out

    def do(self, c, p, board):
        if c == R.IDENTIFY:
            assert p[2:] == b"MCU ISP & WCH.CN" and len(p) == 18
            return self.reply(c, bytes([self.chip, self.typ]))
        if c == R.READ_CONFIG:
            assert p == bytes([0x1F, 0])
            cfg = bytes([0xA5, 0x5A, 0x3F, 0xC0]) + b"\x00" * 4 + b"\xff" * 4 + bytes([0, 2, 9, 0])
            return self.reply(c, b"\x1f\x00" + cfg + self.uid)
        if c == R.ISP_KEY:
            assert p == bytes(30)
            self.unlocked = True
            return self.reply(c, bytes([sum(self.key()) & 0xFF]))
        if c == R.ERASE:
            assert self.unlocked
            self.erased = struct.unpack("<I", p)[0]
            assert self.erased >= 8
            self.flash[:self.erased * 1024] = b"\xff" * (self.erased * 1024)
            return self.reply(c, b"\x00\x00")
        if c in (R.PROGRAM, R.VERIFY):
            assert self.unlocked
            a = struct.unpack("<I", p[:4])[0]
            d = bytes(b ^ self.key()[i % 8] for i, b in enumerate(p[5:]))
            if c == R.PROGRAM:
                if not d:
                    self.committed = True
                else:
                    assert a + len(d) <= self.erased * 1024 and len(d) <= 56
                    self.flash[a:a + len(d)] = d
                return self.reply(c, b"\x00\x00")
            return self.reply(c, bytes([0 if self.flash[a:a + len(d)] == d else 0xF5, 0]))
        if c == R.ISP_END:
            assert p == b"\x01"
            self.ended = True
            board.mode = "app" if not board.boot0 else "rom"
            return self.reply(c, b"\x00\x00")
        raise AssertionError("command 0x%02X" % c)


class StRom:
    """The STM32H743's USART bootloader (AN3155): ACK 0x79, commands with their complement."""
    PID = 0x450

    def __init__(self):
        self.flash = {}                     # address -> byte; absent = 0xFF
        self.started = False
        self.buf = b""
        self.state = None

    def feed(self, data, board):
        self.buf += data
        out = b""
        while True:
            r = self.step()
            if r is None:
                return out
            out += r

    def take(self, n):
        if len(self.buf) < n:
            return None
        b, self.buf = self.buf[:n], self.buf[n:]
        return b

    def step(self):
        if not self.started:
            b = self.take(1)
            if b is None:
                return None
            assert b == b"\x7f"
            self.started = True
            return b"\x79"
        if self.state is None:
            b = self.take(2)
            if b is None:
                return None
            assert b[0] ^ b[1] == 0xFF, "complement"
            self.state = b[0]
            if b[0] == R.ST_GET_ID:
                self.state = None
                return b"\x79\x01" + struct.pack(">H", self.PID) + b"\x79"
            return b"\x79"
        if self.state in (R.ST_WRITE, R.ST_READ) and not hasattr(self, "addr"):
            b = self.take(5)
            if b is None:
                return None
            assert R._xor(b[:4]) == b[4]
            self.addr = struct.unpack(">I", b[:4])[0]
            return b"\x79"
        if self.state == R.ST_WRITE:
            if len(self.buf) < 1 or len(self.buf) < self.buf[0] + 3:
                return None
            n = self.buf[0] + 1
            b = self.take(n + 2)
            assert R._xor(b[:-1]) == b[-1]
            assert n % 32 == 0 and self.addr % 32 == 0, "H7: whole flash words"
            for i, v in enumerate(b[1:-1]):
                assert self.flash.get(self.addr + i, 0xFF) == 0xFF, "written over unerased"
                self.flash[self.addr + i] = v
            del self.addr
            self.state = None
            return b"\x79"
        if self.state == R.ST_READ:
            b = self.take(2)
            if b is None:
                return None
            assert b[0] ^ b[1] == 0xFF
            a = self.addr
            del self.addr
            self.state = None
            return b"\x79" + bytes(self.flash.get(a + i, 0xFF) for i in range(b[0] + 1))
        if self.state == R.ST_EXT_ERASE:
            if len(self.buf) < 2:
                return None
            n = struct.unpack(">H", self.buf[:2])[0] + 1
            b = self.take(2 + 2 * n + 1)
            if b is None:
                return None
            assert R._xor(b[:-1]) == b[-1]
            for k in range(n):
                s = struct.unpack(">H", b[2 + 2 * k:4 + 2 * k])[0]
                base = R.H7_FLASH + s * R.H7_SECTOR
                for a in [a for a in self.flash if base <= a < base + R.H7_SECTOR]:
                    del self.flash[a]
            self.state = None
            return b"\x79"
        raise AssertionError("state 0x%02X" % self.state)


def rig(rom):
    c = Clock()
    b = Board(rom, c)
    return b, R.Lines(b.set, sleep=c.sleep), c


def test_rom_entry_holds_boot0_past_the_reset_rising():
    b, lines, c = rig(WchRom())
    lines.rom()
    assert b.write(b"") == 0 and b.mode == "rom"
    (t0, d0, r0), (t1, d1, r1), (t2, d2, r2) = b.events
    assert (d0, r0) == (True, True) and (d1, r1) == (True, False) and (d2, r2) == (False, False)
    assert t1 - t0 >= 0.01                         # NRST held low long enough to reset
    assert t2 - t1 >= NRST_RISE * 5                # BOOT0 held well past NRST's rise


def test_a_plain_open_glitch_boots_the_application():
    """The kernel raises both on open, then pyserial lets DTR go and then RTS: BOOT0 is down
    before NRST rises, so the open is a reset, not a trip into the ROM."""
    b, lines, c = rig(WchRom())
    b.set(True, True)                              # the kernel's raise
    b.set(False, True)                             # pyserial: dtr = False
    b.set(False, False)                            # pyserial: rts = False
    c.sleep(0.01)
    b.write(b"")
    assert b.mode == "app"


def test_run_leaves_the_rom_with_boot0_low():
    b, lines, c = rig(WchRom())
    lines.rom()
    lines.run()
    c.sleep(0.01)
    b.write(b"")
    assert b.mode == "app" and b.events[-1][1:] == (False, False)


def test_wch_isp_writes_and_verifies_an_image():
    rom = WchRom()
    b, lines, c = rig(rom)
    img = bytes((i * 37 + 11) & 0xFF for i in range(5000))          # not a whole chunk
    R.flash("output_panel", b, lines, img, log=lambda *a: None)
    assert rom.committed and rom.ended and rom.erased == 8
    assert bytes(rom.flash[:len(img)]) == img
    assert bytes(rom.flash[8192:8200]) == b"\xa5" * 8                # past the erase: untouched
    c.sleep(0.01)
    b.write(b"")
    assert b.mode == "app"


def test_wch_verify_only_catches_a_difference():
    rom = WchRom()
    b, lines, c = rig(rom)
    with pytest.raises(R.RomError, match="verify differs"):
        R.flash("output_panel", b, lines, b"\x01" * 100, verify_only=True, log=lambda *a: None)
    assert b.events[-1][1:] == (False, False)       # out of the ROM even after a failure


def test_wch_refuses_a_chip_that_is_not_a_v30x():
    b, lines, c = rig(WchRom(typ=0x19))
    with pytest.raises(R.RomError, match="not a CH32V30x"):
        R.flash("output_panel", b, lines, b"\x00" * 64, log=lambda *a: None)


def test_wch_frames_carry_a_byte_sum():
    assert R.wch_frame(b"\xa2\x01\x00\x01") == b"\x57\xab\xa2\x01\x00\x01\xa4"


def test_st_boot_writes_and_verifies_an_image():
    rom = StRom()
    rom.flash.update({R.H7_FLASH + 5: 0x00})       # an old byte in sector 0
    b, lines, c = rig(rom)
    img = bytes((i * 13 + 5) & 0xFF for i in range(1000))           # not a whole word
    R.flash("optical", b, lines, img, log=lambda *a: None)
    got = bytes(rom.flash.get(R.H7_FLASH + i, 0xFF) for i in range(1024))
    assert got[:1000] == img and got[1000:] == b"\xff" * 24


def test_st_boot_refuses_another_product():
    rom = StRom()
    rom.PID = 0x483
    b, lines, c = rig(rom)
    with pytest.raises(R.RomError, match="not an STM32H74x"):
        R.flash("optical", b, lines, b"\x00" * 32, log=lambda *a: None)


def test_a_board_not_in_its_rom_is_a_quiet_rom():
    """Lines that never reach the ROM (BOOT0 not held): the tool says the ROM is quiet."""
    b, _lines, c = rig(StRom())
    quiet = R.Lines(lambda d, r: b.set(False, r), sleep=c.sleep)     # DTR# never lifts BOOT0
    with pytest.raises(R.RomError, match="quiet"):
        R.flash("optical", b, quiet, b"\x00" * 32, log=lambda *a: None)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="termios: the bench is the Pi")
def test_hupcl_is_cleared_on_a_real_tty():
    import termios
    m, s = os.openpty()
    try:
        a = termios.tcgetattr(s)
        a[2] |= termios.HUPCL
        termios.tcsetattr(s, termios.TCSANOW, a)
        R.clear_hupcl(s)
        assert not termios.tcgetattr(s)[2] & termios.HUPCL
    finally:
        os.close(m)
        os.close(s)
