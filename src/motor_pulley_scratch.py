# -*- coding: utf-8 -*-
"""SCRATCH, NOT A PART: one SERVO42D with its cut D shaft and the motor pulley seated on it, and
the LOW screw pulley beside it, for the tab (user, 2026-10-28)."""
from __future__ import annotations

from . import components as C


def components():
    out = [("motor" + ("_" + k if k else ""), wp) for k, wp, _, _ in C.motor_parts()]
    return out + [("motor_pulley", C.motor_pulley()),
                  ("screw_pulley_lo", C.screw_pulley().translate((30, 0, 0)))]
