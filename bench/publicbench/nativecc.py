"""The one place the bench finds a C compiler for the host, so the firmware-logic tests (levers,
lever ISP, play, arms, frames, the QT Py bench and its gates) run on any machine, not only where
gcc happens to be installed.

In order:
  1. $NATIVE_CC, split like a shell command, e.g. "clang" or "python3 -m ziglang cc"
  2. gcc, then cc, on the PATH (the Pi, Linux, macOS)
  3. Zig's bundled clang from the `ziglang` pip package (`pip install ziglang`): a complete C
     toolchain with no system install, which is what makes these tests run on Windows.

build() compiles one shared library or executable. Zig's first compile on a machine fills its
cache and has been seen to fail once on a cache race ("manifest_create Unexpected", 2026-11-24),
so a failed build is retried once.
"""
from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import subprocess
import sys

_CC: list[str] | None | bool = False      # False: not looked for yet


def compiler() -> list[str] | None:
    """The compiler as an argv prefix, or None when there is none."""
    global _CC
    if _CC is not False:
        return _CC
    env = os.environ.get("NATIVE_CC")
    if env:
        _CC = shlex.split(env, posix=os.name != "nt")
    elif shutil.which("gcc") or shutil.which("cc"):
        _CC = [shutil.which("gcc") or shutil.which("cc")]
    elif importlib.util.find_spec("ziglang") is not None:
        _CC = [sys.executable, "-m", "ziglang", "cc"]
        if sys.platform == "win32":
            _CC += ["-target", "x86_64-windows-gnu"]   # the MinGW ABI: ctypes loads it as is
    else:
        _CC = None
    return _CC


def exe_name(path: str) -> str:
    """An executable's file name on this system."""
    return path + ".exe" if sys.platform == "win32" and not path.endswith(".exe") else path


def build(args: list[str], out: str) -> None:
    """Run the compiler with `args` and `-o out`, retrying once (see the module docstring)."""
    cc = compiler()
    if not cc:
        raise RuntimeError("no native C compiler (set NATIVE_CC, install gcc, or pip install ziglang)")
    cmd = cc + list(args) + ["-o", out]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        subprocess.run(cmd, check=True)


def build_shared(srcs: list[str], out: str, include: str, werror: bool = True) -> None:
    """A shared library of `srcs`, written to `out` atomically (out + .tmp, then renamed)."""
    flags = ["-O2", "-Wall", "-Wextra"] + (["-Werror"] if werror else []) + ["-shared", "-fPIC",
                                                                         "-I", include]
    build(flags + list(srcs), out + ".tmp")
    os.replace(out + ".tmp", out)
