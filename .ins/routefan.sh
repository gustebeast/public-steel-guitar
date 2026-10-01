#!/usr/bin/env bash
# Route several variants of the optical board AT ONCE, and report what each one gives.
#
# WHY: freerouting is deterministic per input and CHAOTIC across inputs. Five routes of
# five placements gave 8, 9, 10, 13, 13 unconnected, and none of it is a smooth function
# of the knob being turned -- widening the analog wall measured WORSE than leaving it, and
# so did widening the corridor outside it. Reasoning about which single change to spend an
# hour on has been wrong more often than right, because the surface is not smooth enough
# to reason about locally.
#
# The machine has 16 cores and freerouting runs single-threaded (-mt 1, its multi-threaded
# optimiser is known to emit clearance violations). One variant per hour is therefore a
# self-imposed limit, not a real one. Six at once turns a day of sampling into an hour.
#
# ⚠ EACH VARIANT NEEDS ITS OWN TREE. They all write elec/out/optical.*; sharing a
# directory would have them overwrite each other's netlists and DRC, and the results would
# be a mixture that still looks like a clean table.
#
#   bash .ins/routefan.sh 'name1:sed-expr' 'name2:sed-expr' ...
#
# The sed expression is applied to src/optical_pickup.py in that variant's tree only.
# An empty expression routes the tree as it stands (the control -- always include one).
# ⚠ NICE BY DEFAULT, AND THE DEFAULT PARALLELISM IS LOW. This runs on the USER'S desktop.
# Six JVMs at ~1.6 GB and a core each was launched while they were trying to play a game,
# and it made the machine unusable -- 16 cores is not headroom to claim, it is somebody's
# computer. FAN_JOBS caps how many route at once; FAN_NICE runs them below normal so an
# interactive program always wins.
set -u
JOBS="${FAN_JOBS:-2}"
pids=""
NICE="${FAN_NICE:-/low}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
KI="C:/Program Files/KiCad/10.0/bin/python.exe"
FAN="${SCRATCH:-/c/Users/gus/AppData/Local/Temp/claude/C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar/d7576032-b257-4aee-8a45-89e587fe4007/scratchpad}/fan"
mkdir -p "$FAN"

for spec in "$@"; do
  # name:pattern=>repl            edits src/optical_pickup.py
  # name:FILE:pattern=>repl       edits FILE (e.g. elec/optical.py, for the router strategy)
  name="${spec%%:*}"; expr="${spec#*:}"
  [ "$expr" = "$name" ] && expr=""
  file="src/optical_pickup.py"
  case "$expr" in
    */*.py:*) file="${expr%%:*}"; expr="${expr#*:}";;
  esac
  d="$FAN/$name"
  rm -rf "$d"; mkdir -p "$d"
  # only the code: elec/out is 32 MB of prior artefacts and every tree regenerates its own
  # the exact set the generator needs, found by running it in an empty tree until it
  # stopped complaining: BOM.md is one of them, because optical.py CHECKS the netlist
  # against it and treats a missing file as a hard error rather than as "no BOM to check".
  for sub in src cadkit tools; do cp -r "$SRC/$sub" "$d/"; done
  mkdir -p "$d/elec/out"
  cp "$SRC"/elec/*.py "$d/elec/" 2>/dev/null
  cp -r "$SRC"/elec/footprints "$SRC"/elec/geom "$d/elec/" 2>/dev/null
  cp "$SRC"/BOM.md "$d/" 2>/dev/null
  # ⚠ NOT `[ -n "$expr" ] && py ... || echo FAILED`. With an empty expr -- the control,
  # the one variant that must always run -- the test fails, && short-circuits, and the ||
  # branch reports EDIT FAILED for a variant that correctly wanted no edit. The control is
  # the variant whose loss costs most: without it the others have nothing to be read
  # against. Use an explicit if.
  if [ -n "$expr" ]; then py -3.12 -c "
import io,re,sys
p=sys.argv[1]; s=io.open(p,encoding='utf-8').read()
pat,rep=sys.argv[2].split('=>')
s2=re.sub(pat,rep,s,count=1)
assert s2!=s, 'variant edit matched nothing: '+pat
io.open(p,'w',encoding='utf-8',newline='\r\n').write(s2)" "$d/$file" "$expr" || { echo "$name: EDIT FAILED"; continue; }
  fi
  (
    cd "$d" || exit 1
    if ! py -3.12 elec/optical.py > gen.log 2>&1; then
      echo "$name: GENERATOR FAILED -- $(tail -1 gen.log)"; exit 1
    fi
    powershell -NoProfile -ExecutionPolicy Bypass -File "$SRC/.ins/lowrun.ps1"         -Exe "$KI" -Log finish.log elec/finish.py elec/out/optical >/dev/null 2>&1
    # ⚠ A MISSING RESULT MUST NOT PRINT AS A RESULT. When `start` silently ran nothing,
    # every finish.log was empty and this line still printed six well-formed rows -- the
    # name, "0 unexpected", and two blanks where the numbers go -- which reads as six
    # routes that found nothing wrong rather than as six routes that never ran. It is the
    # same shape of bug as the control variant's EDIT FAILED: a harness reporting
    # success for a non-event, in output tidy enough that nobody looks twice.
    got=$(grep -oE '[0-9]+ unconnected, [0-9]+ violation\(s\)' finish.log | tail -1)
    if [ -z "$got" ]; then
      echo "$name: NO RESULT -- finish.log $(wc -c < finish.log) bytes, last line: $(tail -1 finish.log | cut -c1-60)"
    else
      echo "$name: $got | $(grep -cE 'UNEXPECTED' finish.log) unexpected | $(grep -oE 'laid [0-9]+ segment' finish.log | tail -1)"
    fi
  ) &
  # ⚠ NOT `while [ "$(jobs -r | wc -l)" -ge "$JOBS" ]`. `$(...)` is a SUBSHELL and a
  # subshell has no job table, so that count is meaningless -- the throttle either spins or
  # jams. It jammed: a run of eight launched four, never created the other four trees, and
  # sat holding two JVMs for an hour and a half before the user asked what was running.
  # Count the PIDs we started, which is state this shell actually owns.
  pids="$pids $!"
  while :; do
    live=""
    for q in $pids; do kill -0 "$q" 2>/dev/null && live="$live $q"; done
    pids="$live"
    set -- $pids
    [ "$#" -lt "$JOBS" ] && break
    sleep 5
  done
done
wait
echo "--- trees kept under $FAN for the winner to be copied back"
