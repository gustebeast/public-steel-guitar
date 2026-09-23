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
NICE="${FAN_NICE:-/low}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
KI="C:/Program Files/KiCad/10.0/bin/python.exe"
FAN="${SCRATCH:-/c/Users/gus/AppData/Local/Temp/claude/C--Users-gus-Sync-Documents-Archive-3D-public-steel-guitar/d7576032-b257-4aee-8a45-89e587fe4007/scratchpad}/fan"
mkdir -p "$FAN"

for spec in "$@"; do
  name="${spec%%:*}"; expr="${spec#*:}"
  [ "$expr" = "$name" ] && expr=""
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
io.open(p,'w',encoding='utf-8',newline='\r\n').write(s2)" "$d/src/optical_pickup.py" "$expr" || { echo "$name: EDIT FAILED"; continue; }
  fi
  (
    cd "$d" || exit 1
    if ! py -3.12 elec/optical.py > gen.log 2>&1; then
      echo "$name: GENERATOR FAILED -- $(tail -1 gen.log)"; exit 1
    fi
    # //b keeps this console (so the redirection above still captures finish.py), and the
    # priority class is INHERITED by the java the router spawns -- which is the process
    # that actually costs the machine something.
    cmd //c start $NICE //b //wait "" "$KI" elec/finish.py elec/out/optical > finish.log 2>&1
    echo "$name: $(grep -oE '[0-9]+ unconnected, [0-9]+ violation\(s\)' finish.log | tail -1) \
| $(grep -cE 'UNEXPECTED' finish.log) unexpected \
| $(grep -oE 'laid [0-9]+ segment' finish.log | tail -1)"
  ) &
  while [ "$(jobs -r | wc -l)" -ge "$JOBS" ]; do wait -n 2>/dev/null || sleep 5; done
done
wait
echo "--- trees kept under $FAN for the winner to be copied back"
