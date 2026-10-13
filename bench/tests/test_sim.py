"""The bench's own code, end to end, against the pretend motor and string (no hardware)."""
import time

import numpy as np
import pytest

from psgbench import pitch, servo
from psgbench.link import CanLink
from psgbench.run import Move, run
from psgbench.sim import SimServo, string_audio


@pytest.fixture
def rig():
    sim = SimServo(can_id=1)
    sim.start()
    link = CanLink(channel="psg-sim", interface="virtual")
    s = servo.Servo(link, 1)
    s.enable()
    time.sleep(0.05)
    yield link, sim, s
    link.close()
    sim.stop()


def test_frames_match_the_manuals_examples():
    """MKS SERVO42D/57D_CAN User Manual V1.0.5, sections 5.1, 6.7 and 6.8."""
    h = bytes.fromhex
    assert servo.pack(1, h("30")) == h("3031")
    assert servo.pack(1, servo.move(servo.MOVE_REL, 0x4000, 600, 2)) == h("F40258020040 0091".replace(" ", ""))
    # (the manual prints the -0x4000 F4 example with checksum 09; by its own rule, and by the
    #  matching F5 example two lines down, it is 10)
    assert servo.pack(1, servo.move(servo.MOVE_REL, -0x4000, 600, 2)) == h("F4025802FFC00010")
    assert servo.pack(1, servo.move(servo.MOVE_ABS, 0x4000, 600, 2)) == h("F502580200400092")
    assert servo.pack(1, servo.move(servo.MOVE_ABS, -0x4000, 600, 2)) == h("F5025802FFC00011")


def test_frame_checksum():
    assert servo.pack(1, bytes([0x31])) == bytes([0x31, 0x32])
    assert servo.check(1, servo.pack(1, servo.move(servo.MOVE_REL, -5, 600, 2)))
    assert servo.parse(1, servo.pack(1, bytes([0x31]) + (-7).to_bytes(6, "big", signed=True))) == (0x31, -7)


def test_position_round_trip(rig):
    link, sim, s = rig
    assert s.position() == 0


def test_one_step_is_timed_and_heard(rig):
    link, sim, s = rig
    quarter = servo.COUNTS_PER_TURN // 4
    rec = run(link, [Move(0.3, 1, quarter, rpm=600)], poll_hz=500, tail=0.6)
    # the command left when it was asked to, to within the computer's scheduling
    assert abs(rec.sent[0] - (rec.t_start + 0.3)) < 0.005
    # the motor got there and said so
    assert rec.positions[1][-1][1] == quarter
    assert len(rec.arrived[1]) == 1
    travel = rec.arrived[1][0] - rec.sent[0]
    assert 0.02 < travel < 0.2
    # the polls came back at about the rate asked for
    assert len(rec.positions[1]) > 0.8 * 500 * (rec.t_end - rec.t_start)
    # and the string's sound says the same thing as the encoder
    sr = 48000.0
    audio = string_audio(sim.history, rec.t_start, rec.t_end, sr, f0=220.0, cents_per_turn=200.0)
    f, _ = pitch.track(audio, sr, 220.0)
    st = pitch.step(f, sr, rec.t_start, rec.sent[0], tol_cents=3.0)
    assert abs(st.moved_cents - 50.0) < 1.0
    assert abs(st.before_hz - 220.0) < 0.2
    assert abs(st.settle_s - travel) < 0.03
    assert st.overshoot_cents < 3.0


def test_two_moves_in_order(rig):
    link, sim, s = rig
    rec = run(link, [Move(0.1, 1, 2000), Move(0.4, 1, -2000)], tail=0.4)
    assert rec.sent[0] < rec.sent[1]
    assert len(rec.arrived[1]) == 2
    pos = np.array([p for _, p in rec.positions[1]])
    assert pos.max() == 2000 and pos[-1] == 0
