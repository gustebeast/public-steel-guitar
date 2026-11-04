"""The lever boards: the firmware's own logic (lever.c, compiled natively) and the Pi's decode
of what it sends, separately and end to end on the simulator's bus."""
import binascii
import time

import pytest

from publicbench import levers as LV
from publicbench import simlever as SL

K = LV.K
pytestmark = pytest.mark.skipif(not SL.compiler(), reason="no native C compiler")


def settle(lv, raw, n=40):
    for _ in range(n):
        lv.sample(raw)


def calibrated(rest=4000, full=6000, uid=0x1234):
    lv = SL.Lever(uid)
    lv.rx(K["ID_ALL"], bytes([K["LC_SLOT"]]) + uid.to_bytes(4, "little") + bytes([3]))
    assert lv.slot() == 3
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_CAL"]]) + rest.to_bytes(2, "little") + full.to_bytes(2, "little"))
    return lv


def test_crc_is_zlibs():
    data = b"lever config page"
    assert SL.lib().lever_crc32(data, len(data)) == binascii.crc32(data)


def test_fresh_board_has_no_slot_and_only_says_hello():
    lv = SL.Lever(0xCAFEF00D)
    settle(lv, 1000)
    assert lv.pos() == K["POS_NONE"] and lv.status() & K["LV_UNCAL"]
    f = lv.poll(0)
    assert f[0] == K["ID_HELLO"] | 0xFEF00D and f[1]
    h = LV.decode(0.0, f[0], f[2])
    assert isinstance(h, LV.Hello) and h.uid == 0xCAFEF00D and h.slot is None and h.mode == 0
    sent = [lv.poll(t) for t in range(1000, 3_000_000, 1000)]
    ids = {f[0] for f in sent if f}
    assert ids == {K["ID_HELLO"] | 0xFEF00D}                # no POS while it has no slot
    assert sum(1 for f in sent if f) == 2                    # one HELLO a second


def test_position_across_travel_both_directions_and_through_the_wrap():
    for rest, full in ((4000, 6000), (6000, 4000), (16000, 600)):   # last: travel crosses 0
        lv = calibrated(rest, full)
        span = ((full - rest + 8192) % 16384) - 8192
        for frac in (0.0, 0.25, 0.5, 1.0):
            settle(lv, (rest + round(span * frac)) % 16384)
            assert abs(lv.pos() / K["POS_FULL"] - frac) < 0.002, (rest, full, frac, lv.pos())
        settle(lv, (rest - span // 4) % 16384)                       # past rest: clamped, flagged
        assert lv.pos() == 0 and lv.status() & K["LV_OUTSIDE"]


def test_one_bad_read_is_thrown_out():
    lv = calibrated()
    settle(lv, 5000)
    p = lv.pos()
    lv.sample(13000)                                          # one SPI glitch
    assert abs(lv.pos() - p) < 20
    settle(lv, 5000, 3)
    assert abs(lv.pos() - p) < 20


def test_send_rules_deadband_rate_and_heartbeat():
    lv = calibrated()
    settle(lv, 5000)
    t = 10_000_000
    while lv.poll(t):                                          # drain the reply, first POS, DIAG
        pass
    assert lv.poll(t + 1000) is None                           # nothing moved
    settle(lv, 5400)
    assert lv.poll(t + 1000) is None                           # moved, but TX_MIN_US not up
    f = lv.poll(t + K["TX_MIN_US"])
    assert f and f[0] == K["ID_POS"] + 3
    p = LV.decode(0, f[0], f[2])
    assert abs(p.pos - 0.7) < 0.002 and p.status == K["LV_UNSAVED"]
    t2 = t + K["TX_MIN_US"]
    assert lv.poll(t2 + K["TX_MIN_US"]) is None                # still: no change, no frame
    f = lv.poll(t2 + K["TX_IDLE_US"])
    assert f and f[0] == K["ID_POS"] + 3                       # the heartbeat


def test_calibration_survives_a_reboot_only_once_saved():
    lv = calibrated()
    lv.reboot()
    assert lv.slot() == 3                                      # the slot was saved on assignment
    settle(lv, 5000)
    assert lv.pos() == K["POS_NONE"]                           # ...the calibration was not
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_CAL"]]) + (4000).to_bytes(2, "little") + (6000).to_bytes(2, "little"))
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_SAVE"]]))
    lv.reboot()
    settle(lv, 5000)
    assert abs(lv.pos() / K["POS_FULL"] - 0.5) < 0.002 and not lv.status() & K["LV_UNSAVED"]


def test_commands_to_another_slot_are_ignored_and_unknown_ops_refused():
    lv = calibrated()
    lv.rx(K["ID_CMD"] + 4, bytes([K["LC_REST"]]))
    assert lv.poll(0)[0] != K["ID_REPLY"] + 4
    lv = calibrated()
    while lv.poll(0):
        pass
    lv.rx(K["ID_CMD"] + 3, b"Z")
    r = LV.decode(0, *[x for i, x in enumerate(lv.poll(0)) if i != 1])
    assert r == LV.Reply(0, 3, "Z", False)


@pytest.fixture
def bus():
    pytest.importorskip("can")
    from publicbench.link import CanLink
    angles = {0xA1: 5000, 0xB2: 9000}
    sims = [SL.SimLever(uid, (lambda u=uid: angles[u]), channel="public-lever-sim") for uid in angles]
    for s in sims:
        s.start()
    link = CanLink(channel="public-lever-sim", interface="virtual")
    yield LV.Levers(link, bus=0), sims, angles
    link.close()
    for s in sims:
        s.stop()


def test_end_to_end_assign_calibrate_save_reboot(bus):
    lv, sims, angles = bus
    found = lv.identify()
    assert set(found) == {0xA1, 0xB2} and all(h.slot is None for h in found.values())
    assert lv.assign(0xA1, 0) and lv.assign(0xB2, 1)
    angles[0xA1] = 5000
    time.sleep(0.05)
    assert lv.rest(0)
    angles[0xA1] = 7000
    time.sleep(0.05)
    assert lv.full(0)
    assert lv.save(0)
    angles[0xA1] = 6000
    time.sleep(0.1)
    assert abs(lv.position(0) - 0.5) < 0.01
    assert lv.position(1) is None                              # assigned, not calibrated
    sims[0].reboot()
    time.sleep(0.1)
    lv.update()
    assert lv.hello[0xA1].slot == 0                            # it comes back as itself
    angles[0xA1] = 6500
    time.sleep(0.1)
    assert abs(lv.position(0) - 0.75) < 0.01
    d = lv.diag[0]
    assert (d.rest, d.full, d.version) == (5000, 7000, LV.K["LEVER_VERSION"])
