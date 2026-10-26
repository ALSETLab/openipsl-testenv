#!/usr/bin/env bash
# run_analysis.sh - every comparison of the Linux System Modeler record (no kernel, no licence): Linux CSVs against the
# Windows round-2 CSVs, raw results bit for bit (Linux g++-nopie against the default compiler; Linux against the
# Windows round-2 raw results when their build tree is readable), the documented key values, the runs tables, every
# tool message. Normal user, inside the distro, after run_all.sh (both compilers) and run_diag_scrxfix.sh.
#
#   bash run_analysis.sh <record dir> <Windows round-2 record dir> [<Windows round-2 build tree .../round2/runs>]
#
# Output in ~/cigre_verify/systemmodeler/analysis, copied (cp -r) to <record dir>/analysis.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?usage: run_analysis.sh <record dir> <Windows record dir> [Windows runs dir]}"
W="${2:?usage}"
WR="${3:-}"
S="$HOME/cigre_verify/systemmodeler"
A="$S/analysis"
rm -rf "$A"; mkdir -p "$A/linux_vs_windows_raw" "$A/nopie_vs_default"
PY="/usr/bin/python3 -I"
{
echo "### run_analysis.sh $(date '+%Y-%m-%d %H:%M:%S')"
$PY "$HERE/compare_windows.py" --spec "$HERE/runs.json" --linux "$S/record" --windows "$W" --out "$A" > /dev/null && echo "compare_windows: $A/compare_windows.md"
$PY "$HERE/compare_windows.py" --spec "$HERE/runs_diag_scrxfix.json" --linux "$S/diag/record" --windows "$W/diagnostics/scrx_fix_b48d49e8" --out "$A" --name compare_windows_diag > /dev/null && echo "compare_windows (diagnostic): $A/compare_windows_diag.md"
$PY "$HERE/key_values.py" --record "$S/record" --record "$W" --labels "Linux,Windows round 2" --out "$A/key_values.md" > /dev/null && echo "key_values: $A/key_values.md"
$PY "$HERE/summarize.py" --spec "$HERE/runs.json" --linux "$S/record" --windows "$W" --out "$A/runs_table.md" > /dev/null
$PY "$HERE/summarize.py" --spec "$HERE/runs.json" --linux "$S/record_default_gpp" --windows "$S/record" --out "$A/runs_table_default_gpp.md" > /dev/null
$PY "$HERE/summarize.py" --spec "$HERE/runs_diag_scrxfix.json" --linux "$S/diag/record" --windows "$W/diagnostics/scrx_fix_b48d49e8" --out "$A/runs_table_diag.md" > /dev/null
echo "runs tables: $A/runs_table*.md"
$PY "$HERE/collect_messages.py" --spec "$HERE/runs.json" --linux "$S/record" --windows "$W" --out "$A/messages_linux_vs_windows.md" --json "$A/messages_linux_vs_windows.json" > /dev/null
$PY "$HERE/collect_messages.py" --spec "$HERE/runs.json" --linux "$S/record_default_gpp" --windows "$S/record" --out "$A/messages_default_gpp_vs_nopie.md" --label-linux "default g++" --label-windows "g++-nopie" > /dev/null
echo "messages: $A/messages_*.md"
echo "== g++-nopie against the default compiler, raw results"
for r in SCRX9__dassl:SCRX9 GFL_Fault__euler:GFL_Fault; do
  tag=${r%%:*}; s=${r##*:}
  $PY "$HERE/compare_mat.py" "$S/runs/$tag/${s}_res.mat" "$S/runs_default_gpp/$tag/${s}_res.mat" --label-a g++-nopie --label-b default_g++ --json "$A/nopie_vs_default/$tag.json"
  cmp -s "$S/record/$tag.csv" "$S/record_default_gpp/$tag.csv" && echo "$tag: CSV byte-identical" || echo "$tag: CSV differs"
done
if [ -n "$WR" ] && [ -d "$WR" ]; then
  echo "== Linux against Windows round 2, raw results"
  for r in SCRX9__dassl:SCRX9 SCRX9__euler:SCRX9 GFL_Fault__euler:GFL_Fault GFL_POCFault__euler:GFL_POCFault \
           GFL_FrequencyStep__euler:GFL_FrequencyStep GFL_VoltageStep__euler:GFL_VoltageStep \
           GFL_PowerRamp__euler:GFL_PowerRamp GFL_FaultPSCAD__euler:GFL_FaultPSCAD GFM_EMTPFault__euler:GFM_EMTPFault \
           GFM_EMTPFull__euler:GFM_EMTPFull EMTPTransformerZeroSeq__euler:EMTPTransformerZeroSeq \
           SmoothShortFault__euler:SmoothShortFault GFL_PowerRamp__dassl:GFL_PowerRamp; do
    tag=${r%%:*}; s=${r##*:}
    [ -f "$WR/$tag/${s}_res.mat" ] || { echo "$tag: no Windows raw result"; continue; }
    $PY "$HERE/compare_mat.py" "$S/runs/$tag/${s}_res.mat" "$WR/$tag/${s}_res.mat" --label-a linux --label-b windows --json "$A/linux_vs_windows_raw/$tag.json" | sed "s/^/$tag: /"
  done
fi
echo "### done $(date '+%H:%M:%S')"
} 2>&1 | tee "$A/run_analysis_console.txt"
mkdir -p "$OUT/analysis"; cp -r "$A/." "$OUT/analysis/"; echo "copied to $OUT/analysis"
