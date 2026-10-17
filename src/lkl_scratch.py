"""JUST the LKL knee housing at its station -- a one-part scratch scope for fast housing
iteration. It does NOT import src.build: that import alone is ~160 s (chassis builds at
import time), against ~15 s for the housing. The station is copied from
build.LEVER_STATIONS["lkl"] -- a scratch aid only, never used by the build."""
from . import knee_lever as KL

LKL_X, LKL_Y = -497.790, -67.950        # build.LEVER_STATIONS lkl (2026-10-16)


def components():
    return [("knee_housing", KL._housing().translate((LKL_X, LKL_Y, KL.MOUNT_Z)))]
