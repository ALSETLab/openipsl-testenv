#!/usr/bin/env bash
# run_all.sh - the System Modeler (Linux, standalone kernel) runs of the IEEE/CIGRE DLL verification contract, one at a
# time (one System Modeler kernel at a time: the licence pool is shared). Normal user, inside the distro.
#
#   bash run_all.sh <package dir .../OpenIPSL> <record dir> [--compiler <path>|default] [--work <build root>]
#                   [--stage <ext4 record dir>] [run id ...]
#
# Default: all 15 runs of runs.json, compiler /opt/openipsl-kit/bin/g++-nopie, build root
# ~/cigre_verify/systemmodeler/runs, record staged in ~/cigre_verify/systemmodeler/record and copied (cp -r) into
# <record dir> at the end (Dropbox is never written while a run is going on: random file-lock failures).
# Console: <build root>/run_all_console.txt (follow it from Windows with
#   wsl -d openipsl-verify-24.04 -e tail -f /home/<user>/cigre_verify/systemmodeler/runs/run_all_console.txt).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage: run_all.sh <package dir> <record dir> [options] [run ids]}" && pwd)"
OUT="${2:?usage: run_all.sh <package dir> <record dir> [options] [run ids]}"
shift 2
COMPILER=/opt/openipsl-kit/bin/g++-nopie
WORK="$HOME/cigre_verify/systemmodeler/runs"
STAGE="$HOME/cigre_verify/systemmodeler/record"
RUNS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --compiler) COMPILER="$2"; shift 2 ;;
    --work) WORK="$2"; shift 2 ;;
    --stage) STAGE="$2"; shift 2 ;;
    *) RUNS+=("$1"); shift ;;
  esac
done
if [ ${#RUNS[@]} -eq 0 ]; then
  RUNS=(SCRX9__dassl SCRX9__euler SCRX9_vs_SCRX__dassl SCRX__dassl GFL_Fault__euler GFL_POCFault__euler
        GFL_FrequencyStep__euler GFL_VoltageStep__euler GFL_PowerRamp__euler GFL_FaultPSCAD__euler
        GFM_EMTPFault__euler GFM_EMTPFull__euler EMTPTransformerZeroSeq__euler SmoothShortFault__euler
        GFL_PowerRamp__dassl)
fi
mkdir -p "$WORK" "$STAGE"
CON="$WORK/run_all_console.txt"
{
  echo "### run_all.sh $(date '+%Y-%m-%d %H:%M:%S')  package $PKG  compiler $COMPILER  work $WORK  stage $STAGE"
  echo "### load before: $(cat /proc/loadavg); other tools running: $(pgrep -l -f 'dymosim|dymola|omc|WSMKernel' | tr '\n' ' ')"
  for r in "${RUNS[@]}"; do
    /usr/bin/python3 -I "$HERE/wsm_run_linux.py" --spec "$HERE/runs.json" --run "$r" --pkg "$PKG" --out "$STAGE" \
      --work "$WORK" --compiler "$COMPILER" --timeout 1800
    echo "### exit $? for $r at $(date '+%H:%M:%S'); load $(cat /proc/loadavg)"
  done
  echo "### all done $(date '+%H:%M:%S')"
} 2>&1 | tee -a "$CON"
mkdir -p "$OUT"
cp "$CON" "$STAGE/logs/run_all_console$( [ "$COMPILER" = default ] && echo _default_gpp ).txt" 2>/dev/null || true
cp -r "$STAGE/." "$OUT/"
echo "record copied to $OUT"
