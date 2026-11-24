"""The QT Py bench firmware's logic, compiled natively (publicbench.simqtpy): the move planner,
the TMC2209 datagrams and the command line. No board: the timer, UART and motor are pretend."""
import ctypes
import math

import pytest

from publicbench import simqtpy as Q

pytestmark = pytest.mark.skipif(not Q.compiler(), reason="no native C compiler")
F = Q.TICK_HZ


# ── the planner ──
def move(steps, v, a):
    q = Q.QtPy()
    r = q.send("mv %d %d %d" % (steps, v, a))
    assert r == "ok steps=%d" % abs(steps), r
    iv = q.run()
    return q, iv


def test_a_move_sends_exactly_its_steps_and_ends_on_target():
    for steps in (1, 2, 3, 7, 100, 833, 5000, -1, -833):
        q, iv = move(steps, 42_700, 4_300_000)
        assert len(iv) == abs(steps)
        assert q.L.sim_pos() == steps and not q.L.sim_armed()
        assert q.fields(q.send("st"))["moving"] == "0"


def test_the_trapezoid_reaches_cruise_and_is_roughly_symmetric():
    v, a = 42_700, 4_300_000                     # ~1600 rpm at 1/4 step of a 0.9 deg motor
    q, iv = move(2000, v, a)
    cmin = F // v
    assert min(iv) == cmin                        # cruises at vmax, never faster
    assert iv.count(cmin) > 1000
    nacc = v * v // (2 * a)
    assert abs(iv.index(cmin) - nacc) <= nacc * 0.1 + 2
    up, down = iv[1:nacc], iv[-nacc:][::-1]
    assert all(x >= y for x, y in zip(up, up[1:]))           # speeds up monotonically
    assert all(x >= y for x, y in zip(down, down[1:]))       # slows down monotonically
    assert max(abs(x - y) for x, y in zip(up, down[1:])) <= max(3, cmin // 10)


def test_the_move_time_matches_the_trapezoid():
    v, a, s = 42_700, 4_300_000, 833             # a whole tone, about 0.52 turn at 1600 steps/rev
    q, iv = move(s, v, a)
    t = sum(iv) / F
    ta = v / a
    da = v * v / (2 * a)
    ideal = 2 * ta + (s - 2 * da) / v if s > 2 * da else 2 * math.sqrt(s / a)
    assert abs(t - ideal) / ideal < 0.05, (t, ideal)


def test_a_short_move_is_a_triangle_and_never_overshoots_speed():
    v, a = 42_700, 4_300_000
    q, iv = move(50, v, a)
    assert min(iv) > F // v                      # never got to cruise
    t = sum(iv) / F
    assert abs(t - 2 * math.sqrt(50 / a)) / (2 * math.sqrt(50 / a)) < 0.15


def test_slow_moves_clamp_to_the_16_bit_compare():
    q, iv = move(20, 50, 100)
    assert max(iv) <= 65535 and len(iv) == 20


def test_halt_stops_where_it_is():
    q = Q.QtPy()
    q.send("mv 1000 20000 1000000")
    q.run(stop_after=300)
    r = q.send("halt")
    assert r == "ok pos=%d" % q.L.sim_pos() and not q.L.sim_armed()
    st = q.fields(q.send("st"))
    assert st["pos"] == st["target"] and st["moving"] == "0"


def test_busy_refuses_a_second_move_and_zero():
    q = Q.QtPy()
    q.send("mv 100 1000 10000")
    assert q.send("mv 5 1000 1000") == "err busy"
    assert q.send("zero") == "err busy"
    q.run()
    assert q.send("zero") == "ok" and q.L.sim_pos() == 0


def test_go_is_absolute_and_mv_relative_and_dir_follows():
    q = Q.QtPy()
    q.send("go 10 1000 10000"); q.run()
    assert q.L.sim_dir() == 1
    q.send("go -5 1000 10000"); q.run()
    assert q.L.sim_pos() == -5 and q.L.sim_dir() == -1
    q.send("mv 3 1000 10000"); q.run()
    assert q.L.sim_pos() == -2
    assert q.send("go -2 1000 10000") == "ok steps=0"


def test_moves_run_with_the_outputs_off():
    """gate 1 item (i) sends steps with ENN high to see whether MSCNT follows them"""
    q = Q.QtPy()
    assert q.send("en 0") == "ok en=0" and not q.L.sim_en()
    assert q.send("mv 8 1000 10000") == "ok steps=8"
    assert len(q.run()) == 8


# ── TMC2209 datagrams (datasheet section 4) ──
def test_crc_matches_the_datasheet_routine():
    def ref(data):
        crc = 0
        for b in data:
            for _ in range(8):
                crc = ((crc << 1) ^ 0x07) & 0xFF if (crc >> 7) ^ (b & 1) else (crc << 1) & 0xFF
                b >>= 1
        return crc
    L = Q.lib()
    for data in (b"\x05\x00\x00", b"\x05\x00\x80\x00\x00\x00\xc0", bytes(range(7))):
        buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        assert L.sim_crc(buf, len(data)) == ref(data)


def test_datagrams_are_framed_as_the_datasheet_says():
    L = Q.lib()
    w = Q.dg(L.sim_write_dg, 0, 0x6C, 0x16000053)
    assert w[:7] == bytes([0x05, 0x00, 0xEC, 0x16, 0x00, 0x00, 0x53])
    r = Q.dg(L.sim_read_dg, 3, 0x6A, n=4)
    assert r[:3] == bytes([0x05, 0x03, 0x6A])
    buf = (ctypes.c_uint8 * 7).from_buffer_copy(w[:7])
    assert w[7] == L.sim_crc(buf, 7)


def test_a_reply_is_checked_before_it_is_believed():
    L = Q.lib()
    body = bytes([0x05, 0xFF, 0x6A, 0, 0, 0x01, 0x23])
    crc = L.sim_crc((ctypes.c_uint8 * 7).from_buffer_copy(body), 7)
    good = (ctypes.c_uint8 * 8).from_buffer_copy(body + bytes([crc]))
    v = ctypes.c_uint32()
    assert L.sim_parse(good, 0x6A, ctypes.byref(v)) == 0 and v.value == 0x123
    bad = (ctypes.c_uint8 * 8).from_buffer_copy(body + bytes([crc ^ 1]))
    assert L.sim_parse(bad, 0x6A, ctypes.byref(v)) == -2
    assert L.sim_parse(good, 0x6C, ctypes.byref(v)) == -3
    nosync = (ctypes.c_uint8 * 8).from_buffer_copy(bytes([0x00]) + body[1:] + bytes([crc]))
    assert L.sim_parse(nosync, 0x6A, ctypes.byref(v)) == -1


def test_current_scale_follows_the_p50_formula():
    L = Q.lib()
    for ma in (200, 500, 1000, 1400, 1700):
        cs = L.sim_cs(ma, 110)
        assert cs == min(31, max(0, round(ma / 1000 * 32 * math.sqrt(2) * 0.130 / 0.325) - 1))
        assert abs(L.sim_ma(cs, 110) - ma) <= 1770 / 32 / 2 + 1
    assert L.sim_cs(99999, 110) == 31 and L.sim_cs(0, 110) == 0


def test_chopconf_keeps_the_default_and_sets_mres_and_dedge():
    L = Q.lib()
    v = L.sim_chop(6, 1)
    assert (v >> 24) & 0xF == 6 and v >> 29 & 1 and v >> 28 & 1 and v & 0xF == 3


# ── the command line ──
def test_init_writes_the_bench_configuration_and_counts_it():
    q = Q.QtPy()
    r = q.fields(q.send("init"))
    assert r == {"writes": "5", "usteps": "4"}
    L = q.L
    assert L.sim_reg(0x00) == (1 << 6) | (1 << 7)              # pdn_disable, mstep_reg_select
    assert L.sim_reg(0x6C) == L.sim_chop(6, 1)
    assert L.sim_reg(0x11) == 20
    assert q.fields(q.send("init 16"))["usteps"] == "16"
    assert (L.sim_reg(0x6C) >> 24) & 0xF == 4
    assert q.send("init 3") == "err usteps"


def test_cur_sets_ihold_irun_and_reports_what_it_got():
    q = Q.QtPy()
    r = q.fields(q.send("cur 1400 0"))
    assert r["irun"] == str(Q.lib().sim_cs(1400, 110)) and r["ihold"] == "0"
    assert abs(int(r["run_mA"]) - 1400) < 60
    v = q.L.sim_reg(0x10)
    assert (v >> 8) & 31 == int(r["irun"]) and v & 31 == 0 and (v >> 16) & 15 == 4


def test_ms_reports_mscnt_beside_the_steps_sent():
    q = Q.QtPy()
    q.send("init")
    q.send("mv 7 1000 10000"); q.run()
    r = q.fields(q.send("ms"))
    assert r == {"mscnt": str((7 * 64) % 1024), "pos": "7", "per": "64", "moving": "0"}
    q.send("mv -20 1000 10000"); q.run()
    r = q.fields(q.send("ms"))
    assert int(r["mscnt"]) == (-13 * 64) % 1024


def test_gstat_reads_and_clears_the_reset_flag():
    q = Q.QtPy()
    q.L.sim_set_reg(0x01, 1)
    assert q.send("gstat") == "ok gstat=0x1 reset=1"
    assert q.L.sim_reg(0x01) == 0
    assert q.send("gstat") == "ok gstat=0x0 reset=0"


def test_raw_register_access_and_uart_faults_are_reported():
    q = Q.QtPy()
    assert q.send("w 0x6c 0x10000053") == "ok"
    assert q.send("r 0x6c") == "ok 0x6c=0x10000053"
    q.L.sim_fail(1)
    assert q.send("r 0x6c") == "err uart -10"
    assert q.send("init").startswith("err uart")
    assert q.send("r 0x80") .startswith("err unknown")


def test_nonsense_is_refused_not_obeyed():
    q = Q.QtPy()
    for line in ("", "mv", "mv x 1 1", "mv 5 -1 1", "go 1 2", "cur 1", "en", "frob"):
        assert q.send(line).startswith("err"), line
    assert not q.L.sim_armed()
    assert q.send("id").startswith("ok qtpy_bench")


# ── the Pi's client (publicbench.qtpy) against the same pretend board ──
class FakeSerial:
    """routes each line to the native firmware; a move runs to its end before the reply"""

    def __init__(self):
        self.q = Q.QtPy()
        self.out = b""

    def reset_input_buffer(self):
        self.out = b""

    def write(self, data):
        r = self.q.send(data.decode().strip())
        if self.q.L.sim_armed():
            self.q.run()
        self.out += (r + "\n").encode()

    def readline(self):
        line, _, self.out = self.out.partition(b"\n")
        return line + b"\n" if line else b""


def test_client_drives_a_move_and_checks_mscnt():
    from publicbench import qtpy as P
    b = P.QtPyBench(ser=FakeSerial())
    assert b.init(4) == {"writes": 5, "usteps": 4}
    assert b.current(1000)["run_mA"] > 900
    ms0 = b.mscnt()
    assert b.move(833, 42_700, 4_300_000) == 833
    s = b.wait()
    assert s["pos"] == 833 and s["moving"] == 0
    assert P.mscnt_agrees(b.mscnt(), ms0["mscnt"], +1)
    assert not P.mscnt_agrees(b.mscnt(), (ms0["mscnt"] + 64) % 1024, +1)


def test_client_raises_on_err():
    from publicbench import qtpy as P
    b = P.QtPyBench(ser=FakeSerial())
    with pytest.raises(P.BenchError):
        b.do("frob")
    assert P.fields("ok drv=0x80000000 otpw=0") == {"drv": 0x80000000, "otpw": 0}


def test_setpos_says_where_the_motor_is_without_moving():
    q = Q.QtPy()
    assert q.send("setpos -37") == "ok pos=-37" and q.L.sim_pos() == -37 and not q.L.sim_armed()
    assert q.fields(q.send("st"))["target"] == "-37"
    q.send("mv 10 1000 10000")
    assert q.send("setpos 0") == "err busy"
