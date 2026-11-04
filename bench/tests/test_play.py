"""The control path: copedent.json compiled on the Pi (copedent.py) into the table motor_ctrl plays
from (play.c, compiled natively), by itself and end to end with the real lever logic on bus B
(simlever) and pretend motors on bus A (sim.SimServo)."""
import random
import time

import pytest

from publicbench import copedent as CP
from publicbench import servo as S
from publicbench import simlever as SL

pytestmark = pytest.mark.skipif(not SL.compiler(), reason="no native C compiler")
K = CP.K
FULL = K["PLAY_POS_FULL"]
DRIVE = 3                                                   # play.h PS_DRIVE


@pytest.fixture(scope="module")
def cop():
    return CP.load()


@pytest.fixture(scope="module")
def table(cop):
    return CP.compile_table(cop)


def slot_of(cop, name):
    return next(k["slot"] for k in cop["controls"] if k["name"] == name)


def pos_frame(slot, frac=None, raw=None):
    v = raw if raw is not None else round(frac * FULL)
    return K["PLAY_POS_ID"] + slot, v.to_bytes(2, "little") + bytes([0, 0])


def test_the_table_is_what_play_h_says(table):
    from publicbench.simplay import Play, lib
    assert len(table) == CP.SIZE == lib().sim_table_size()
    assert lib().play_table_ok(table)
    bad = bytearray(table)
    bad[40] ^= 1
    assert not lib().play_table_ok(bytes(bad))
    p = Play(bytes(bad))
    assert p.poll(0) is None                                  # a bad table drives nothing


def test_pitch_rule_matches_the_pis_copy(cop, table):
    from publicbench.simplay import Play
    t = CP.cents_table(cop)
    rnd = random.Random(7)
    for _ in range(200):
        p = Play(table)
        pos = {c: rnd.choice((0.0, 1.0, rnd.random())) for c in rnd.sample(range(11), 4)}
        for c, f in pos.items():
            p.rx(1, *pos_frame(c, f), now_us=0)
        for s in range(CP.STRINGS):
            assert p.cents(s) == CP.pitch(t, pos, s), (pos, s)


def test_raises_take_the_largest_and_lowers_add(cop, table):
    from publicbench.simplay import Play
    p = Play(table)
    p1, p2, p5 = (slot_of(cop, n) for n in ("P1", "P2", "P5"))
    for c in (p1, p2):
        p.rx(1, *pos_frame(c, 1.0), now_us=0)
    assert p.cents(9) == 200                                  # string 10: C -> D, not E
    assert p.cents(8) == 100 and p.cents(4) == -100 and p.cents(1) == 100
    p.rx(1, *pos_frame(p5, 1.0), now_us=0)
    assert p.cents(9) == 200 - 300                            # raise D + lower A = Bb
    assert p.cents(8) == 100 - 100


def test_curve_lookup_matches_and_clamps(table):
    from publicbench.simplay import lib
    curve = CP.model_curve()
    for c in list(range(-700, 900, 7)) + [0, -400, 600]:
        assert lib().play_counts(table, 3, c) == CP.counts(curve, c), c
    assert lib().play_counts(table, 0, 0) == 0
    assert lib().play_counts(table, 0, 5000) == curve[-1]


def boot(p, bases, now=0):
    """Answer play.c's encoder questions and enables as ten motors would."""
    for _ in range(40):
        f = p.poll(now)
        if f is None:
            break
        mid, d = f
        if d[0] == S.READ_ENCODER:
            p.rx(0, mid, S.pack(mid, bytes([S.READ_ENCODER]) + bases[mid].to_bytes(6, "big", signed=True)), now)
        elif d[0] in (S.SET_RESPOND, S.ENABLE):
            if d[0] == S.SET_RESPOND:
                assert d[1:3] == bytes([1, 0])              # start reply on, arrival reply off
            p.rx(0, mid, S.pack(mid, bytes([d[0], 1])), now)
    assert all(p.state(s) == DRIVE for s in range(CP.STRINGS))


def move_of(f):
    mid, d = f
    assert d[0] == S.MOVE_ABS and S.check(mid, d)
    return mid, int.from_bytes(d[4:7], "big", signed=True)


def test_boot_drive_rate_limit_and_a_lost_lever(cop, table):
    from publicbench.simplay import Play
    p = Play(table)
    bases = {m: 1000 * m - 4000 for m in range(1, 11)}
    boot(p, bases)
    assert [p.base(s) for s in range(10)] == [bases[s + 1] for s in range(10)]
    assert p.poll(1000) is None                               # all at open: nothing to say
    t = 1_000_000
    p.rx(1, *pos_frame(slot_of(cop, "P1"), 1.0), now_us=t)
    got = {}
    while (f := p.poll(t)) is not None:
        mid, c = move_of(f)
        got[mid] = c
    curve = CP.model_curve()
    assert got == {2: bases[2] + CP.counts(curve, 100), 6: bases[6] + CP.counts(curve, 100),
                   10: bases[10] + CP.counts(curve, 200)}
    p.rx(1, *pos_frame(slot_of(cop, "P1"), 0.5), now_us=t + 1000)
    assert p.poll(t + 1000) is None                           # min_us not up for those motors
    t2 = t + K["PLAY_LOST_US"] // 2
    assert {move_of(f)[0] for f in iter(lambda: p.poll(t2), None)} == {2, 6, 10}
    t3 = t + 1000 + K["PLAY_LOST_US"] + 1                     # the lever went quiet
    back = {move_of(f) for f in iter(lambda: p.poll(t3), None)}
    assert back == {(2, bases[2]), (6, bases[6]), (10, bases[10])}


def test_an_uncalibrated_lever_is_at_rest(cop, table):
    from publicbench.simplay import Play
    p = Play(table)
    p.rx(1, *pos_frame(slot_of(cop, "P4"), raw=0xFFFF), now_us=0)
    assert p.cents(2) == 0


def test_rebase_asks_again(table):
    from publicbench.simplay import Play
    p = Play(table)
    boot(p, {m: 0 for m in range(1, 11)})
    p.rebase()
    f = p.poll(10)
    assert f and f[1][0] == S.READ_ENCODER


class FakeBoard:
    """main.c's 'P' lines over a pretend link, into play.c's table check."""

    def __init__(self):
        self.stage = bytearray(CP.SIZE)
        self.kept = None

    def ask(self, line, timeout=1.0):
        from publicbench.simplay import lib
        p = line.split()
        if p[:2] == ["P", "W"]:
            off, data = int(p[2]), bytes.fromhex(p[3])
            if off + len(data) > len(self.stage):
                return ["E", "line"]
            self.stage[off:off + len(data)] = data
            return ["OK", "P"]
        if p == ["P", "S"]:
            if not lib().play_table_ok(bytes(self.stage)):
                return ["E", "table"]
            self.kept = bytes(self.stage)
            return ["OK", "P", "S"]
        if p == ["P"]:
            crc = int.from_bytes(self.kept[-4:], "little") if self.kept else 0
            return ["P", "1", "1", "0", "0" * 10, "%08X" % crc]
        return ["E", "line"]


def test_the_pi_writes_the_table_down(table):
    b = FakeBoard()
    st = CP.write(b, table)
    assert b.kept == table and st[1] == "1"


# ---- end to end -----------------------------------------------------------------------------
REST, SPAN = 3000, 2400                 # lever angles: rest and travel, 14-bit counts
ACCEL = 1200.0                          # turns/s^2: 0.52 turn to 90 % in ~35 ms, as the motor did
                                        # unloaded on 11-02 (39 ms, motor-step-results). NOT loaded.


@pytest.fixture
def rig(cop, table):
    pytest.importorskip("can")
    from publicbench.levers import Levers
    from publicbench.link import CanLink
    from publicbench.sim import SimServo
    from publicbench.simplay import SimMotorCtrl
    names = ("P1", "P2", "LKR")
    angle = {n: REST for n in names}
    levers = {n: SL.SimLever(0x500 + i, (lambda n=n: angle[n]), channel="public-play-b")
              for i, n in enumerate(names)}
    servos = [SimServo(m, channel="public-play-a", accel_turns_s2=ACCEL) for m in range(1, 11)]
    bases = {}
    for sv in servos:
        sv.pos = float(random.Random(sv.id).randrange(-20000, 20000))
        bases[sv.id] = int(sv.pos)
    for th in list(levers.values()) + servos:
        th.start()
    pi = CanLink(channel="public-play-b", interface="virtual")   # the Pi's tuning role, on bus B
    lv = Levers(pi, bus=0)
    for i, n in enumerate(names):                                # assign, calibrate, save
        assert lv.assign(0x500 + i, slot_of(cop, n))
    time.sleep(0.05)
    for n in names:
        s = slot_of(cop, n)
        assert lv.cal(s, REST, REST + SPAN) and lv.save(s)
    mc = SimMotorCtrl(table, a_channel="public-play-a", b_channel="public-play-b")
    mc.start()
    end = time.monotonic() + 3
    while time.monotonic() < end and not all(mc.play.state(s) == DRIVE for s in range(10)):
        time.sleep(0.01)
    assert all(mc.play.state(s) == DRIVE for s in range(10)), "every motor based and enabled"
    assert not any(sv.active for sv in servos), "arrival replies off"
    yield angle, servos, bases, mc
    mc.stop()
    pi.close()
    for th in list(levers.values()) + servos:
        th.stop()


def counts_per_cent(curve, cents):
    return (CP.counts(curve, cents + 5) - CP.counts(curve, cents - 5)) / 10.0


def settle_time(servo, t0, goal, tol):
    """Time after t0 from which the motor stays within tol counts of goal."""
    h = [x for x in list(servo.history) if x[0] >= t0]
    last_out = t0
    for t, c in h:
        if abs(c - goal) > tol:
            last_out = t
    assert abs(h[-1][1] - goal) <= tol, (h[-1][1], goal)
    return last_out - t0


def test_end_to_end_pedals_and_lever_to_motors(cop, rig):
    angle, servos, bases, mc = rig
    curve = CP.model_curve()
    tgt = lambda s, c: bases[s] + CP.counts(curve, c)
    tol = lambda c: 3 * counts_per_cent(curve, c)               # 3 cents

    # 1. P1 stamped down in one sample: the worst case, a step
    t0 = time.monotonic()
    angle["P1"] = REST + SPAN
    time.sleep(0.4)
    first = min(t for t, mid, d in list(mc.sent) if t >= t0 and d[0] == S.MOVE_ABS) - t0
    lag_step = max(settle_time(servos[s - 1], t0, tgt(s, c), tol(c)) for s, c in ((2, 100), (6, 100), (10, 200)))
    for s in (1, 3, 4, 5, 7, 8, 9):
        assert servos[s - 1].pos == bases[s]                    # nobody else moved

    # 2. P2 pressed over 80 ms, as a foot does, on top of P1: string 10 stays at D
    t0 = time.monotonic()
    while (u := (time.monotonic() - t0) / 0.08) < 1:
        angle["P2"] = REST + int(SPAN * u)
        time.sleep(0.001)
    angle["P2"] = REST + SPAN
    t_full = time.monotonic()
    time.sleep(0.4)
    lag_ramp = max(settle_time(servos[s - 1], t_full, tgt(s, c), tol(c)) for s, c in ((5, -100), (9, 100)))
    assert abs(servos[9].pos - tgt(10, 200)) <= tol(200)

    # 3. LKR half way: string 8 a quarter tone flat, string 4 too
    angle["LKR"] = REST + SPAN // 2
    time.sleep(0.4)
    for s in (4, 8):
        assert abs(servos[s - 1].pos - tgt(s, -50)) <= tol(-50)

    # 4. everything released: every string back at open
    for n in angle:
        angle[n] = REST
    time.sleep(0.5)
    for sv in servos:
        assert abs(sv.pos - bases[sv.id]) <= 4, sv.id
    print("\nstep: first F5 after %.1f ms, within 3 cents after %.1f ms; 80 ms press: %.1f ms behind"
          " the pedal; %d F5 frames" % (first * 1e3, lag_step * 1e3, lag_ramp * 1e3, mc.play.moves()))
    # loose: Python threads on a Pi, not the boards' timing. docs/control-path.md has the budget
    assert first < 0.03 and lag_step < 0.15 and lag_ramp < 0.15
