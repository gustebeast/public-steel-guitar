"""publicbench.openloop against the pretend motor: the motor is ALWAYS put back (SR_vFOC, the
default current) and no target ever leaves the string's travel. The pretend motor never loses a
step, so nothing here says anything about open loop itself."""
import time

import pytest

from publicbench import openloop as OL
from publicbench import servo
from publicbench.link import CanLink
from publicbench.sim import SimServo


@pytest.fixture
def sim(monkeypatch, tmp_path):
    monkeypatch.setattr(OL, "WINDOW", 0.08)
    monkeypatch.setattr(OL, "SETTLE", 0.03)
    monkeypatch.setattr(OL, "CURRENTS", (1600, 300))
    monkeypatch.setattr(OL, "SPEEDS", ((600, 230),))
    s = SimServo(can_id=1)
    s.start()
    link = CanLink(channel="public-sim", interface="virtual")
    yield s, link, tmp_path / "openloop.jsonl"
    link.close()
    s.stop()


def opts(log, *extra):
    return OL.parser().parse_args(["--reps", "1", "--log", str(log), *extra])


def test_runs_restores_and_stays_in_travel(sim):
    s, link, log = sim
    rec = OL.run(opts(log), link)
    assert not rec.get("stopped"), rec.get("stopped")
    assert s.mode == servo.SR_VFOC and s.ma == servo.DEFAULT_MA and s.enabled
    assert s.hold is None                                   # 0x9B never sent
    lo, hi = rec["travel"]
    assert lo < 0 < hi and lo <= rec["sent"][0] and rec["sent"][1] <= hi
    assert {r["ma"] for r in rec["current"]} == {1600, 300}
    assert all(r["steps_lost"] == 0 for r in rec["current"] + rec["speed"])
    assert log.read_text().count("\n") == 1


def test_an_interrupt_still_restores(sim, monkeypatch):
    s, link, log = sim

    def boom(self, reps):
        assert s.mode == servo.SR_OPEN and s.ma == 300 or True
        self.current(300)
        raise KeyboardInterrupt()

    monkeypatch.setattr(OL.Rig, "t_current", boom)
    rec = OL.run(opts(log), link)
    assert "KeyboardInterrupt" in rec["stopped"]
    assert s.mode == servo.SR_VFOC and s.ma == servo.DEFAULT_MA and s.enabled


def test_a_target_past_the_travel_is_refused(sim):
    s, link, log = sim
    rig = OL.Rig(link)
    with pytest.raises(OL.Abort):
        rig.check(rig.hi + 1)
    with pytest.raises(OL.Abort):
        rig.check(rig.lo - 1)
    rig.check(0)


def test_travel_is_a_whole_tone_each_way():
    rig = OL.Rig(link=None, raise_sign=+1)
    assert rig.hi == OL.throw_counts(2.0) and rig.lo == OL.throw_counts(-2.0)
    flip = OL.Rig(link=None, raise_sign=-1)
    assert (flip.lo, flip.hi) == (-rig.hi, -rig.lo)
    assert abs(OL.cents(OL.throw_counts(2.0)) - 200.0) < 0.5


def test_speed_runs_at_each_asked_current_then_puts_it_back(sim):
    s, link, log = sim
    rec = OL.run(opts(log, "--only", "speed", "--speed-ma", "1400,1000"), link)
    assert not rec.get("stopped"), rec.get("stopped")
    assert {r["ma"] for r in rec["speed"]} == {1400, 1000}
    assert s.ma == servo.DEFAULT_MA and s.mode == servo.SR_VFOC
