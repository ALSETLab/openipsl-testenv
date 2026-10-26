#!/usr/bin/env bash
# run_diag_scrxfix.sh - DIAGNOSTIC (not contract runs): the two native-SCRX runs (SCRX9_vs_SCRX, PSSE.ES.SCRX) on a copy
# of the package whose OpenIPSL/Electrical/Controls/PSSE/ES/SCRX.mo is replaced by the file of OpenIPSL commit
# b48d49e8 (branch fix/scrx-start-value, the separate pull request of decision D.2), as the Windows round 2 did.
#
#   bash run_diag_scrxfix.sh <package dir .../OpenIPSL> <SCRX.mo of b48d49e8> <record dir>
#
# Get the file read-only from a clone: git -C <clone> show b48d49e8:OpenIPSL/Electrical/Controls/PSSE/ES/SCRX.mo > SCRX.mo
# Library copy ~/cigre_verify/systemmodeler/diag/scrxfix/OpenIPSL, build root ~/cigre_verify/systemmodeler/diag/runs,
# record staged in ~/cigre_verify/systemmodeler/diag/record, copied to <record dir>.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage}" && pwd)"; FIX="${2:?usage}"; OUT="${3:?usage}"
D="$HOME/cigre_verify/systemmodeler/diag"
rm -rf "$D/scrxfix"; mkdir -p "$D/scrxfix" "$D/runs" "$D/record"
cp -r "$PKG" "$D/scrxfix/OpenIPSL"
chmod -R u+w "$D/scrxfix/OpenIPSL"
cp "$FIX" "$D/scrxfix/OpenIPSL/Electrical/Controls/PSSE/ES/SCRX.mo"
{
  echo "### run_diag_scrxfix.sh $(date '+%Y-%m-%d %H:%M:%S'); SCRX.mo sha256 $(sha256sum "$FIX" | cut -c1-64)"
  diff -rq "$PKG" "$D/scrxfix/OpenIPSL"
  for r in SCRX9_vs_SCRX__dassl SCRX__dassl; do
    /usr/bin/python3 -I "$HERE/wsm_run_linux.py" --spec "$HERE/runs_diag_scrxfix.json" --run "$r" --pkg "$D/scrxfix/OpenIPSL" \
      --out "$D/record" --work "$D/runs" --timeout 1800
    echo "### exit $? for $r at $(date '+%H:%M:%S')"
  done
} 2>&1 | tee "$D/record/console.txt"
mkdir -p "$OUT"; cp -r "$D/record/." "$OUT/"; echo "record copied to $OUT"
