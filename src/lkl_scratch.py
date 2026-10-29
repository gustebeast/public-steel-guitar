"""JUST the LKL knee housing and its axle stack at its station -- a scratch scope for fast
housing iteration. It does NOT import src.build: that import alone is ~160 s (chassis builds
at import time), against ~15 s for the housing. The station is copied from
build.LEVER_STATIONS["lkl"] -- a scratch aid only, never used by the build."""
from . import knee_lever as KL

LKL_X, LKL_Y = -497.790, -67.950        # build.LEVER_STATIONS lkl (2026-10-16)
_STACK = ("bearing", "spacer", "preload_spring", "axle_washer", "axle_screw")


def components():
    at = (LKL_X, LKL_Y, KL.MOUNT_Z)
    out = [("knee_housing", KL._housing()), ("knee_lever", KL.knee_lever), ("kl_axle_sprung", KL.kl_axle_sprung)]
    out += [(n, s) for n, s in KL.demo_parts() if any(k in n for k in _STACK)]
    return [(n, s.translate(at)) for n, s in out]
