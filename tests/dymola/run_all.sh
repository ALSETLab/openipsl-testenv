#!/usr/bin/env bash
# Dymola 2026x Refresh 1 for Linux: the verification runs of the OpenIPSL IEEE/CIGRE DLL package (replacing PR #362)
# with the SHIPPED Resources/Library/linux64/lib<Name>.so. Linux port of the Windows round-2 driver
# report/verification_round2/dymola/scripts/run_all.sh: the same 15 runs with the same arguments, one fresh hidden
# Dymola per run (dymola_run.py), then post.py writes the data-contract files.
#
# Usage (normal user, inside the distro):
#   bash run_all.sh <package dir .../OpenIPSL> <output dir> [run names...]
# Environment (optional):
#   BUILD=<build dir>        build tree and raw results, default ~/cigre_verify/dymola (ext4, never Dropbox)
#   DYMOLA_SH=<start script> default /opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh
#   CAP=<seconds>            Dymola's own wall-clock cap of one simulation (Advanced.Simulation.MaxRunTime), 1800
#   EVALUATE=true|false|keep Dymola's flag Evaluate for checks and runs (read before, written back). Default true:
#                            the setting in effect in the Windows round-2 record (a persistent flag of its
#                            setup.dymx); false is Dymola's default
#   WINDOWS_REC=<dir>        the Windows round-2 Dymola record for the self-comparison
#                            (default: $WINDOWS_RECORD_ROOT/dymola from the kit's site.env; none = step skipped)
#   WINDOWS_RUNS=<dir>       the Windows round-2 build tree (dsres.mat, dsmodel.c) for the stored-point comparison
#                            (default: $WINDOWS_RAW_ROOT/dymola/runs from site.env; none = raw comparison skipped)
#   KIT_SITE=<file>          the site settings file read for those two roots (default: <kit>/site.env, optional)
#   STEPS="checks runs diag compare copy"   the steps to do (default: all of them; with run names given:
#                            "runs compare copy")
# The record is assembled in $BUILD/record and copied with cp to <output dir> at the end (step copy), so that
# nothing is written into a Dropbox folder while Dymola runs.
set -uo pipefail
PKG_DIR="$(realpath "${1:?usage: run_all.sh <package dir .../OpenIPSL> <output dir> [run names...]}")"
OUT="${2:?usage: run_all.sh <package dir .../OpenIPSL> <output dir> [run names...]}"
shift 2
ALL="$*"
K="$(cd "$(dirname "$0")" && pwd)"
KIT_SITE="${KIT_SITE:-$K/../../site.env}"
# shellcheck source=/dev/null
[ -f "$KIT_SITE" ] && . "$KIT_SITE"
PY=/opt/openipsl-kit/venv-dymola/bin/python
BUILD="${BUILD:-$HOME/cigre_verify/dymola}"
DYMOLA_SH="${DYMOLA_SH:-/opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh}"
CAP="${CAP:-1800}"
EVALUATE="${EVALUATE:-true}"
if [ -n "$ALL" ]; then STEPS="${STEPS:-runs compare copy}"; else STEPS="${STEPS:-checks runs diag compare copy}"; fi
REC="$BUILD/record"
PKG="$PKG_DIR/package.mo"
T=OpenIPSL.Tests.Controls.IEEE_CIGRE
SETUP="$HOME/.dassaultsystemes/dymola/2026x Refresh 1/setup.dymx"
WINDOWS_REC="${WINDOWS_REC:-${WINDOWS_RECORD_ROOT:+$WINDOWS_RECORD_ROOT/dymola}}"
# the Windows round-2 build tree (raw dsres.mat and dsmodel.c), read only; the raw comparison is skipped without it
WINDOWS_RUNS="${WINDOWS_RUNS:-${WINDOWS_RAW_ROOT:+$WINDOWS_RAW_ROOT/dymola/runs}}"
step() { case " $STEPS " in *" $1 "*) return 0;; esac; return 1; }
sel() { [ -z "$ALL" ] && return 0; for x in $ALL; do [ "$x" = "$1" ] && return 0; done; return 1; }

[ -f "$PKG" ] || { echo "no package.mo in $PKG_DIR"; exit 2; }
[ -x "$DYMOLA_SH" ] || { echo "no Dymola start script $DYMOLA_SH"; exit 2; }
mkdir -p "$REC/logs" "$BUILD/runs"
echo "=== run_all.sh $(date -Is): package $PKG_DIR, build $BUILD, output $OUT, steps: $STEPS, Evaluate=$EVALUATE, runs: ${ALL:-all}"
( cd "$PKG_DIR/Resources/Library/linux64" && sha256sum lib*.so ) | tee "$REC/logs/linux64.sha256"
[ -f "$PKG_DIR/../COMMIT" ] && echo "commit $(cat "$PKG_DIR/../COMMIT")" | tee "$REC/logs/commit.txt"
{ step checks || step runs || step diag; } && [ -f "$SETUP" ] && cp -p "$SETUP" "$BUILD/setup_before_run_all.dymx"

if step checks; then
  echo "=== checks $(date +%H:%M:%S)"
  rm -rf "$BUILD/checks"; mkdir -p "$REC/logs/checks"
  "$PY" -I -B "$K/dymola_checks.py" --lib "$PKG_DIR" --work "$BUILD/checks" --out "$REC/logs/checks" \
    --dymola "$DYMOLA_SH" --evaluate "$EVALUATE" > "$REC/logs/checks/console.txt" 2>&1
  echo "checks exit $? $(date +%H:%M:%S)"; tail -n 2 "$REC/logs/checks/console.txt"
fi

# run <name> <grid for the CSV> <model> <solver> <stop> <interval> [step]
run() {
  name=$1; grid=$2; model=$3; solver=$4; stop=$5; interval=$6; stp=${7:-}
  sel "$name" || return 0
  W="$BUILD/runs/$name"
  rm -rf "$W"; mkdir -p "$W"
  stepargs=""; [ -n "$stp" ] && stepargs="--step $stp"
  cmd="$PY -I -B $K/dymola_run.py --package $PKG --model $model --work $W --solver $solver $stepargs --stop $stop --interval $interval --tolerance 1e-6 --maxruntime $CAP --dymola $DYMOLA_SH --evaluate $EVALUATE"
  echo "=== $name $(date +%H:%M:%S)"
  echo "$cmd" > "$W/driver.out"
  # outer cap: Dymola's own MaxRunTime stops the simulation at $CAP s; this one only guards a hung session
  timeout 2700 $cmd >> "$W/driver.out" 2>&1
  rc=$?
  echo "exit $rc $(date +%H:%M:%S)"
  "$PY" -I -B "$K/post.py" --run "$W" --name "$name" --out "$REC" --grid "$grid" --stop "$stop"
}

if step runs; then
  run SCRX9__dassl              0.001  $T.SCRX9.SCRX9                         dassl 10  0.005
  run SCRX9__euler              0.001  $T.SCRX9.SCRX9                         euler 10  0.005  0.005
  run SCRX9_vs_SCRX__dassl      0.001  $T.SCRX9.SCRX9_vs_SCRX                 dassl 10  0.005
  run SCRX__dassl               0.001  OpenIPSL.Tests.Controls.PSSE.ES.SCRX   dassl 10  0.005
  run GFL_Fault__euler          0.0001 $T.GFM.GFL_Fault                       euler 5.8 0.0001 1e-5
  run GFL_POCFault__euler       0.0001 $T.GFM.GFL_POCFault                    euler 4   0.0001 1e-5
  run GFL_FrequencyStep__euler  0.0001 $T.GFM.GFL_FrequencyStep               euler 3   0.0001 1e-5
  run GFL_VoltageStep__euler    0.0001 $T.GFM.GFL_VoltageStep                 euler 3   0.0001 1e-5
  run GFL_PowerRamp__euler      0.0001 $T.GFM.GFL_PowerRamp                   euler 3.6 0.0001 1e-5
  run GFL_FaultPSCAD__euler     0.0001 $T.GFM.GFL_FaultPSCAD                  euler 5.8 0.0001 1e-5
  run GFM_EMTPFault__euler      0.0001 $T.GFM.GFM_EMTPFault                   euler 5.9 0.0001 1e-5
  run GFM_EMTPFull__euler       0.0001 $T.GFM.GFM_EMTPFull                    euler 6   0.0001 1e-5
  run EMTPTransformerZeroSeq__euler 0.0001 $T.GFM.Components.EMTPTransformerZeroSeq euler 3 0.0001 1e-5
  run SmoothShortFault__euler   0.0001 $T.GFM.Components.SmoothShortFault     euler 5.5 0.0001 1e-5
  run GFL_PowerRamp__dassl      0.0001 $T.GFM.GFL_PowerRamp                   dassl 3.6 0.0001
  "$PY" -I -B "$K/post.py" --selftest "$BUILD/runs/SCRX9__dassl/dsres.mat" > "$REC/logs/reader_selftest.txt" 2>&1 || true
fi

if step diag; then
  echo "=== build diagnostics $(date +%H:%M:%S)"
  bash "$K/diag_build.sh" "$PKG_DIR" "$BUILD" "$REC" > "$REC/logs/diag_build_console.txt" 2>&1
  echo "diag exit $? $(date +%H:%M:%S)"
fi

if { step checks || step runs || step diag; } && [ -f "$SETUP" ] && [ -f "$BUILD/setup_before_run_all.dymx" ]; then
  { echo "# diff of $SETUP before and after run_all.sh ($(date -Is))"
    diff "$BUILD/setup_before_run_all.dymx" "$SETUP" && echo "(identical)"; } > "$REC/logs/setup_dymx_diff.txt"
fi

if step compare && [ ! -d "${WINDOWS_REC:-}" ]; then
  echo "=== self-comparison skipped: no Windows record (set WINDOWS_REC, or WINDOWS_RECORD_ROOT in site.env)"
elif step compare; then
  echo "=== self-comparison against the Windows round-2 record $(date +%H:%M:%S)"
  "$PY" -I -B "$K/compare_windows.py" --linux "$REC" --windows "$WINDOWS_REC" --out "$REC" --linux-runs "$BUILD/runs" \
    --windows-runs "$WINDOWS_RUNS" \
    > "$REC/logs/self_comparison_console.txt" 2>&1
  echo "compare exit $?"
  "$PY" -I -B "$K/raw_summary.py" "$REC/self_comparison.json" > "$REC/logs/self_comparison_raw.md" 2>&1
  "$PY" -I -B "$K/headline_values.py" --linux "$REC" --windows "$WINDOWS_REC" --out "$REC/headline_values.json" \
    > "$REC/logs/headline_values.md" 2>&1
  [ -d "$WINDOWS_RUNS" ] && bash "$K/codediff.sh" "$BUILD/runs" "$WINDOWS_RUNS" $ALL > "$REC/logs/dsmodel_linux_vs_windows.txt" 2>&1
  "$PY" -I -B "$K/table.py" "$REC" > "$REC/logs/table_of_runs.md" 2>&1
  "$PY" -I -B "$K/messages.py" "$REC" > "$REC/logs/unique_messages.md" 2>&1
fi

if step copy; then
  if [ "$(realpath -m "$OUT")" != "$(realpath -m "$REC")" ]; then
    mkdir -p "$OUT"
    cp -r "$REC/." "$OUT/"
    echo "=== record copied to $OUT $(date +%H:%M:%S)"
  fi
fi
echo "=== done $(date -Is)"
