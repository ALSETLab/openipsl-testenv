#!/usr/bin/env bash
# probe_folders.sh: which Resources/Library/<folder> omc links (-L order) and loads (DT_RPATH order) on this machine.
# Every layout gets its own copy of FolderProbe with libFolderProbe.so built into the named folders, each copy
# returning its folder number (base=1, aarch64-linux=2, linux64=3, arm64-linux=4); the simulated y names the copy loaded.
#   bash probe_folders.sh <out dir>
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(mkdir -p "${1:?usage}" && cd "$1" && pwd)"
declare -A ID=([base]=1 [aarch64-linux]=2 [linux64]=3 [arm64-linux]=4)
LAYOUTS=("none" "aarch64-linux" "linux64" "arm64-linux" "base" "aarch64-linux+linux64" "aarch64-linux+base" "base+aarch64-linux+linux64+arm64-linux")
SUMMARY="$OUT/LOOKUP_RESULTS.txt"
echo "# probe_folders.sh $(date -Iseconds) on $(uname -m), $(omc --version)" > "$SUMMARY"
for lay in "${LAYOUTS[@]}"; do
  d="$OUT/$lay"; rm -rf "$d"; mkdir -p "$d/run"
  cp -r "$HERE/FolderProbe" "$d/"
  lib="$d/FolderProbe/Resources/Library"; mkdir -p "$lib"
  if [ "$lay" != none ]; then
    IFS=+ read -ra fs <<< "$lay"
    for f in "${fs[@]}"; do
      if [ "$f" = base ]; then t="$lib"; else t="$lib/$f"; mkdir -p "$t"; fi
      gcc -O2 -fPIC -shared -DFOLDER_ID=${ID[$f]} "$HERE/folder_probe.c" -o "$t/libFolderProbe.so"
    done
  fi
  cat > "$d/run/run.mos" <<MOS
loadFile("$d/FolderProbe/package.mo"); getErrorString();
cd("$d/run");
simulate(FolderProbe.M, stopTime=0.01, numberOfIntervals=1, fileNamePrefix="M");
print("SIMERR " + getErrorString() + "\nEND\n");
print("Y_AT_END " + String(val(y, 0.01, "M_res.mat")) + "\n");
MOS
  (cd "$d/run" && omc run.mos > log.txt 2>&1)
  y=$(grep -o 'Y_AT_END [-0-9.e+]*' "$d/run/log.txt" | awk '{print $2}')
  mk="$d/run/M.makefile"
  L=$(grep -E '^omc_main_target' -A1 "$mk" 2>/dev/null | tail -1 | grep -oE -- '-L"?[^" ]+' | sed 's/^-L"\{0,1\}//' | sed "s#$d/FolderProbe#<pkg>#" | tr '\n' ' ')
  rp=""; [ -x "$d/run/M" ] && rp=$(readelf -d "$d/run/M" | grep -E 'RPATH|RUNPATH' | sed "s#$d/FolderProbe#<pkg>#g")
  ld=""; [ -x "$d/run/M" ] && ld=$(ldd "$d/run/M" | grep FolderProbe | sed "s#$d/FolderProbe#<pkg>#g")
  nf=$(grep -A8 'Could not find library' "$d/run/log.txt" | sed "s#$d/FolderProbe#<pkg>#g" | head -8)
  {
    echo "== layout: $lay"
    echo "y (folder number loaded): ${y:-none}"
    echo "link -L: ${L:-none}"
    echo "executable: ${rp:-no executable}"
    echo "ldd: ${ld:-none}"
    [ -n "$nf" ] && echo "omc: $nf"
    grep -m3 -iE 'error|undefined reference|cannot find|skipping incompatible' "$d/run/log.txt" | sed "s#$d/FolderProbe#<pkg>#g"
  } >> "$SUMMARY"
done
cat "$SUMMARY"
