"""Motor quality, unloaded: step response at pedal travel, and repeatability against angle.
1 cent at string 1 (E4 model, DL_OPEN 4 mm, 2 mm lead, 16384 counts per turn): 38 counts."""
import json, serial, statistics as st, time
from .link import find_motor_port
from . import servo
T = servo.COUNTS_PER_TURN
CENT = 38
s = serial.Serial(find_motor_port(), 115200, timeout=0, write_timeout=1)
s.reset_input_buffer()
buf = b""
def lines():
    global buf
    buf += s.read(4096)
    *ls, buf = buf.split(b"\n")
    return [l.decode("ascii", "replace").split() for l in ls]
def send(body):
    d = servo.pack(1, body)
    s.write(b"S 0 1 %s\n" % d.hex().encode())
def pos_of(p):
    d = bytes.fromhex(p[4])
    return int.from_bytes(d[1:7], "big", signed=True)
def read_pos(n=1):
    out = []
    for _ in range(n):
        send(b"\x31")
        end = time.time() + 0.2
        while time.time() < end:
            got = [pos_of(p) for p in lines() if len(p) > 4 and p[0] == "R" and p[4].upper().startswith("31")]
            if got:
                out.append(got[0]); break
    return out
def wait_arrive(limit=2.0):
    end = time.time() + limit
    while time.time() < end:
        for p in lines():
            if len(p) > 4 and p[0] == "R" and p[4].upper().startswith(("F502", "F402")):
                return True
    return False
def move_abs(c, rpm, acc):
    send(servo.move(servo.MOVE_ABS, c, rpm, acc))

send(bytes([servo.ENABLE, 1])); time.sleep(.3); lines()
home = read_pos(3)[-1]
print("home", home, flush=True)
send(servo.move(servo.MOVE_ABS, home, 300, 200)); wait_arrive(); time.sleep(.3)

# 1. standing still, driven
hold = []
for _ in range(600):
    hold += read_pos(1)
print("hold: n %d sd %.2f range %d counts" % (len(hold), st.pstdev(hold), max(hold) - min(hold)), flush=True)

# 2. step response, encoder polled as fast as the bus goes
res = []
for turns in (0.25, 0.52, 0.76, 1.0):
    for rpm, acc in ((1000, 200), (3000, 200), (3000, 240), (3000, 255), (3000, 0)):
        rows = []
        for sign in (1, -1, 1, -1):
            a = home if sign > 0 else home + int(turns * T)
            b = home + int(turns * T) if sign > 0 else home
            lines()
            move_abs(b, rpm, acc)
            t0 = None; tr = []; t_arr = None; last = 0; end = time.time() + 1.2
            while time.time() < end:
                now = time.time()
                if now - last > 0.002:
                    send(b"\x31"); last = now
                for p in lines():
                    if p[0] == "X" and t0 is None: t0 = int(p[3])
                    if len(p) > 4 and p[0] == "R":
                        u = p[4].upper()
                        if u.startswith("31"): tr.append((int(p[2]), pos_of(p)))
                        if u.startswith(("F502", "F402")) and t_arr is None: t_arr = int(p[2])
                time.sleep(0.0002)
            t = [(x - t0) / 1000 for x, _ in tr]
            q = [(v - b) * sign for _, v in tr]
            span = abs(b - a)
            i50 = next((i for i, v in enumerate(q) if v > -span / 2), None)
            i90 = next((i for i, v in enumerate(q) if v > -span * .1), None)
            cent = None
            for i in range(len(q) - 1, -1, -1):
                if abs(q[i]) > CENT: cent = t[i + 1] if i + 1 < len(t) else None; break
            rows.append(dict(t50=t[i50] if i50 is not None else None, t90=t[i90] if i90 is not None else None,
                             t1c=cent, over=max(q), arr=(t_arr - t0) / 1000 if t_arr else None, n=len(q)))
        res.append(dict(turns=turns, rpm=rpm, acc=acc, rows=rows))
        m = lambda k: round(st.mean(r[k] for r in rows if r[k] is not None), 1) if any(r[k] is not None for r in rows) else None
        print("%.2f turn %4d rpm acc %3d: t50 %s t90 %s within1c %s arrived %s overshoot %s polls %d" %
              (turns, rpm, acc, m("t50"), m("t90"), m("t1c"), m("arr"), m("over"), rows[0]["n"]), flush=True)

# 3. repeatability against angle, from both sides
angles = [home + k * T // 12 for k in range(12)]
rec = {i: {"up": [], "dn": []} for i in range(12)}
offset = T // 8
for cycle in range(10):
    for i, a in enumerate(angles):
        for side, start in (("up", a - offset), ("dn", a + offset)):
            move_abs(start, 2000, 240); wait_arrive(1)
            lines()
            move_abs(a, 2000, 240); wait_arrive(1); time.sleep(.15); lines()
            rec[i][side].append(st.mean(read_pos(4)) - a)
    print("cycle", cycle, flush=True)
json.dump(dict(rec=rec, step=res, hold=hold), open("/tmp/mq.json", "w"))
allr = []
print("angle  mean_up  sd_up   mean_dn  sd_dn   up-dn")
for i in range(12):
    u, d = rec[i]["up"], rec[i]["dn"]
    print("%3d  %7.1f %6.2f  %7.1f %6.2f  %6.1f" % (i * 30, st.mean(u), st.stdev(u), st.mean(d), st.stdev(d), st.mean(u) - st.mean(d)))
    allr += [x - st.mean(u) for x in u] + [x - st.mean(d) for x in d]
print("random: sd %.2f, worst %.1f counts over %d arrivals" % (st.pstdev(allr), max(abs(x) for x in allr), len(allr)))
move_abs(home, 300, 200); wait_arrive(); send(bytes([servo.ENABLE, 0])); time.sleep(.2)
print("end", read_pos(1))
s.close()
