#!/usr/bin/env bash
# OpenModelica verification of the IEEE_CIGRE tests on macOS (Apple Silicon): every step of omc_verify_macos.py in
# order. Port of the Linux kit's tests/openmodelica/run_all.sh.
#   bash run_all_om_macos.sh <package dir .../OpenIPSL> <record dir> [<build dir>]
# Environment: OMC (omc path), STEPS (default "env checks extras run timing binding compare table"), OMC_TIMING_REPS
# (default 3), WIN_RECORD (the Windows round-2 OpenModelica record, for "compare"; read only), MODELICAPATH.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage}" && pwd)"
OUT="${2:?usage}"
BUILD="${3:-$HOME/arm-verify/build/om_runs}"
STEPS="${STEPS:-env checks extras run timing binding compare table}"
PY=/opt/homebrew/bin/python3.15
export OPENMODELICALIBRARY="${OPENMODELICALIBRARY:-$HOME/arm-verify/om/libs/omlibrary}"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
ARGS=(--pkg "$PKG" --build "$BUILD" --out "$OUT" --reps "${OMC_TIMING_REPS:-3}")
[ -n "${WIN_RECORD:-}" ] && ARGS+=(--win-record "$WIN_RECORD")
mkdir -p "$OUT/logs" "$BUILD"
LOG="$OUT/logs/run_all.log"
echo "== run_all_om_macos.sh $(date -Iseconds) pkg=$PKG build=$BUILD out=$OUT steps=[$STEPS] OMC=${OMC:-default}" | tee -a "$LOG"
rc=0
for s in $STEPS; do
  case "$s" in run|timing) set -- "$s" all ;; *) set -- "$s" ;; esac
  echo "== step $s $(date -Iseconds)" | tee -a "$LOG"
  "$PY" -I "$HERE/omc_verify_macos.py" "${ARGS[@]}" "$@" 2>&1 | tee -a "$LOG"
  st=${PIPESTATUS[0]}
  echo "== step $s exit $st $(date -Iseconds)" | tee -a "$LOG"
  [ "$st" -ne 0 ] && rc=1
done
exit $rc
