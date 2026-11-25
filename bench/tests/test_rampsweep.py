"""publicbench.rampsweep's arithmetic, no hardware."""
from publicbench import openloop as OL
from publicbench import rampsweep as R

T = R.T


def test_shape_of_a_triangle_move():
    a, s = 400.0, 0.233                                  # rev/s^2, turns: 48 ms, peak 1160 rpm
    tm = 2 * (s / a) ** 0.5
    def pos(t):                                          # turns at t
        return 0.5 * a * t * t if t < tm / 2 else s - 0.5 * a * (tm - t) ** 2
    curve = [(k * 0.001, pos(min(k * 0.001, tm)) * T) for k in range(int(tm * 1000) + 20)]
    sh = R.shape(curve, s * T)
    assert abs(sh["tri_rev_s2"] - a) / a < 0.1            # 1 ms polls
    assert abs(sh["peak_rpm"] - a * tm / 2 * 60) < 40


def test_long_move_fits_the_raise_budget():
    lo = OL.throw_counts(-2.0)
    assert lo + round(R.LONG_TURN * T) <= OL.throw_counts(2.4)


def test_home_tolerance_is_half_a_cent():
    assert 9.0 < OL.home_tol() < 10.0
