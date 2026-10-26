#!/usr/bin/env bash
# Build diagnostics for Dymola for Linux (normal user): how dymosim is compiled and linked against the shipped
# Resources/Library/linux64/lib<Name>.so, and how it finds the library at run time.
#   1. translate-only runs of one SCRX9 test and one GFM test under strace (execve only): the exact dsbuild.sh
#      call Dymola makes, the exact cc command line (the link line with -L, -Wl,-rpath and -l<Name>), the
#      collect2/ld calls, and the wall time of dsbuild.sh (start and exit of its process);
#   2. for each of the two dymosim: readelf -d (NEEDED, RUNPATH/RPATH), readelf -p .comment, ldd, the
#      dllLibraryPath[] entries of dsmodel.c;
#   3. the loader's own account (LD_DEBUG=libs) of the library search, from a copy of dymosim in an empty folder;
#   4. LD_DEBUG=files over a complete SCRX9 simulation in a copy of the run folder: whether the runtime's
#      DymosimEnsureDLLLoaded(dllLibraryPath) opens the library a second time.
# Usage: bash diag_build.sh <package dir .../OpenIPSL> <build dir> <record dir>
# Writes <record dir>/logs/build_diagnostics.txt and <record dir>/logs/strace_<test>.txt.
set -uo pipefail
PKG="${1:?usage: diag_build.sh <package dir> <build dir> <record dir>}"
B="${2:?build dir}"
OUT="${3:?record dir}"
K="$(cd "$(dirname "$0")" && pwd)"
PY=/opt/openipsl-kit/venv-dymola/bin/python
T=OpenIPSL.Tests.Controls.IEEE_CIGRE
mkdir -p "$OUT/logs" "$B/diag"
LOG="$OUT/logs/build_diagnostics.txt"
: > "$LOG"
say() { echo "$*" | tee -a "$LOG"; }

say "# Dymola for Linux build diagnostics, $(date -Is)"
say "system: $(. /etc/os-release && echo "$PRETTY_NAME"), $(ldd --version | head -n1), kernel $(uname -r)"
say "cc: $(command -v cc) -> $(readlink -f "$(command -v cc)"); $(cc --version | head -n1)"
say "package: $PKG"
( cd "$PKG/Resources/Library/linux64" && sha256sum lib*.so ) | tee -a "$LOG"

for pair in "SCRX9:$T.SCRX9.SCRX9:dassl:10:0.005" "GFL_Fault:$T.GFM.GFL_Fault:euler:5.8:0.0001"; do
  IFS=: read -r name model solver stop interval <<< "$pair"
  W="$B/diag/${name}_translate"
  rm -rf "$W"; mkdir -p "$W"
  step=""; [ "$solver" = euler ] && step="--step 1e-5"
  TR="$OUT/logs/strace_${name}.txt"
  say ""
  say "== $name: translate-only under strace -f -tt -e trace=execve"
  strace -f --seccomp-bpf -tt -s 8192 -e trace=execve -e signal=none -o "$B/diag/strace_${name}.raw" \
    "$PY" -I -B "$K/dymola_run.py" --package "$PKG/package.mo" --model "$model" --work "$W" \
    --solver "$solver" $step --stop "$stop" --interval "$interval" --translate-only > "$W/driver.out" 2>&1
  say "dymola_run.py exit $?"
  # keep only the build: dsbuild.sh and everything it started, and the exits of those processes
  grep -E 'dsbuild|/cc"|"cc"|x86_64-linux-gnu-gcc|cc1"|collect2|/ld"|exited with' "$B/diag/strace_${name}.raw" \
    | grep -vE '^\s*$' > "$B/diag/strace_${name}.build" || true
  pids=$(grep -E 'execve\(.*dsbuild\.sh' "$B/diag/strace_${name}.raw" | grep -v ENOENT | awk '{print $1}' | sort -u)
  {
    echo "# strace -f -tt -e trace=execve of a translate-only Dymola session ($model), build processes only"
    grep -E 'execve\(("[^"]*(dsbuild\.sh|/cc|x86_64-linux-gnu-gcc-13|cc1|as|collect2|ld)"|.*dsbuild\.sh)' "$B/diag/strace_${name}.raw" \
      | grep -v ENOENT
    echo "# exits of the dsbuild.sh processes"
    for p in $pids; do grep -E "^$p .*exited with" "$B/diag/strace_${name}.raw"; done
  } > "$TR"
  say "dsbuild.sh call:"
  grep -E 'execve\(.*dsbuild\.sh' "$B/diag/strace_${name}.raw" | grep -v ENOENT | sed 's/^/  /' | tee -a "$LOG" > /dev/null
  say "cc call (compile and link, one command):"
  grep -E 'execve\("/usr/bin/cc"' "$B/diag/strace_${name}.raw" | sed 's/^/  /' | tee -a "$LOG" > /dev/null
  say "collect2 call (the link):"
  grep -E 'execve\("[^"]*collect2"' "$B/diag/strace_${name}.raw" | sed 's/^/  /' | cut -c1-6000 | tee -a "$LOG" > /dev/null
  for p in $pids; do
    t0=$(grep -E "^$p .*execve\(.*dsbuild\.sh" "$B/diag/strace_${name}.raw" | head -n1 | awk '{print $2}')
    t1=$(grep -E "^$p .*exited with" "$B/diag/strace_${name}.raw" | tail -n1 | awk '{print $2}')
    say "dsbuild.sh pid $p: started $t0, exited $t1"
  done
  python3 -I -c "import json,sys; r=json.load(open(sys.argv[1])); b=r.get('build',{}); print('build_s_from_mtimes %.3f s; Dymola reported compilation time %s s; translateModel wall %.3f s; total translation %s s' % (b.get('build_s_from_mtimes') or -1, r['times_s'].get('dymola_compilation_time_s'), r['times_s'].get('translateModel_wall'), r['times_s'].get('dymola_total_translation_time_s')))" "$W/run.json" | tee -a "$LOG"
  say "-- ELF facts of $W/dymosim"
  ( cd "$W" && readelf -d dymosim | grep -E 'NEEDED|RUNPATH|RPATH' ) | tee -a "$LOG"
  ( cd "$W" && readelf -p .comment dymosim | sed -n 's/^ *\[ *[0-9a-f]*\] */  .comment: /p' ) | tee -a "$LOG"
  ( cd "$W" && ldd ./dymosim ) | tee -a "$LOG"
  say "dsmodel.c dllLibraryPath[]:"
  awk '/dllLibraryPath\[\]=\{/,/^0\};/' "$W/dsmodel.c" | sed 's/^/  /' | tee -a "$LOG"
  say "buildlog.txt:"
  sed 's/^/  /' "$W/buildlog.txt" | tee -a "$LOG"
  say "-- LD_DEBUG=libs: the loader's search for the NEEDED libraries (copy of dymosim in an empty folder)"
  E="$B/diag/${name}_ldd"; rm -rf "$E"; mkdir -p "$E"; cp "$W/dymosim" "$E/"
  ( cd "$E" && env -u LD_LIBRARY_PATH LD_DEBUG=libs ./dymosim > dymosim.out 2> ld_debug.txt; echo "dymosim exit $? (no dsin.txt here, so it stops after loading)" ) | tee -a "$LOG"
  grep -E 'find library=lib(SCRX9|GFM_GFL_IBR)|search path=|trying file=.*(SCRX9|GFM_GFL_IBR)|calling init: .*(SCRX9|GFM_GFL_IBR)' "$E/ld_debug.txt" \
    | grep -B1 -A3 -E 'lib(SCRX9|GFM_GFL_IBR)' | sed 's/^ *[0-9]*: */  /' | head -n 12 | tee -a "$LOG"
  say "LD_LIBRARY_PATH in this shell: '${LD_LIBRARY_PATH:-}' (unset for the test above)"
done

say ""
say "== a complete SCRX9 simulation (copy of the translate folder, its dsin.txt) under LD_DEBUG=files"
S="$B/diag/SCRX9_files"; rm -rf "$S"; cp -r "$B/diag/SCRX9_translate" "$S"
( cd "$S" && env -u LD_LIBRARY_PATH LD_DEBUG=files ./dymosim > dymosim.out 2> ld_files.txt; echo "dymosim exit $?" ) | tee -a "$LOG"
say "every loader event naming libSCRX9.so (a dlopen by DymosimEnsureDLLLoaded would appear as 'dynamically loaded by'):"
grep -E 'libSCRX9' "$S/ld_files.txt" | sed 's/^ *[0-9]*: */  /' | tee -a "$LOG"
grep -E 'SUCCESSFUL|terminated' "$S/dslog.txt" | sed 's/^/  dslog: /' | tee -a "$LOG"
say "raw strace files kept in $B/diag/"
