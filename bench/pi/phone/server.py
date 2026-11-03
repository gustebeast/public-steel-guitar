"""The phone page: https://public-steel-guitar.home (docs/phone-ui.md).

    python3 server.py                     the motors, through motor_ctrl on USB, port 80
    python3 server.py --tls-dir DIR       and HTTPS on 443 (install.sh makes DIR)
    python3 server.py --mock --port 8765  pretend motors, for a computer with no instrument

Standard library only (pyserial for the real motors, as the rest of bench/ uses): one static
page and one WebSocket, /ws. The page sends {"t": "down"|"up", "b": button} and a ping while
anything is held; the server answers every change with the state.

NO STRING IS LEFT BENT: a bend or a creep belongs to the connection that pressed it, and goes
when that connection does, when the page says it was hidden, or when a holding page has been
silent for HOLD_TIMEOUT (a phone that sleeps mid-press keeps its socket open for a while).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import struct
import threading
import time
import zlib

from pitchctl import BUTTONS, Driver, MockMotors, Pitch, STRINGS

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
TICK = 0.05
HOLD_TIMEOUT = 1.0
GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
         ".webmanifest": "application/manifest+json", ".png": "image/png"}


def icon_png(size=180) -> bytes:
    """The home-screen icon: white "PUBLIC" on black, 1-bit, scaled by whole pixels."""
    from font import text_bits
    bits, w, h = text_bits("PUBLIC")
    k = max(1, (size * 3 // 5) // w)
    ox, oy = (size - w * k) // 2, (size - h * k) // 2
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            bx, by = (x - ox) // k, (y - oy) // k
            on = 0 <= bx < w and 0 <= by < h and bits[by][bx] and x >= ox and y >= oy
            row.append(255 if on else 0)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


class Hub:
    """THE PORT IS OPEN WHILE A PAGE SHOWS (user, 2026-11-03: buttons that look live and do
    nothing for a while are worse than NO LINK). A page on screen asks for the motors; they
    are opened on a thread, so nothing waits on it, and the page reads NO LINK until they
    answer. 3 s after the last page goes (closed, or hidden), the port is shut again."""
    RETRY = 2.0

    def __init__(self, driver: Driver, motors):
        self.d, self.m, self.p = driver, motors, driver.p
        self.clients = {}             # writer -> {"seen": t, "shown": bool}
        self._n = 0
        self._opening = None
        self._retry_at = 0.0

    def live(self) -> bool:
        if not hasattr(self.m, "open"):
            return getattr(self.m, "ok", True)          # the mock: always there
        return self.m.link is not None and self._opening is None and self.m.ok

    def snapshot(self):
        s = self.p.state()
        s["link"] = self.m.name if self.live() else "lost"
        return s

    def _bring_up(self):
        try:
            self.m.open()
            self.d.ensure_home()
        except Exception as e:
            print("motors:", e, flush=True)
            self.m.ok = False
            self.m.close()
            self._retry_at = time.monotonic() + self.RETRY
        finally:
            self._opening = None

    def _port(self, now):
        if not hasattr(self.m, "open"):
            return
        held = self.p.creep or self.p.bend is not None
        if any(c["shown"] for c in self.clients.values()) or held:
            self.m.touch()
            if self.m.link is None and self._opening is None and now >= self._retry_at:
                self._opening = threading.Thread(target=self._bring_up, daemon=True)
                self._opening.start()
        elif self._opening is None:
            self.m.idle()                              # the port goes back to the bench scripts

    async def broadcast(self):
        msg = _frame(json.dumps(self.snapshot()).encode())
        for w in list(self.clients):
            try:
                w.write(msg)
            except Exception:
                pass

    async def run(self):
        last = time.monotonic()
        prev = None
        while True:
            await asyncio.sleep(TICK)
            now = time.monotonic()
            for w, c in list(self.clients.items()):
                if self._holds(w) and now - c["seen"] > HOLD_TIMEOUT:
                    self.p.release(w)
            self.p.tick(now - last)
            last = now
            self._port(now)
            self._step()
            s = self.snapshot()
            if s != prev:
                prev = s
                await self.broadcast()

    def _step(self):
        if not self.live():
            return
        try:
            self.d.step(TICK)
            self.d.save()
        except Exception as e:                         # a motor that stops answering, a busy port
            print("motor:", e, flush=True)
            self.m.ok = False
            if hasattr(self.m, "open"):                # shut it; a page still showing reopens it
                self.m.close()
                self._retry_at = time.monotonic() + self.RETRY

    def _holds(self, w):
        return w in self.p.creep or (self.p.bend is not None and self.p.bend[0] is w)

    async def message(self, w, raw: bytes):
        self.clients[w]["seen"] = time.monotonic()
        try:
            m = json.loads(raw)
        except ValueError:
            return
        t, b = m.get("t"), m.get("b")
        if t == "down" and b in BUTTONS:
            self.p.press(w, b)
        elif t == "up" and b in BUTTONS:
            self.p.release(w, b)
        elif t == "hide":
            self.p.release(w)
            self.clients[w]["shown"] = False
        elif t == "show":
            self.clients[w]["shown"] = True
        self._step()                               # a press goes out now, not at the next tick
        await self.broadcast()


def _frame(payload: bytes, op=0x1) -> bytes:
    n = len(payload)
    if n < 126:
        head = bytes([0x80 | op, n])
    elif n < 65536:
        head = bytes([0x80 | op, 126]) + struct.pack(">H", n)
    else:
        head = bytes([0x80 | op, 127]) + struct.pack(">Q", n)
    return head + payload


async def _ws(hub: Hub, r: asyncio.StreamReader, w: asyncio.StreamWriter, key: str):
    acc = base64.b64encode(hashlib.sha1(key.encode() + GUID).digest()).decode()
    w.write(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
             "Sec-WebSocket-Accept: %s\r\n\r\n" % acc).encode())
    hub.clients[w] = {"seen": time.monotonic(), "shown": True}   # the page says if it is hidden
    w.write(_frame(json.dumps(hub.snapshot()).encode()))
    buf = b""
    try:
        while True:
            h = await r.readexactly(2)
            op, n = h[0] & 0x0F, h[1] & 0x7F
            if n == 126:
                n = struct.unpack(">H", await r.readexactly(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", await r.readexactly(8))[0]
            mask = await r.readexactly(4) if h[1] & 0x80 else b"\0\0\0\0"
            data = bytes(c ^ mask[i % 4] for i, c in enumerate(await r.readexactly(n)))
            if op == 0x8:
                w.write(_frame(data[:2], 0x8))
                break
            if op == 0x9:
                w.write(_frame(data, 0xA))
                continue
            if op in (0x1, 0x0):
                buf += data
                if h[0] & 0x80:
                    await hub.message(w, buf)
                    buf = b""
    except (asyncio.IncompleteReadError, ConnectionError):
        pass
    finally:
        hub.clients.pop(w, None)
        hub.p.release(w)                       # whatever this phone held goes with it
        hub._step()
        await hub.broadcast()
        w.close()


async def handle(hub: Hub, r: asyncio.StreamReader, w: asyncio.StreamWriter):
    try:
        head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
    except (asyncio.IncompleteReadError, asyncio.TimeoutError, asyncio.LimitOverrunError, ConnectionError):
        w.close()
        return
    lines = head.decode("latin-1").split("\r\n")
    try:
        method, path, _ = lines[0].split(" ", 2)
    except ValueError:
        w.close()
        return
    hdr = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:] if l)}
    path = path.split("?", 1)[0]
    if path == "/ws" and hdr.get("upgrade", "").lower() == "websocket":
        await _ws(hub, r, w, hdr.get("sec-websocket-key", ""))
        return
    if path == "/":
        path = "/index.html"
    if path == "/icon.png":
        body, ctype = ICON, "image/png"
    elif path == "/ca.crt" and CA_CRT and os.path.isfile(CA_CRT):
        body, ctype = open(CA_CRT, "rb").read(), "application/x-x509-ca-cert"
    elif path == "/font.js":
        from font import js
        body, ctype = js().encode(), TYPES[".js"]
    else:
        f = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not f.startswith(STATIC) or not os.path.isfile(f):
            w.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            await w.drain()
            w.close()
            return
        body = open(f, "rb").read()
        ctype = TYPES.get(os.path.splitext(f)[1], "application/octet-stream")
    w.write(("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nCache-Control: no-cache\r\n"
             "Connection: close\r\n\r\n" % (ctype, len(body))).encode() + (body if method != "HEAD" else b""))
    await w.drain()
    w.close()


ICON = b""
CA_CRT = None


async def main(argv=None):
    global ICON, CA_CRT
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mock", action="store_true", help="pretend motors")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--strings", default=",".join(map(str, STRINGS)),
                    help="which strings have a motor on the bus, e.g. 1 for one motor on the bench")
    ap.add_argument("--raise-sign", type=int, choices=(1, -1), default=None,
                    help="the motor direction that raises pitch (pitchctl.RAISE_SIGN)")
    ap.add_argument("--state", default="/var/lib/public-steel-guitar-phone/state.json",
                    help="where each motor's open-pitch count is kept across restarts")
    ap.add_argument("--tls-port", type=int, default=443)
    ap.add_argument("--tls-dir", default=None,
                    help="server.crt, server.key and ca.crt (install.sh makes them): HTTPS on "
                         "--tls-port as well as HTTP, and the CA at /ca.crt for the phone")
    a = ap.parse_args(argv)
    strings = [int(s) for s in a.strings.split(",") if s]
    motors = MockMotors(strings) if a.mock else __import__("pitchctl").MotorCtrlMotors(strings)
    state = a.state if not a.mock else None
    if state:
        os.makedirs(os.path.dirname(state), exist_ok=True)
    kw = {} if a.raise_sign is None else {"raise_sign": a.raise_sign}
    drv = Driver(motors, Pitch(), state, **kw)
    hub = Hub(drv, motors)
    ICON = icon_png()
    servers = [await asyncio.start_server(lambda r, w: handle(hub, r, w), a.host, a.port)]
    print("phone page on %s:%d, motors: %s, strings %s" % (a.host, a.port, motors.name, strings), flush=True)
    if a.tls_dir:
        import ssl
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(os.path.join(a.tls_dir, "server.crt"), os.path.join(a.tls_dir, "server.key"))
        CA_CRT = os.path.join(a.tls_dir, "ca.crt")
        servers.append(await asyncio.start_server(lambda r, w: handle(hub, r, w), a.host, a.tls_port, ssl=ctx))
        print("and https on %s:%d" % (a.host, a.tls_port), flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers), hub.run())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
