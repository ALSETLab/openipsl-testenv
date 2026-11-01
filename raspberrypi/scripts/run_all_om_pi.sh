#!/usr/bin/env bash
# OpenModelica verification of the IEEE_CIGRE tests on Linux aarch64 (Raspberry Pi 400): every step of
# omc_verify_pi.py in order, one omc process at a time (3.7 GiB RAM). Port of run_all_om_macos.sh (itself a port of
# the Linux kit's tests/openmodelica/run_all.sh).
#   bash run_all_om_pi.sh <package dir .../OpenIPSL> <record dir> [<build dir>]
# Environment: OMC (omc path, default /usr/bin/omc), STEPS (default "env checks extras run timing binding compare
# table"), OMC_TIMING_REPS (default 3), WIN_RECORD (the Windows round-2 OpenModelica record, for "compare"; read only),
# KEYS (run keys for "run" and "timing", default all).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage}" && pwd)"
OUT="${2:?usage}"
BUILD="${3:-$HOME/arm-verify/build/om_runs}"
STEPS="${STEPS:-env checks extras run timing binding compare table}"
KEYS="${KEYS:-all}"
PY=/usr/bin/python3
ARGS=(--pkg "$PKG" --build "$BUILD" --out "$OUT" --reps "${OMC_TIMING_REPS:-3}")
[ -n "${WIN_RECORD:-}" ] && ARGS+=(--win-record "$WIN_RECORD")
mkdir -p "$OUT/logs" "$BUILD"
LOG="$OUT/logs/run_all.log"
echo "== run_all_om_pi.sh $(date -Iseconds) pkg=$PKG build=$BUILD out=$OUT steps=[$STEPS] keys=[$KEYS] OMC=${OMC:-/usr/bin/omc}" | tee -a "$LOG"
rc=0
for s in $STEPS; do
  case "$s" in run|timing) set -- "$s" $KEYS ;; *) set -- "$s" ;; esac
  echo "== step $s $(date -Iseconds)" | tee -a "$LOG"
  "$PY" -I "$HERE/omc_verify_pi.py" "${ARGS[@]}" "$@" 2>&1 | tee -a "$LOG"
  st=${PIPESTATUS[0]}
  echo "== step $s exit $st $(date -Iseconds)" | tee -a "$LOG"
  [ "$st" -ne 0 ] && rc=1
done
exit $rc
