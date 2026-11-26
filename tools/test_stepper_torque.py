"""tools/stepper_torque.py: the model against Leadshine's published curve, and its arithmetic."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import stepper_torque as S  # noqa: E402


def test_the_model_matches_leadshines_24v_curve_for_the_42cm06():
    m = S.MOTORS["42CM06"]
    for rpm, published in S.LEADSHINE_42CM06_24V:
        got = S.pullout(m, rpm, 2.5, 24.0)
        assert abs(got - published) / published < 0.08, (rpm, got, published)


def test_less_current_never_gives_more_torque_and_speed_costs_torque():
    m = S.MOTORS["42CM06"]
    assert S.pullout(m, 1600, 1.4) < S.pullout(m, 1600, 1.8) < S.pullout(m, 1600, 2.5)
    assert S.pullout(m, 2000, 1.4) < S.pullout(m, 1250, 1.4) < S.pullout(m, 500, 1.4)


def test_self_locking_threshold_and_the_fifty_percent_floor():
    sc = S.screw(128.0, mu_factor=1.0)
    assert abs(sc["lead_deg"] - 5.20) < 0.01 and abs(sc["mu_threshold"] - 0.0878) < 0.001
    assert abs(sc["load"] - sc["floor"]) < 1e-3          # exactly self-locking = 50 % efficient
    assert S.screw(128.0, 1.5)["load"] > sc["load"]


def test_a_t90_of_39_ms_is_a_50_ms_triangle():
    mv = S.move(0.52, 0.039, 82e-7, 0.0)
    assert abs(mv["t"] - 0.0503) < 0.0005 and abs(mv["peak_rpm"] - 1241) < 5
    assert abs(mv["accel_rev"] - 4 * 0.52 / mv["t"] ** 2) < 1e-6
    assert math.isclose(S.T90_OF_TRIANGLE, 0.7764, abs_tol=1e-4)
