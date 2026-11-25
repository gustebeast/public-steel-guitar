"""publicbench.gates against the pretend bench (publicbench.simqtpy.SimRig: the native firmware,
a pretend TMC2209 counter and a pretend rotor). The rig's physics are assumptions; these tests
prove the scripts tell the cases apart and do their bookkeeping, not what the motor does."""
import json

import pytest

from publicbench import gates as G
from publicbench import simqtpy as Q
from publicbench.qtpy import QtPyBench

pytestmark = pytest.mark.skipif(not Q.compiler(), reason="no native C compiler")


def rig(**kw):
    r = Q.SimRig(**kw)
    g = G.Gate(QtPyBench(ser=r), truth=r.truth, prompt=r.power_cycle, sleep=lambda s: None)
    g.setup()
    return r, g


def test_setup_learns_the_sign_and_starts_at_zero():
    r, g = rig()
    assert g.sign == 1 and g.tone == round(G.TONE_TURNS * 800) and g.per == 64
    assert 0.2 < G.TONE_TURNS < 0.21                # this rig's +-2 st (was 0.52 turn: +3.6/-6.4 st)
    assert r.L.sim_pos() == 0 and g.agrees()


def test_gate_i_tells_counting_from_frozen():
    r, g = rig(counts_when_off=False)
    out = g.gate_i()
    assert out["enn"]["verdict"] == out["toff"]["verdict"] == "frozen" and out["plan"] == "B"
    assert r.truth() == 0 and g.agrees()            # nothing moved; field and rotor still agree

    r, g = rig(counts_when_off=True)
    out = g.gate_i()
    assert out["enn"]["verdict"] == "counts" and out["plan"] == "A"
    assert out["enn"]["back"]                       # it stepped back before turning on again
    assert r.truth() == 0 and g.agrees()


def test_gate_ii_freewheel_restarts_land_on_target():
    r, g = rig(detent=True)
    out = g.gate_ii(cycles=4)
    assert out["worst"] == 0 and out["mscnt_bad"] == 0
    assert (r.L.sim_reg(0x10) & 31) != 0            # hold current put back afterwards


def test_gate_iii_counts_no_mismatch_when_nothing_is_lost():
    r, g = rig()
    out = g.gate_iii(moves=40, rpm=1600)
    assert out["mscnt_bad"] == 0 and out["worst"] == 0


def test_gate_iii_sees_a_lost_edge():
    r, g = rig()
    r.mscnt = (r.mscnt + 64) % 1024                 # the driver missed one step's edge
    r._sync()
    assert g.gate_iii(moves=4)["mscnt_bad"] == 4


def test_gate_iv_snap_matches_prediction_and_restores_exactly():
    r, g = rig()
    out = g.gate_iv(reps=2)
    assert r.cycles == len(out["rows"]) and out["reset_unseen"] == 0 and out["reinit_short"] == 0
    assert out["snap_n"] > 0 and out["snap_ok"] == out["snap_n"]
    assert out["worst"] == 0
    amb = [x for x in out["rows"] if x["ambiguous"]]
    assert amb, "the +-512 phase must be among the targets"
    big = [x for x in out["rows"] if abs(x["predicted"]) >= 1.5]
    assert big, "some targets must need a real snap"
    for x in out["rows"]:
        assert abs(x["target"]) <= g.tone


def test_gate_iv_catches_a_snap_held_short_by_the_screw():
    r, g = rig(stick=40)                            # friction stops it 40 units (5/8 step) short
    out = g.gate_iv(reps=1)
    assert out["snap_ok"] < out["snap_n"]
    assert out["worst"] > 0.5


def test_gate_v_needs_the_reset_seen():
    r, g = rig()
    out = g.gate_v(reps=2)
    assert out["reset_unseen"] == 0 and out["worst"] == 0

    r, g = rig()
    g.prompt = lambda msg: None                     # a "dip" the driver rode through
    out = g.gate_v(reps=1)
    assert out["reset_unseen"] == 1


def test_no_target_past_a_whole_tone():
    r, g = rig()
    with pytest.raises(G.Abort):
        g.go(g.tone + 1)
    assert r.L.sim_pos() == 0


def test_run_logs_and_goes_home(tmp_path):
    r = Q.SimRig()
    o = G.parser().parse_args(["all", "--reps", "1", "--moves", "8", "--log", str(tmp_path / "g.jsonl")])
    rec = G.run(o, b=QtPyBench(ser=r), truth=r.truth, prompt=r.power_cycle, sleep=lambda s: None)
    assert "stopped" not in rec, rec.get("stopped")
    assert rec["i"]["plan"] == "B" and rec["iii"]["mscnt_bad"] == 0 and rec["iv"]["worst"] == 0
    assert r.L.sim_pos() == 0 and r.truth() == 0
    line = json.loads((tmp_path / "g.jsonl").read_text().splitlines()[0])
    assert line["which"] == "all" and line["sign"] == 1


def test_a_dead_uart_stops_the_run_cleanly(tmp_path):
    r = Q.SimRig()
    r.L.sim_fail(1)
    o = G.parser().parse_args(["i", "--log", str(tmp_path / "g.jsonl")])
    rec = G.run(o, b=QtPyBench(ser=r), prompt=r.power_cycle, sleep=lambda s: None)
    assert "stopped" in rec and (tmp_path / "g.jsonl").exists()


def test_gate_2_sweeps_inside_the_travel_and_loses_nothing():
    r, g = rig()
    out = g.gate_2(accs=(400, 1600), reps=4)
    assert out["up"] in (1, -1)
    for kind in ("tone", "long"):
        rows = out["kinds"][kind]
        assert len(rows) == 2 * 2 * 4               # two accelerations, reps each way
        assert all(r_["lost"] == 0 and r_["mscnt_ok"] for r_ in rows)
        assert all(out["lo"] - 1 <= r_["target"] <= max(out["hi"], out["top"]) + 1 for r_ in rows)
    long_ = out["kinds"]["long"]
    assert max(x["target"] for x in long_) - min(x["target"] for x in long_) == round(0.52 * 800) or \
        abs((max(x["target"] for x in long_) - min(x["target"] for x in long_)) - 0.52 * 800) <= 1
    assert r.L.sim_pos() == 0                       # home afterwards


def test_gate_2_stops_at_the_first_acceleration_that_loses_steps():
    r, g = rig()
    calls = {"n": 0}

    def truth():                                    # the shaft slips a full step after a while
        calls["n"] += 1
        return r.truth() - (5 if calls["n"] > 40 else 0)
    g.truth = truth
    out = g.gate_2(accs=(400, 800, 1200), kinds=("tone",), reps=4)
    accs = {x["acc"] for x in out["kinds"]["tone"]}
    assert max(accs) < 1200 and any(x["lost"] for x in out["kinds"]["tone"])


def test_gate_2_needs_the_encoder():
    r = Q.SimRig()
    g = G.Gate(QtPyBench(ser=r), truth=None, sleep=lambda s: None)
    g.setup()
    with pytest.raises(G.Abort):
        g.gate_2()
