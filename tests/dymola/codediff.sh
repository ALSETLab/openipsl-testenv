#!/usr/bin/env bash
# Generated code, Linux against Windows: diff of the dsmodel.c that Dymola for Linux and Dymola for Windows wrote
# for the same run (carriage returns of the Windows file removed). Shows whether the two translations are the same
# equations, so that a numerical difference can be put on the compilers and math libraries, not on the translation.
# Usage: bash codediff.sh <Linux runs dir> <Windows runs dir> [run names...]
set -uo pipefail
L="${1:?usage: codediff.sh <Linux runs dir> <Windows runs dir> [run names...]}"
W="${2:?Windows runs dir}"
shift 2
RUNS="${*:-$(cd "$L" && ls -d *__* )}"
tmp="$(mktemp)"
for r in $RUNS; do
  [ -f "$L/$r/dsmodel.c" ] && [ -f "$W/$r/dsmodel.c" ] || { echo "== $r: dsmodel.c missing"; continue; }
  tr -d '\r' < "$W/$r/dsmodel.c" > "$tmp"
  n=$(diff "$L/$r/dsmodel.c" "$tmp" | grep -c '^[<>]')
  echo "== $r: lines linux $(wc -l < "$L/$r/dsmodel.c"), windows $(wc -l < "$tmp"); differing lines (< linux, > windows): $n"
  diff "$L/$r/dsmodel.c" "$tmp" | cut -c1-220
done
rm -f "$tmp"
