# -*- coding: utf-8 -*-
"""cadkit.kept — geometry built once per CHANGE, by whoever builds it first, and read
by everyone after that.

    from cadkit.kept import kept, keep

    belt = kept(C.belt, motor_xyz, screw_xyz, upper, p, x0, x1, end_a, end_b, tooth)

    @keep
    def _build():                        # bridge_endplate = _build()
        ...

`kept(make, *args)` is `make(*args)`: computed the first time, read from a file every time
after that, until something it is made from changes. `@keep` is the same for every call
of a function.

ONE STORE PER MACHINE, NOT PER WORKTREE. Results live in ~/.cadkit/kept (CADKIT_KEPT_DIR
moves it), named by a hash of what they are made from. So the lead's build, an agent's
scratch view and another agent's gate all fill the same store as they work, and each
reads what any of them already computed FROM THE SAME INPUTS. Nobody publishes anything:
a part nobody has changed is never computed twice, and a change is paid for once, by
whoever meets it first. Two worktrees whose sources differ simply get different names.

WHAT THE NAME IS MADE FROM -- what the function can actually read, BY VALUE:

  * its own code (bytecode, constants, nested functions and lambdas), its defaults and
    the cells it closes over;
  * every global it names, and every `module.attribute` it reads -- the VALUE that is
    there now: a number by its exact repr, a list by its items, a function by this same
    rule (so a helper's helper's dimension counts), a module it uses whole by the source
    of the module and of every project module that one imports;
  * project modules it imports by name inside itself (`import`, `importlib.import_module
    ("src.x")`, `__import__`), by their source and by the data files they read as they
    imported (cadkit.IMPORT_READS);
  * the arguments, by the same rule;
  * an object of a project class by its attributes (not a `*cache*`/`*memo*` one), or by its
    own `__kept_key__()` when it has one;
  * GEOMETRY by WHAT IT IS: a result of another kept call carries the hash of its stored
    BREP (computed once, when it is written), so a kept chassis passed into a kept cut costs
    nothing to name -- and an upstream result that is RECOMPUTED BUT COMES OUT IDENTICAL keeps
    its name, so nothing made from it is computed again (EARLY CUTOFF: a chassis change that
    leaves the anchor as it was stops at the anchor). Any other solid is named by a hash of
    its BREP the same way. (Results written before this carry their call's key instead.);
  * an environment variable it names in a string ("PI_NO_CRADLE"), by its value;
  * project data files the function OPENED while it was computed (a board's JSON...):
    recorded with the result, and a result whose files have changed since is computed
    again;
  * the versions of cadquery and its kernel.

So changing a dimension invalidates exactly the results whose code reads it -- through
any number of calls -- and nothing else. What the name cannot see: the
environment read under a name the code does not spell, the clock, randomness, and state reached in ways the code does not spell (a global
CHANGED IN PLACE by a function this one calls, `getattr(module, computed_name)` on a
module it does not otherwise name). A function that depends on those must not be kept.
A value the name cannot be made from at all (an open file, a socket...) is not kept:
the function is simply called, and `tally()` says so.

WHAT A RESULT MAY BE: a cq.Workplane (any number of shapes, its plane kept), a cq.Shape,
plain data (numbers, strings, None, bools), and tuples, lists and dicts of those, to any
depth. The first build computes it, writes it, and hands back the result READ FROM THAT
FILE -- the very one every later build gets -- so a build that computed and a build that
read give the same model, to the byte.

CADKIT_KEPT=0 computes everything. CADKIT_KEPT_MAX_GB (default 20) caps the store; the
least recently used results go first.
"""

from __future__ import annotations

import ast
import dis
import functools
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import threading
import time
import types
import weakref

import cadquery as cq

__all__ = ["kept", "keep", "tally", "store", "fingerprint"]

_PLAIN = (int, float, str, bool, type(None), bytes, complex)
_TALLY = {"read": 0, "drawn": 0, "plain": 0, "read_s": 0.0, "drawn_s": 0.0}
_WHY_PLAIN = {}                                 # qualname -> why it was not kept
_SRC = {}                                       # module name -> closure digest | None
_FN = {}                                        # id(code obj) -> (code obj, digest)
_SHAPE_H = weakref.WeakKeyDictionary()          # cq.Shape -> BREP digest
_ATTR = "_cadkit_kept"                          # provenance tag on returned geometry
_EXT = {".py", ".pyc", ".pyd", ".dll", ".so"}
_LOCAL = threading.local()


_ENV_NAME = __import__("re").compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9_]+$")


class _Unkeyable(Exception):
    pass


# ── where ────────────────────────────────────────────────────────────────────────────
def store() -> pathlib.Path:
    d = os.environ.get("CADKIT_KEPT_DIR")
    return pathlib.Path(d) if d else pathlib.Path.home() / ".cadkit" / "kept"


@functools.lru_cache(maxsize=None)
def _project_root():
    """The project this cadkit is vendored into (its parent), or cadkit's own repo."""
    pkg = pathlib.Path(__file__).resolve().parent
    return pkg if (pkg / ".git").exists() else pkg.parent


@functools.lru_cache(maxsize=4096)
def _in_project(f) -> bool:
    """A real file under the project (not "<string>", which resolves against the cwd)."""
    if not f or str(f).startswith("<") or not os.path.isabs(str(f)):
        return False
    try:
        pathlib.Path(f).resolve().relative_to(_project_root())
    except ValueError:
        return False
    return "site-packages" not in str(f)


# ── module source closures (for a module used WHOLE) ───────────────────────────────
def _imports(name: str, file: pathlib.Path):
    """Names of the modules `file` imports, anywhere in it (inside functions too)."""
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return
    package = name if file.name == "__init__.py" else name.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom):
            try:
                base = importlib.util.resolve_name("." * node.level + (node.module or ""),
                                                   package) if node.level else node.module
            except (ImportError, ValueError):
                continue
            if not base:
                continue
            yield base
            for a in node.names:                      # `from . import dimensions`
                yield base + "." + a.name


def _file(name: str):
    mod = sys.modules.get(name)
    f = getattr(mod, "__file__", None)
    if f is None and mod is None:
        try:
            spec = importlib.util.find_spec(name)
        except (ImportError, ValueError, AttributeError):
            spec = None
        f = spec.origin if spec is not None and spec.has_location else None
    return pathlib.Path(f) if f and str(f).endswith(".py") else None


def _closure(name: str):
    """sha1 over the source of module `name` and of every project module it reaches;
    None if `name` is not a project module."""
    if name in _SRC:
        return _SRC[name]
    start = _file(name)
    if start is None or not _in_project(start):
        _SRC[name] = None
        return None
    seen, todo = {}, [name]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        f = _file(n)
        if f is None or not _in_project(f):
            continue
        seen[n] = f
        todo.extend(_imports(n, f))
    h = hashlib.sha1()
    for n in sorted(seen):
        h.update(n.encode())
        h.update(seen[n].read_bytes().replace(b"\r\n", b"\n"))
    # ...and the data files those modules read while they imported (cadkit.IMPORT_READS)
    from . import IMPORT_READS
    for path in sorted({p for m, p in IMPORT_READS if m in seen}):
        if _in_project(path) and os.path.isfile(path):
            h.update(path.encode())
            with open(path, "rb") as fh:
                h.update(hashlib.sha1(fh.read()).digest())
    _SRC[name] = h.hexdigest()
    return _SRC[name]


# ── naming values ──────────────────────────────────────────────────────────────────
def _brep_bytes(shape) -> bytes:
    """The shape's BREP WITHOUT triangulation: a mesh is cached on a shape by whatever meshed
    it last (a bounding box, a view), so with it the same solid writes different bytes."""
    from OCP.BRepTools import BRepTools
    from OCP.TopTools import TopTools_FormatVersion
    buf = io.BytesIO()
    BRepTools.Write_s(shape.wrapped, buf, False, False, TopTools_FormatVersion.TopTools_FormatVersion_VERSION_1)
    return buf.getvalue()


_NUM = __import__("re").compile(rb"-?\d+\.\d*(?:[eE][-+]?\d+)?|-?\d+[eE][-+]?\d+")


def _q(m):
    v = round(float(m.group(0)), 9)
    return (b"%.9g" % (0.0 if v == 0 else v))


def _quantised(brep: bytes) -> bytes:
    """A BREP's text with every real rounded to 1e-9: the same solid built in another process
    comes out with last-bit noise (1.3e-17 for 0, 0.049999999999999989 for 0.05), so its exact
    bytes would name it differently every run."""
    return _NUM.sub(_q, brep)


def _shape_token(s: cq.Shape) -> str:
    tag = getattr(s, _ATTR, None)
    if tag:
        return "kept:" + tag
    h = _SHAPE_H.get(s)
    if h is None:
        h = _SHAPE_H[s] = hashlib.sha1(_quantised(_brep_bytes(s))).hexdigest()
    return "brep:" + h


def _plane_token(p: cq.Plane) -> str:
    return "plane:%r" % ((p.origin.toTuple(), p.xDir.toTuple(), p.zDir.toTuple()),)


class _Namer:
    """Turns a value into a stable string, by the rules in the module docstring."""

    def __init__(self, log=None):
        self.log = log                  # CADKIT_KEPT_DEBUG: every ingredient, for a diff
        self.stack = set()
        self.memo = {}                  # id -> token, for functions, classes and objects

    def _memo(self, x, make):
        hit = self.memo.get(id(x))
        if hit is not None and hit[0] is x:
            return hit[1]
        tok = make(x)
        if not tok.startswith(("fn-rec:", "cls-rec:")):
            self.memo[id(x)] = (x, tok)
        return tok

    def val(self, x) -> str:
        if isinstance(x, _PLAIN):
            return "%s:%r" % (type(x).__name__, x)
        if isinstance(x, (tuple, list)):
            return "%s[%s]" % (type(x).__name__, ",".join(self.val(v) for v in x))
        if isinstance(x, (set, frozenset)):
            return "set{%s}" % ",".join(sorted(self.val(v) for v in x))
        if isinstance(x, dict):
            return "dict{%s}" % ",".join(sorted("%s=%s" % (self.val(k), self.val(v))
                                                for k, v in x.items()))
        if isinstance(x, types.ModuleType):
            return self.module(x)
        lazy = self._lazy(x)
        if lazy is not None:
            return lazy
        if isinstance(x, cq.Workplane):
            tag = getattr(x, _ATTR, None)
            if tag:
                return "kept:" + tag
            return "wp(%s;%s)" % (_plane_token(x.plane), ",".join(self.val(o) for o in x.objects))
        if isinstance(x, cq.Shape):
            return _shape_token(x)
        if isinstance(x, (cq.Vector, cq.Location, cq.Plane)):
            if isinstance(x, cq.Vector):
                return "vec%r" % (x.toTuple(),)
            if isinstance(x, cq.Plane):
                return _plane_token(x)
            return "loc%r" % (x.toTuple(),)
        if isinstance(x, functools.partial):
            return "partial(%s;%s;%s)" % (self.val(x.func), self.val(x.args), self.val(x.keywords))
        if isinstance(x, types.MethodType):
            return "method(%s;%s)" % (self.val(x.__func__), self.val(x.__self__))
        if isinstance(x, types.FunctionType):
            return self._memo(x, self.function)
        if isinstance(x, (types.BuiltinFunctionType, types.BuiltinMethodType)):
            return "builtin:%s.%s" % (getattr(x, "__module__", None) or "", x.__qualname__)
        if isinstance(x, type):
            return self._memo(x, self.klass)
        if isinstance(x, functools._lru_cache_wrapper):
            return self.val(x.__wrapped__)
        if callable(x) and hasattr(x, "__wrapped__"):
            return "wrapped(%s)" % self.val(x.__wrapped__)
        cls_mod = getattr(type(x), "__module__", "") or ""
        if cls_mod.split(".")[0] in ("numpy", "math"):
            if hasattr(x, "tobytes") and hasattr(x, "dtype"):          # an array
                return "nd(%s;%r;%s)" % (x.dtype, getattr(x, "shape", ()),
                                         hashlib.sha1(x.tobytes()).hexdigest())
            if callable(x) and hasattr(x, "__name__"):                  # a ufunc
                return "npfn:" + x.__name__
            if hasattr(x, "item"):                                      # a numpy scalar
                return "np:%r" % (x.item(),)
        import enum
        if isinstance(x, enum.Enum):
            return "enum:%s.%s" % (self.klass(type(x)), x.name)
        cls = type(x)
        own = getattr(cls, "__kept_key__", None)
        if own is not None:                  # the object says what it is (cadkit.board_geom.Boards)
            return "own(%s;%s)" % (self.klass(cls), x.__kept_key__())
        mod = sys.modules.get(cls.__module__)
        if mod is not None and _in_project(getattr(mod, "__file__", None)) and hasattr(x, "__dict__"):
            if id(x) in self.stack:
                return "cycle"
            self.stack.add(id(x))
            try:
                # a memo is not state: what is in it depends on what asked first
                st = {k: v for k, v in vars(x).items()
                      if "cache" not in k.lower() and "memo" not in k.lower()}
                return "obj(%s;%s)" % (self.klass(cls), self.val(st))
            finally:
                self.stack.discard(id(x))
        raise _Unkeyable("%s value" % cls.__qualname__)

    def _lazy(self, x):
        try:
            cls = object.__getattribute__(x, "__class__")
        except Exception:
            return None
        if cls.__name__ != "_Lazy" or not cls.__module__.endswith("lazy"):
            return None
        value = object.__getattribute__(x, "_lazy_value")
        if value is not None:
            return self.val(value)
        return "lazy(%s)" % self.val(object.__getattribute__(x, "_lazy_build"))

    def module(self, m) -> str:
        c = _closure(m.__name__)
        return "mod:%s:%s" % (m.__name__, c) if c else "lib:" + m.__name__

    def klass(self, c: type) -> str:
        mod = sys.modules.get(c.__module__)
        if mod is None or not _in_project(getattr(mod, "__file__", None)):
            return "libcls:%s.%s" % (c.__module__, c.__qualname__)
        if id(c) in self.stack:
            return "cls-rec:" + c.__qualname__
        self.stack.add(id(c))
        try:
            parts = []
            for k, v in sorted(vars(c).items()):
                if k in ("__dict__", "__weakref__", "__doc__", "__module__"):
                    continue
                try:
                    parts.append("%s=%s" % (k, self.val(v)))
                except _Unkeyable:
                    parts.append("%s=?" % k)
            bases = ",".join(self.klass(b) for b in c.__bases__)
            return "cls:%s(%s){%s}" % (c.__qualname__, bases, ";".join(parts))
        finally:
            self.stack.discard(id(c))

    def function(self, f: types.FunctionType) -> str:
        mod = sys.modules.get(f.__module__)
        if not _in_project(f.__code__.co_filename):
            return "libfn:%s.%s" % (f.__module__, f.__qualname__)
        if id(f) in self.stack:
            return "fn-rec:" + f.__qualname__
        self.stack.add(id(f))
        try:
            h = _Log(self.log, f.__qualname__)
            h.update(_code_digest(f.__code__).encode())
            h.update(self.val(f.__defaults__ or ()).encode())
            h.update(self.val(f.__kwdefaults__ or {}).encode())
            for cell in f.__closure__ or ():
                try:
                    h.update(self.val(cell.cell_contents).encode())
                except ValueError:                     # an empty cell
                    h.update(b"empty")
            g = f.__globals__
            builtins = g.get("__builtins__", {})
            for kind, name, attr in _reads(f.__code__):
                if kind == "import":
                    c = _closure(name)
                    h.update(("imp:%s:%s" % (name, c)).encode())
                    continue
                if kind == "env":
                    h.update(("env:%s=%r" % (name, os.environ.get(name))).encode())
                    continue
                if name in g:
                    v = g[name]
                elif (name in builtins if isinstance(builtins, dict) else hasattr(builtins, name)):
                    continue
                else:
                    h.update(("missing:" + name).encode())
                    continue
                if attr is not None and isinstance(v, types.ModuleType):
                    if hasattr(v, attr):
                        h.update(("%s.%s=%s" % (name, attr, self.val(getattr(v, attr)))).encode())
                    else:
                        # a submodule not imported yet, or a typo: by source
                        h.update(("%s.%s?%s" % (name, attr, self.module(v))).encode())
                    continue
                h.update(("%s=%s" % (name, self.val(v))).encode())
            return "fn:%s:%s" % (f.__qualname__, h.hexdigest())
        finally:
            self.stack.discard(id(f))


class _Log:
    """A sha1 that also writes what it is fed to a list, when there is one."""

    def __init__(self, log, who):
        self.h, self.log, self.who = hashlib.sha1(), log, who

    def update(self, b):
        self.h.update(b)
        if self.log is not None:
            self.log.append("%s\t%s" % (self.who, b.decode(errors="replace")[:4000]))

    def hexdigest(self):
        return self.h.hexdigest()


def _const_repr(c) -> str:
    """repr, but a frozenset's in sorted order (its own order follows the hash seed)."""
    if isinstance(c, frozenset):
        return "frozenset{%s}" % ",".join(sorted(_const_repr(v) for v in c))
    if isinstance(c, tuple):
        return "(%s)" % ",".join(_const_repr(v) for v in c)
    return repr(c)


def _code_digest(code) -> str:
    hit = _FN.get(id(code))
    if hit is not None and hit[0] is code:
        return hit[1]
    h = hashlib.sha1()
    h.update(code.co_code)
    h.update(repr(code.co_names).encode())
    h.update(repr((code.co_argcount, code.co_kwonlyargcount, code.co_flags)).encode())
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            h.update(_code_digest(c).encode())
        else:
            h.update(_const_repr(c).encode())
    _FN[id(code)] = (code, h.hexdigest())
    return _FN[id(code)][1]


def _reads(code):
    """(kind, name, attr) for every global this code (and its nested code) reads:
    ("global", name, attr-or-None) -- `name` itself, or `name.attr` when the global is
    only ever used for one attribute in that spot -- and ("import", module, None) for
    a module it imports or names in a string to import_module/__import__."""
    out = []
    instrs = list(dis.get_instructions(code))
    for i, ins in enumerate(instrs):
        op = ins.opname
        if op in ("LOAD_GLOBAL", "LOAD_NAME"):
            name = ins.argval
            nxt = instrs[i + 1] if i + 1 < len(instrs) else None
            if nxt is not None and nxt.opname in ("LOAD_ATTR", "LOAD_METHOD"):
                out.append(("global", name, nxt.argval))
                # the module itself may still be used whole elsewhere: those spots
                # show up as plain loads and are named whole
            else:
                out.append(("global", name, None))
        elif op == "IMPORT_NAME":
            out.append(("import", ins.argval, None))
        elif op == "LOAD_CONST" and isinstance(ins.argval, str):
            if _ENV_NAME.match(ins.argval):
                out.append(("env", ins.argval, None))       # os.environ.get("PI_NO_CRADLE")
            elif _looks_like_module(ins.argval):
                out.append(("import", ins.argval, None))
    for c in code.co_consts:
        if isinstance(c, types.CodeType):
            out.extend(_reads(c))
    seen, uniq = set(), []
    for r in out:
        if r not in seen:
            seen.add(r)
            uniq.append(r)
    return uniq


def _looks_like_module(s: str) -> bool:
    if not s or len(s) > 100 or " " in s or "/" in s or "\\" in s:
        return False
    head = s.split(".")[0]
    if not head.isidentifier():
        return False
    return head in sys.modules and _closure(s) is not None


def fingerprint(make, *args, **kw) -> str:
    """The name `kept(make, *args, **kw)` would be stored under (raises _Unkeyable)."""
    dbg = os.environ.get("CADKIT_KEPT_DEBUG")
    n = _Namer([] if dbg else None)
    import OCP
    blob = "|".join((n.val(make), n.val(args), n.val(kw),
                     getattr(cq, "__version__", "?"), getattr(OCP, "__version__", "?"), "v2"))
    key = hashlib.sha1(blob.encode()).hexdigest()
    if dbg:
        d = pathlib.Path(dbg)
        d.mkdir(parents=True, exist_ok=True)
        (d / ("%s.%s.txt" % (getattr(make, "__qualname__", "x"), key[:8]))).write_text(
            "\n".join(n.log + ["TOP\t" + blob[:4000]]), encoding="utf-8")
    return key


# ── what a function opens while it computes ────────────────────────────────────────
def _audit(event, args):
    rec = getattr(_LOCAL, "opened", None)
    if rec is None or event != "open":
        return
    path, mode = args[0], args[1] if len(args) > 1 else "r"
    if not isinstance(path, (str, os.PathLike)) or (isinstance(mode, str) and any(c in mode for c in "wax+")):
        return
    rec.add(os.fspath(path))


_HOOKED = False


def _hook():
    global _HOOKED
    if not _HOOKED:
        sys.addaudithook(_audit)
        _HOOKED = True


def _file_deps(paths):
    deps, st = {}, store().resolve()
    for p in paths:
        try:
            rp = pathlib.Path(p).resolve()
        except (OSError, ValueError):
            continue
        if rp.suffix.lower() in _EXT or not rp.is_file() or not _in_project(rp):
            continue
        try:
            rp.relative_to(st)
            continue
        except ValueError:
            pass
        try:
            deps[str(rp)] = hashlib.sha1(rp.read_bytes()).hexdigest()
        except OSError:
            pass
    return deps


def _deps_ok(deps) -> bool:
    for p, h in deps.items():
        try:
            if hashlib.sha1(pathlib.Path(p).read_bytes()).hexdigest() != h:
                return False
        except OSError:
            return False
    return True


# ── result <-> files ───────────────────────────────────────────────────────────────
def _pack(x, shapes):
    if isinstance(x, _PLAIN) and not isinstance(x, (bytes, complex)):
        return x
    if isinstance(x, tuple):
        return {"T": [_pack(v, shapes) for v in x]}
    if isinstance(x, list):
        return {"L": [_pack(v, shapes) for v in x]}
    if isinstance(x, dict):
        if not all(isinstance(k, str) for k in x):
            raise _Unkeyable("a dict result with non-string keys")
        return {"D": {k: _pack(v, shapes) for k, v in x.items()}}
    lazy = getattr(type(x), "__name__", "") == "_Lazy"
    if lazy:
        x = object.__getattribute__(x, "_lazy_get")()
    if isinstance(x, cq.Workplane):
        idx = []
        for o in x.objects:
            if not isinstance(o, cq.Shape):
                raise _Unkeyable("a Workplane holding a %s" % type(o).__name__)
            idx.append(len(shapes))
            shapes.append(o)
        p = x.plane
        return {"W": idx, "P": [p.origin.toTuple(), p.xDir.toTuple(), p.zDir.toTuple()]}
    if isinstance(x, cq.Shape):
        shapes.append(x)
        return {"S": len(shapes) - 1}
    raise _Unkeyable("a %s result" % type(x).__name__)


def _unpack(x, shapes, key, path="r"):
    if isinstance(x, dict):
        if "T" in x:
            return tuple(_unpack(v, shapes, key, "%s.%d" % (path, i)) for i, v in enumerate(x["T"]))
        if "L" in x:
            return [_unpack(v, shapes, key, "%s.%d" % (path, i)) for i, v in enumerate(x["L"])]
        if "D" in x:
            return {k: _unpack(v, shapes, key, path + "." + k) for k, v in x["D"].items()}
        if "W" in x:
            o, xd, zd = x["P"]
            w = cq.Workplane(cq.Plane(o, xd, zd))
            w.objects = [shapes[i] for i in x["W"]]
            setattr(w, _ATTR, key + ":" + path)
            return w
        if "S" in x:
            s = shapes[x["S"]]
            setattr(s, _ATTR, key + ":" + path)
            return s
    return x


def _write(key, result, deps, seconds):
    shapes = []
    skel = _pack(result, shapes)                       # raises _Unkeyable
    d = store() / key[:2]
    d.mkdir(parents=True, exist_ok=True)
    tmp = ".%d.%d.tmp" % (os.getpid(), threading.get_ident())
    brep = d / (key + ".brep")
    if shapes:
        comp = cq.Compound.makeCompound(shapes)
        t = brep.with_suffix(tmp)
        t.write_bytes(_brep_bytes(comp))
        os.replace(t, brep)
    # THE RESULT'S CONTENT NAME (early cutoff): its stored BREP, reals rounded as _shape_token
    # rounds them, so a recompute that comes out the same solid gets the same name
    content = hashlib.sha1(_quantised(_brep_bytes(comp))).hexdigest() if shapes else key
    meta = {"skel": skel, "n": len(shapes), "deps": deps, "s": round(seconds, 2),
            "t": time.time(), "c": content}
    t = (d / (key + ".json")).with_suffix(tmp)
    t.write_text(json.dumps(meta))
    os.replace(t, d / (key + ".json"))                 # the json last: it says "complete"


def _read(key):
    d = store() / key[:2]
    try:
        meta = json.loads((d / (key + ".json")).read_text())
    except (OSError, ValueError):
        return None
    if not _deps_ok(meta.get("deps", {})):
        return None
    shapes = []
    if meta["n"]:
        try:
            comp = cq.Shape.importBrep(io.BytesIO((d / (key + ".brep")).read_bytes()))
        except Exception:
            return None
        if meta["n"] == 1 and not isinstance(comp, cq.Compound):
            shapes = [comp]
        else:
            import OCP.TopoDS
            it = OCP.TopoDS.TopoDS_Iterator(comp.wrapped)
            while it.More():
                shapes.append(cq.Shape.cast(it.Value()))
                it.Next()
        if len(shapes) != meta["n"]:
            return None
    try:
        os.utime(d / (key + ".json"))                  # recently used: pruned last
    except OSError:
        pass
    return (_unpack(meta["skel"], shapes, "c" + meta.get("c", key)),)


def _prune():
    try:
        cap = float(os.environ.get("CADKIT_KEPT_MAX_GB", "20")) * 1e9
    except ValueError:
        return
    files = []
    total = 0
    for f in store().glob("*/*.json"):
        try:
            st = f.stat()
            b = f.with_suffix(".brep")
            size = st.st_size + (b.stat().st_size if b.exists() else 0)
        except OSError:
            continue
        files.append((st.st_mtime, f, size))
        total += size
    if total <= cap:
        return
    for _t, f, size in sorted(files):
        for g in (f, f.with_suffix(".brep")):
            try:
                g.unlink()
            except OSError:
                pass
        total -= size
        if total <= 0.8 * cap:
            break


# ── the API ────────────────────────────────────────────────────────────────────────
def kept(make, *args, **kw):
    """`make(*args, **kw)`, read from the store if it has been computed from exactly
    these inputs, computed and kept if not (see the module docstring)."""
    what = getattr(make, "__qualname__", repr(make))
    if os.environ.get("CADKIT_KEPT") == "0":
        _TALLY["plain"] += 1
        return make(*args, **kw)
    t0 = time.perf_counter()
    try:
        key = fingerprint(make, *args, **kw)
    except (_Unkeyable, RecursionError) as exc:
        _TALLY["plain"] += 1
        _WHY_PLAIN[what] = str(exc)
        return make(*args, **kw)
    hit = _read(key)
    if hit is not None:
        _TALLY["read"] += 1
        _TALLY["read_s"] += time.perf_counter() - t0
        return hit[0]
    _hook()
    outer = getattr(_LOCAL, "opened", None)
    _LOCAL.opened = set()
    try:
        result = make(*args, **kw)
        opened = _LOCAL.opened
    finally:
        _LOCAL.opened = outer
    if outer is not None:
        outer.update(opened)                          # an enclosing kept call read them too
    seconds = time.perf_counter() - t0
    try:
        _write(key, result, _file_deps(opened), seconds)
    except _Unkeyable as exc:
        _TALLY["plain"] += 1
        _WHY_PLAIN[what] = str(exc)
        return result
    except OSError as exc:
        _WHY_PLAIN[what] = "not written (%s)" % exc
        return result
    _TALLY["drawn"] += 1
    _TALLY["drawn_s"] += seconds
    if _TALLY["drawn"] % 25 == 1:
        _prune()
    hit = _read(key)
    return hit[0] if hit is not None else result


def keep(fn):
    """Decorator: every call of `fn` goes through `kept`."""
    @functools.wraps(fn)
    def wrapper(*args, **kw):
        return kept(fn, *args, **kw)
    wrapper.__kept__ = True
    return wrapper


def tally() -> str:
    """One line for a build's log: how many kept results were read and how many computed."""
    s = ("kept: %(read)d read (%(read_s).0f s), %(drawn)d computed (%(drawn_s).0f s), "
         "%(plain)d not kept" % _TALLY)
    if _WHY_PLAIN:
        s += " [" + "; ".join("%s: %s" % kv for kv in sorted(_WHY_PLAIN.items())[:6]) + "]"
    return s
