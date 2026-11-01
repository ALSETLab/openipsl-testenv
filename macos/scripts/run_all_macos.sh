#!/usr/bin/env bash
# run_all_macos.sh - the System Modeler (macOS, Apple Silicon, standalone kernel) runs of the IEEE/CIGRE DLL
# verification contract, one at a time. Port of the Linux kit's tests/systemmodeler/run_all.sh.
#   bash run_all_macos.sh <package dir .../OpenIPSL> <record dir> [--work <build root>] [--compiler <path>|default]
#                         [--no-dyld-path] [run id ...]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage}" && pwd)"
OUT="${2:?usage}"
shift 2
WORK="$HOME/arm-verify/build/wsm_runs"
EXTRA=()
RUNS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --work) WORK="$2"; shift 2 ;;
    --compiler) EXTRA+=(--compiler "$2"); shift 2 ;;
    --no-dyld-path) EXTRA+=(--no-dyld-path); shift ;;
    *) RUNS+=("$1"); shift ;;
  esac
done
if [ ${#RUNS[@]} -eq 0 ]; then
  RUNS=(SCRX9__dassl SCRX9__euler SCRX9_vs_SCRX__dassl SCRX__dassl GFL_Fault__euler GFL_POCFault__euler
        GFL_FrequencyStep__euler GFL_VoltageStep__euler GFL_PowerRamp__euler GFL_FaultPSCAD__euler
        GFM_EMTPFault__euler GFM_EMTPFull__euler EMTPTransformerZeroSeq__euler SmoothShortFault__euler
        GFL_PowerRamp__dassl)
fi
mkdir -p "$WORK" "$OUT/logs"
CON="$OUT/logs/run_all_console.txt"
{
  echo "### run_all_macos.sh $(date '+%Y-%m-%d %H:%M:%S')  package $PKG  work $WORK  extra ${EXTRA[*]:-}"
  echo "### load before: $(sysctl -n vm.loadavg); other tools running: $(pgrep -l -f 'omc|WSMKernel|dymosim' | tr '\n' ' ')"
  for r in "${RUNS[@]}"; do
    /opt/homebrew/bin/python3.15 -I "$HERE/wsm_run_macos.py" --spec "$HERE/runs.json" --run "$r" --pkg "$PKG" --out "$OUT" \
      --work "$WORK" --timeout 1800 ${EXTRA[@]+"${EXTRA[@]}"}
    echo "### exit $? for $r at $(date '+%H:%M:%S'); load $(sysctl -n vm.loadavg)"
  done
  echo "### all done $(date '+%H:%M:%S')"
} 2>&1 | tee -a "$CON"
