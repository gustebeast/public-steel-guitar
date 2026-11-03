"""The phone page's controller and server, against the pretend motors (no hardware)."""
import asyncio
import base64
import json
import math
import os
import socket
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pi", "phone"))
import pitchctl as P            # noqa: E402
import server as S              # noqa: E402


def test_whole_tone_is_052_turn_on_the_model():
    """The number bronner's step test used for string 1: 0.52 turn = a whole tone from open."""
    assert abs(P.turns(2.0) - 0.52) < 0.005
    assert P.turns(0.0) == 0.0
    assert P.turns(-12.0) < 0 and P.turns(4.0) > P.turns(2.0)


def test_creep_moves_base_and_stays():
    p = P.Pitch()
    assert p.press("a", "pu")
    for _ in range(20):
        p.tick(0.05)
    assert abs(p.base - P.CREEP_ST_S) < 1e-6
    p.release("a", "pu")
    p.tick(1.0)
    assert abs(p.base - P.CREEP_ST_S) < 1e-6


def test_bend_returns_on_release_and_only_its_owner_can_release():
    p = P.Pitch(base=0.5)
    p.press("a", "wu")
    assert p.target == 2.5
    p.release("b")                  # another phone letting go does nothing
    assert p.target == 2.5
    p.release("a", "wu")
    assert p.target == 0.5


def test_raise_is_clamped_and_buttons_say_so():
    p = P.Pitch(base=3.0)
    assert p.can("hu") and not p.can("wu")
    assert not p.press("a", "wu")
    p.press("a", "pu")
    for _ in range(100):
        p.tick(0.05)
    assert p.base == P.RAISE_MAX and not p.can("pu") and not p.can("hu")
    p = P.Pitch(base=1.5)
    p.press("a", "wu")              # bent to 3.5: a creep under it stops at 2.0
    p.press("a", "pu")
    for _ in range(100):
        p.tick(0.05)
    assert abs(p.target - P.RAISE_MAX) < 1e-9


def test_driver_moves_fast_for_steps_and_slow_for_creep():
    m = P.MockMotors(strings=(1, 2))
    p = P.Pitch()
    d = P.Driver(m, p)
    d.step(0.05)
    m.log.clear()
    p.press("a", "hu")
    d.step(0.05)
    half = math.ceil(P.turns(1.0) / P.STEP_S * 60.0)          # a half step in STEP_S
    assert {r[3] for r in m.log} == {half}
    assert m.log[0][2] == round(P.turns(1.0) * P.COUNTS_PER_TURN)
    p.release("a", "hu")
    m.log.clear()
    d.step(0.05)
    assert m.log[0][2] == 0 and m.log[0][3] == half
    p.press("a", "pu")
    p.tick(0.05)
    m.log.clear()
    d.step(0.05)
    assert all(r[3] < 100 for r in m.log)


def test_home_survives_a_restart(tmp_path):
    st = str(tmp_path / "state.json")
    m = P.MockMotors(strings=(1,))
    p = P.Pitch()
    d = P.Driver(m, p, st)
    p.base = 1.0
    d.step(0.05)
    d.save()
    m.pos = dict(m.goal)                      # it got there
    p2 = P.Pitch()
    d2 = P.Driver(m, p2, st)
    assert p2.base == 1.0 and d2.home == d.home


def test_a_busy_port_is_left_alone_until_a_press():
    class Busy(P.MockMotors):
        busy = True
        reads = 0

        def home(self):
            self.reads += 1
            if self.busy:
                raise P.PortBusy("bench script has it")
            return super().home()
    m = Busy(strings=(1,))
    p = P.Pitch()
    d = P.Driver(m, p)
    assert d.home is None and m.reads == 1
    for _ in range(5):
        d.step(0.05)                          # nothing held: the port is not tried
    assert m.reads == 1
    m.busy = False
    p.press("a", "hu")
    d.step(0.05)                              # the press reads the motors, then moves them
    assert d.home == {1: 0} and m.goal[1] == round(P.turns(1.0) * P.COUNTS_PER_TURN)


def test_font_covers_the_page():
    import font
    for s in ("PITCH", "HALF", "WHOLE", "MOCK", "NO LINK", "PSG", "+0.123456789-.", "^v"):
        assert all(ch in font.GLYPHS for ch in s)
    assert all(len(g) == 7 and all(len(r) == 5 for r in g) for g in font.GLYPHS.values())


# ── the server, over a real socket ───────────────────────────────────────────────────────
def _ws_frame(obj):
    data = json.dumps(obj).encode()
    mask = b"\x01\x02\x03\x04"
    return bytes([0x81, 0x80 | len(data)]) + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(data))


async def _read_msg(r):
    h = await r.readexactly(2)
    n = h[1] & 0x7F
    if n == 126:
        n = struct.unpack(">H", await r.readexactly(2))[0]
    return json.loads(await r.readexactly(n))


async def _latest(r, t=0.3):
    last = None
    end = asyncio.get_event_loop().time() + t
    while True:
        try:
            last = await asyncio.wait_for(_read_msg(r), max(0.01, end - asyncio.get_event_loop().time()))
        except asyncio.TimeoutError:
            return last


@pytest.fixture
def port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    n = s.getsockname()[1]
    s.close()
    return n


def test_server_page_icon_and_a_dropped_phone_lets_go(port):
    async def go():
        motors = P.MockMotors((1,))
        drv = P.Driver(motors, P.Pitch())
        hub = S.Hub(drv, motors)
        S.ICON = S.icon_png()
        srv = await asyncio.start_server(lambda r, w: S.handle(hub, r, w), "127.0.0.1", port)
        task = asyncio.ensure_future(hub.run())
        try:
            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
            page = await r.read()
            assert b"200 OK" in page and b"<canvas" in page
            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(b"GET /icon.png HTTP/1.1\r\nHost: x\r\n\r\n")
            assert (await r.read()).split(b"\r\n\r\n", 1)[1][:8] == b"\x89PNG\r\n\x1a\n"

            key = base64.b64encode(os.urandom(16)).decode()
            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(("GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                     "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % key).encode())
            assert b"101" in await r.readuntil(b"\r\n\r\n")
            assert (await _read_msg(r))["link"] == "mock"
            w.write(_ws_frame({"t": "down", "b": "wu"}))
            assert (await _latest(r))["bend"] == 2.0
            assert motors.goal[1] == round(P.turns(2.0) * P.COUNTS_PER_TURN)
            w.close()                                  # the phone vanishes mid-bend
            await asyncio.sleep(0.3)
            assert hub.p.bend is None and motors.goal[1] == 0

            r, w = await asyncio.open_connection("127.0.0.1", port)
            w.write(("GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                     "Sec-WebSocket-Key: %s\r\n\r\n" % key).encode())
            await r.readuntil(b"\r\n\r\n")
            w.write(_ws_frame({"t": "down", "b": "hd"}))
            await asyncio.sleep(0.3)
            assert hub.p.bend is not None
            await asyncio.sleep(S.HOLD_TIMEOUT + 0.3)  # a phone asleep with its socket open
            assert hub.p.bend is None
            w.close()
        finally:
            task.cancel()
            srv.close()
    asyncio.run(go())
