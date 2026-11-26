"""memgate judges each (kind, stage) on its own peaks (2026-11-25: one 9.81 GB close_ab_ck.sh
peak made an ownroute.py --post that used 0.93 GB wait 4 h 37 min).  py -3.12 test_memgate_stage.py"""
import json
import os
import sys
import tempfile

os.environ["MEMGATE_STATE"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memgate as m  # noqa: E402

PY = "C:/Program Files/KiCad/10.0/bin/python.exe"
assert m.stage_of([PY, "ownroute.py", r"C:\x\output_board", "--post"]) == "ownroute.py --post"
assert m.stage_of([PY, "finish.py", "--keep-route", "b"]) == "finish.py --keep-route"
# stored records keep only a joined, possibly clipped string
assert m.stage_of("bash C:/a b/mV/close_ab_ck.sh mVW48ws1 fC_ws1") == "close_ab_ck.sh"
assert m.stage_of(r"py C:\cadkit\pcbflow\finish.py elec/out/x") == "finish.py"

recs = [{"name": "finish", "rc": 0, "cap_hit": False, "peak_ram_gb": 9.81,
         "cmd": "bash /s/mV/close_ab_ck.sh a b PCBFLOW_POWER_GATE=1"},      # old, no 'stage'
        {"name": "finish", "stage": "ownroute.py --post", "rc": 0, "cap_hit": False,
         "peak_ram_gb": 0.93, "cmd": "x"},
        {"name": "finish", "stage": "finish.py --keep-route", "rc": 1, "cap_hit": False,
         "peak_ram_gb": 2.93, "cmd": "x"},                                  # failed: not a need
        {"name": "build", "rc": 0, "cap_hit": False, "peak_ram_gb": 5.3, "cmd": "agent_sync.py build"}]
json.dump(recs, open(os.path.join(os.environ["MEMGATE_STATE"], "peaks.json"), "w"))

assert m.need_for("finish", "ownroute.py --post") == 1.07
assert m.need_for("finish", "close_ab_ck.sh") == 11.28
assert m.need_for("finish", "finish.py --keep-route") == 11.28   # unseen stage: the kind's max
assert m.need_for("nosuch", "x.py") == m.DEFAULT_NEED_GB
assert m.need_for("finish") == 11.28                          # whole kind, as before
# day margin = what one build needs, no 6 GB floor once a build is recorded
m.time.localtime = lambda *a: type("T", (), {"tm_hour": 12})()
assert m.default_margin() == 6.1
recs[-1]["peak_ram_gb"] = 3.0
json.dump(recs, open(os.path.join(os.environ["MEMGATE_STATE"], "peaks.json"), "w"))
assert m.default_margin() == 3.4
msg = m.why_waiting("finish", "ownroute.py --post", 1.07, 3.4, 2.0, False)
assert "0 jobs running" in msg and "short 2.5 GB" in msg and "ownroute.py --post" in msg, msg
print("ok")
