#!/usr/bin/env bash
# run_validation.sh - validation of every class of the IEEE_CIGRE packages (and the two UsersGuide classes) with
# System Modeler's standalone kernel on Linux (checkModelTest, one session per class, unit violations as warnings,
# setCompilerPath(/opt/openipsl-kit/bin/g++-nopie) for the external-function evaluator), plus the five diagnostic
# classes of the Windows round 2 (experiments/WSMExperimentsRound2.mo). Two controls: the negative control once more
# with the kernel's default unit severity, and all 57 classes once more with the kernel's default compiler (its
# evaluator link fails; are the verdicts the same?). Normal user, inside the distro.
#
#   bash run_validation.sh <package dir .../OpenIPSL> <record dir> [<Windows round-2 wsm_validate.json>]
#
# Build tree ~/cigre_verify/systemmodeler/validation, record staged in ~/cigre_verify/systemmodeler/record and copied
# (cp -r) into <record dir> at the end.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage: run_validation.sh <package dir> <record dir> [windows json]}" && pwd)"
OUT="${2:?usage: run_validation.sh <package dir> <record dir> [windows json]}"
WIN="${3:-}"
WORK="$HOME/cigre_verify/systemmodeler/validation"
STAGE="$HOME/cigre_verify/systemmodeler/record"
mkdir -p "$WORK" "$STAGE/logs"
rm -rf "$WORK"/warning "$WORK"/default "$WORK"/default_gpp "$STAGE"/logs/validation* "$STAGE"/validation*
/usr/bin/python3 -I "$HERE/list_classes.py" "$PKG" > "$STAGE/logs/classes.txt"
printf '%s\n' WSMExperimentsRound2.EMTPTransformerOpen WSMExperimentsRound2.EMTPTransformerWinding1Loaded \
  WSMExperimentsRound2.EMTPTransformerOpenNoInitFilters WSMExperimentsRound2.EMTPTransformerZeroSeqOpen \
  WSMExperimentsRound2.UnitCheckNegativeControl > "$STAGE/logs/experiment_classes.txt"
echo WSMExperimentsRound2.UnitCheckNegativeControl > "$STAGE/logs/negative_control.txt"
{
  echo "### run_validation.sh $(date '+%Y-%m-%d %H:%M:%S')  package $PKG; $(wc -l < "$STAGE/logs/classes.txt") classes + 5 diagnostic"
  echo "### load before: $(cat /proc/loadavg); other tools running: $(pgrep -l -f 'dymosim|dymola|omc|WSMKernel' | tr '\n' ' ')"
  /usr/bin/python3 -I "$HERE/validate_classes.py" --pkg "$PKG" --classes "$STAGE/logs/classes.txt" \
    --extra "$HERE/experiments/WSMExperimentsRound2.mo" --extra-classes "$STAGE/logs/experiment_classes.txt" \
    --work "$WORK/warning" --out "$STAGE" --severity warning --name validation ${WIN:+--windows-json "$WIN"}
  echo "### negative control with the kernel's default unit-violation severity"
  : > "$STAGE/logs/empty_classes.txt"
  /usr/bin/python3 -I "$HERE/validate_classes.py" --pkg "$PKG" --classes "$STAGE/logs/empty_classes.txt" \
    --extra "$HERE/experiments/WSMExperimentsRound2.mo" --extra-classes "$STAGE/logs/negative_control.txt" \
    --work "$WORK/default" --out "$STAGE" --severity default --name validation_default_severity
  echo "### all classes once more with the kernel's default compiler (no setCompilerPath)"
  /usr/bin/python3 -I "$HERE/validate_classes.py" --pkg "$PKG" --classes "$STAGE/logs/classes.txt"     --extra "$HERE/experiments/WSMExperimentsRound2.mo" --extra-classes "$STAGE/logs/experiment_classes.txt"     --work "$WORK/default_gpp" --out "$STAGE" --severity warning --compiler default --name validation_default_gpp     ${WIN:+--windows-json "$WIN"}
  rm -f "$STAGE/logs/empty_classes.txt"
  echo "### done $(date '+%H:%M:%S')"
} 2>&1 | tee "$WORK/run_validation_console.txt"
cp "$WORK/run_validation_console.txt" "$STAGE/logs/"
mkdir -p "$OUT"
cp -r "$STAGE/." "$OUT/"
echo "record copied to $OUT"
