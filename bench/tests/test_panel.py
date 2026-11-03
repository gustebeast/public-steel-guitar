import numpy as np

from guitarbench.panel import Fit, Lockin


def carrier(sig):
    """A photodiode's input at 192 kHz: `sig`, at 48 kHz, as the depth of the gated light."""
    sq = np.repeat(sig, 4) * np.tile([1.0, 1.0, -1.0, -1.0], len(sig))
    return 1000.0 * sq


def test_lockin_by_blocks_gets_the_string_back():
    t = np.arange(48000) / 48000.0
    want = 1.0 + 0.1 * np.sin(2 * np.pi * 440.0 * t)
    x = carrier(want)
    lock = Lockin()
    y = np.concatenate([lock(x[at:at + 960 * 4]) for at in range(0, len(x), 960 * 4)])
    got, ref = y[4800:], want[4800:]
    got, ref = got - got.mean(), ref - ref.mean()
    k = np.dot(got, ref) / np.dot(ref, ref)
    assert np.std(got - k * ref) < 0.02 * np.std(k * ref)


def test_fit_is_continuous_and_keeps_the_rate():
    fit = Fit(48000.0, 48076.0)
    t = np.arange(48000) / 48000.0
    x = np.sin(2 * np.pi * 440.0 * t)
    y = np.concatenate([fit(x[at:at + 240]) for at in range(0, len(x), 240)])
    assert abs(len(y) - 48076) <= 2
    # one sample late: each block interpolates from the last sample of the one before
    want = np.sin(2 * np.pi * 440.0 * (np.arange(len(y)) / 48076.0 - 1 / 48000.0))
    assert np.max(np.abs(y - want)[1:]) < 0.01     # the first starts from silence
