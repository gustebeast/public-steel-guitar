"""Flashing the lever and pedal boards from the Pi (leverisp.py): motor_ctrl's arms.c, the real
lever.c / ldr.c on every board, and the chain's power wiring, on one simulated clock
(simchain.py)."""
import pytest

from publicbench import leverisp as LI
from publicbench import simarms as SA
from publicbench import simchain as SC
from publicbench import simlever as SL

pytestmark = pytest.mark.skipif(not SL.compiler(), reason="no native C compiler")

APP = b"\x13" * 64          # a stand-in application, as SimLever's
LOADER = b"boot.bin"        # the simulator's ISP only needs to know one was handed over
AK = SA.K


def test_a_window_hands_one_arm_over_and_ends_by_itself():
    a = SA.Arms()
    assert a.powered(0) and a.powered(1) and not a.lane()
    assert a.flash(1, 100, 0, 0)
    assert not a.flash(0, 100, 0, 0) and not a.power(0, 0, 0)     # one window, nothing else
    a.poll(AK["ARM_LEAD_US"] - 1)
    assert not a.usb(1) and not a.lane()                          # the OK goes out first
    a.poll(AK["ARM_LEAD_US"])
    assert a.usb(1) and a.lane() and not a.usb(0) and a.powered(1)
    end = AK["ARM_LEAD_US"] + 100000
    a.poll(end)
    assert not a.usb(1) and not a.lane() and not a.powered(0) and not a.powered(1)
    a.poll(end + AK["ARM_OFF_US"])
    assert a.powered(0) and a.powered(1) and not a.busy()


def test_a_cycled_window_brings_the_arm_up_on_the_lane():
    a = SA.Arms()
    assert a.flash(0, 1000, 1, 0)
    a.poll(AK["ARM_LEAD_US"])
    assert a.usb(0) and not a.powered(0)
    a.poll(AK["ARM_LEAD_US"] + AK["ARM_OFF_US"])
    assert a.usb(0) and a.powered(0)


def test_refused():
    a = SA.Arms()
    assert not a.flash(2, 100, 0, 0) and not a.flash(0, 0, 0, 0)
    assert not a.flash(0, AK["ARM_WINDOW_MAX"] + 1, 0, 0) and not a.power(0, 3, 0)


def bench(levers, pedals=None):
    pedals = pedals if pedals is not None else [SC.Node(0x500 + i, APP) for i in range(2)]
    return SC.SimBench([pedals, levers])


def test_walk_gives_slots_in_chain_order_and_stops_at_the_silent_board():
    ch = [SC.Node(0x100, APP), SC.Node(0x101, APP), SC.Node(0x102, None, blank=True), SC.Node(0x103, APP)]
    b = bench(ch)
    order, silent = LI.walk(b, 1, [4, 5, 6, 7], log=lambda *_: None)
    assert [h.uid for h in order] == [0x100, 0x101] and [h.slot for h in order] == [4, 5]
    assert silent
    assert not any(n.powered for n in b.chains[0])                # the pedals held dark


def test_blank_boards_get_their_loader_over_usb_and_their_application_over_can():
    ch = [SC.Node(0x100, APP), SC.Node(0x101, None, blank=True), SC.Node(0x102, None, blank=True),
          SC.Node(0x103, APP)]
    b = bench(ch)
    order = LI.flash_arm(b, 1, [0, 1, 2, 3], LOADER, APP, log=lambda *_: None)
    assert [h.uid for h in order] == [0x100, 0x101, 0x102, 0x103]
    assert [h.slot for h in order] == [0, 1, 2, 3] and all(h.mode == 0 for h in order)
    assert [n.isp_writes for n in ch] == [0, 1, 1, 0]
    assert b.windows == [(1, False), (1, False)]                  # each cycled by the board before
    assert all(n.board.app_ok() for n in ch)


def test_a_blank_first_board_is_cycled_by_motor_ctrl():
    ch = [SC.Node(0x100, None, blank=True), SC.Node(0x101, APP)]
    b = bench(ch)
    order = LI.flash_arm(b, 1, [0, 1], LOADER, APP, log=lambda *_: None)
    assert [h.uid for h in order] == [0x100, 0x101]
    assert b.windows == [(1, True)]


def test_a_board_with_a_broken_application_is_written_over_can_alone():
    ch = [SC.Node(0x100, APP), SC.Node(0x101, None), SC.Node(0x102, APP)]   # 0x101: its loader, no app
    b = bench(ch)
    order = LI.flash_arm(b, 1, [0, 1, 2], LOADER, APP, log=lambda *_: None)
    assert [h.mode for h in order] == [0, 0, 0] and b.windows == []


def test_the_pedal_arm_too():
    ped = [SC.Node(0x500, APP), SC.Node(0x501, None, blank=True)]
    b = bench([SC.Node(0x100, APP)], ped)
    order = LI.flash_arm(b, 0, [10, 11], LOADER, APP, log=lambda *_: None)
    assert [h.slot for h in order] == [10, 11] and b.windows == [(0, False)]


def test_a_dead_board_is_named_not_retried_for_ever():
    ch = [SC.Node(0x100, APP), SC.Node(0x101, None, blank=True, dead=True), SC.Node(0x102, APP)]
    b = bench(ch)
    with pytest.raises(SystemExit, match="no ROM loader"):
        LI.flash_arm(b, 1, [0, 1, 2], LOADER, APP, log=lambda *_: None)
