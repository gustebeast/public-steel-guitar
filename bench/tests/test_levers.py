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



def test_release_frees_the_pair_everywhere_and_cycles_one_board():
    """ALL 'U' ms, slot: every board lets go of the pair; only the named slot (the board BEFORE
    the one to flash) cycles its next board (docs/lever-usb-flash.md)."""
    lv = calibrated()                                       # slot 3
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_RELEASE"]]) + (500).to_bytes(2, "little") + bytes([3]))
    assert lv.take_release() is None                        # a broadcast op only
    lv.rx(K["ID_ALL"], bytes([K["LC_RELEASE"]]) + (500).to_bytes(2, "little") + bytes([3]))
    assert lv.take_release() == (500, True)
    lv.rx(K["ID_ALL"], bytes([K["LC_RELEASE"]]) + (500).to_bytes(2, "little") + bytes([5]))
    assert lv.take_release() == (500, False)                # another board's turn: release only
    lv.rx(K["ID_ALL"], bytes([K["LC_RELEASE"], 0, 0, K["SLOT_NONE"]]))
    assert lv.take_release() == (1, False)                  # 0 ms still means release
    lv.rx(K["ID_ALL"], bytes([K["LC_RELEASE"], 0x10, 0]))   # no slot given: ignored
    assert lv.take_release() is None


def test_hold_and_next_walk_the_chain_one_board_at_a_time():
    """ALL 'H' holds every board's next board dark (and stops the automatic power-up);
    CMD 'N' 1 / 0 lets one board's next board up or down, and is acknowledged."""
    lv = calibrated()
    while lv.poll(0):
        pass
    assert not lv.held()
    lv.rx(K["ID_ALL"], bytes([K["LC_HOLD"]]))
    assert lv.held() and lv.take_next() == 2
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_NEXT"], 1]))
    assert lv.take_next() == 1
    r = LV.decode(0, *[x for i, x in enumerate(lv.poll(0)) if i != 1])
    assert r == LV.Reply(0, 3, "N", True)
    lv.rx(K["ID_ALL"], bytes([K["LC_HOLD"]]))
    assert lv.take_next() == 0                  # an 'N' 1's next board stays up through 'H'
    lv.rx(K["ID_CMD"] + 3, bytes([K["LC_NEXT"], 0]))
    assert lv.take_next() == 2
    lv.rx(K["ID_ALL"], bytes([K["LC_HOLD"]]))
    assert lv.take_next() == 2                  # ...and one 'N' 0 put down stays down


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


# ---- the CAN loader (ldr.c) -------------------------------------------------------------------
import zlib


def drain(b, t=0):
    out = []
    for _ in range(50):
        got = b.poll(t)
        if not got:
            break
        out += got
    return out


def ldr_send(b, slot, op, args=b""):
    b.rx(K["ID_LDR"] + slot, op.encode() + args)
    return [LV.decode(0, i, d) for i, _e, d in drain(b) if i == K["ID_LDR_R"] + slot]


def write_image(b, slot, img, bad_page=None, stop_after=None):
    assert ldr_send(b, slot, "E", len(img).to_bytes(4, "little"))[0].ok
    padded = img + b"\xff" * (-len(img) % 256)
    for no in range(len(padded) // 256):
        if stop_after is not None and no == stop_after:
            return
        p = padded[no * 256:(no + 1) * 256]
        crc = zlib.crc32(p) ^ (1 if no == bad_page else 0)
        b.rx(K["ID_LDR"] + slot, b"W" + no.to_bytes(2, "little") + crc.to_bytes(4, "little"))
        for k in range(0, 256, 8):
            b.rx(K["ID_LDR_D"] + slot, p[k:k + 8])
        r = [LV.decode(0, i, d) for i, _e, d in drain(b) if i == K["ID_LDR_R"] + slot]
        assert r and r[0].op == "W" and r[0].ok == (no != bad_page)
    return ldr_send(b, slot, "C", len(img).to_bytes(3, "little") + zlib.crc32(img).to_bytes(4, "little"))[0]


def slotted(b, slot=2):
    b.rx(K["ID_ALL"], bytes([K["LC_SLOT"]]) + b.lv.uid.to_bytes(4, "little") + bytes([slot]))
    drain(b)
    return slot


def test_blank_board_waits_in_its_loader_and_takes_an_image():
    b = SL.Board(0x77)
    assert b.in_loader
    h = [LV.decode(0, i, d) for i, e, d in drain(b) if e][0]
    assert h.mode == 1 and h.slot is None
    s = slotted(b)
    r = ldr_send(b, s, "I")[0]
    assert r.ok and r.more == bytes([K["LDR_VERSION"], 0])
    img = bytes(range(256)) * 9 + b"tail"
    assert write_image(b, s, img).ok
    assert ldr_send(b, s, "G")[0].ok and not b.in_loader     # restarted into the application
    assert b.mem[K["APP_AT"]:K["APP_AT"] + len(img)] == img
    assert b.lv.slot() == s                                     # the slot lived through it


def test_a_bad_page_is_refused_and_a_half_update_stays_in_the_loader():
    b = SL.Board(0x78, app_image=b"\x55" * 300)
    assert not b.in_loader
    s = slotted(b)
    b.rx(K["ID_CMD"] + s, b"B")                                 # the application: to the loader
    drain(b)
    assert b.in_loader
    write_image(b, s, b"\x66" * 2000, bad_page=1, stop_after=3)  # page 1 refused, then it stops
    b.reset()
    assert b.in_loader                                          # the record was erased: no app
    assert not ldr_send(b, s, "C", (2000).to_bytes(3, "little") + zlib.crc32(b"\x66" * 2000).to_bytes(4, "little"))[0].ok
    assert write_image(b, s, b"\x66" * 2000).ok
    b.reset()
    assert not b.in_loader


def test_loader_ignores_other_slots():
    b = SL.Board(0x79)
    s = slotted(b, 5)
    b.rx(K["ID_LDR"] + 6, b"I")
    assert not [1 for i, _e, _d in drain(b) if i == K["ID_LDR_R"] + 6]
    assert ldr_send(b, s, "Z")[0] == LV.LdrReply(0, s, "Z", False, b"")


def test_end_to_end_update_over_the_bus(bus):
    from publicbench import leverflash
    lv, sims, _angles = bus
    assert lv.assign(0xA1, 4)
    img = bytes((i * 7) & 0xFF for i in range(3000))
    leverflash.write(lv, 4, img, log=lambda *_: None)
    m = sims[0].board.mem
    assert m[K["APP_AT"]:K["APP_AT"] + len(img)] == img and sims[0].board.app_ok()
    assert not sims[0].board.in_loader
