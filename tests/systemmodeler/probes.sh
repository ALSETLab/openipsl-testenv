#!/usr/bin/env bash
# probes.sh - DIAGNOSTIC probes behind statements of the Linux System Modeler record (not contract runs). Normal user,
# inside the distro, after run_all.sh (it reuses the SCRX9__dassl build). One kernel or simulation at a time.
#
#   bash probes.sh <package dir .../OpenIPSL> <record dir> [<build root of run_all.sh>]
#
# P1  the built executable without LD_LIBRARY_PATH: does it find lib<Name>.so by itself?
# P2  the SCRX9 executable with the nonlinear-system log: the residual behind Windows' "[init:246] Accepting solution
#     to nonlinear system ... residual looks big: 2.50356e-09", which the Linux runs do not print
# P3  what the kernel's script language offers for validation: mce_checkModel (returns the validation report),
#     instantiateModelTest (flatten only), checkModel and validateModel (do they exist?), the unit-violation severity
#     getter. Messages accumulate in a session, so the calls that fail come last; the final instantiateModelTest of a
#     valid class reports the errors those calls raised (a call to a missing function prints nothing by itself).
# P4  the kernel's external-function evaluator: compiled and linked how, and does it find libSCRX9.so by itself?
#     (a compiler wrapper that logs every call and keeps every linked output, used only here)
# P5  where the executable's stderr goes when stdout and stderr share one file: the runner therefore keeps them apart
# Output: <record dir>/diagnostics/probes/probes.txt (+ the files each probe keeps).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$(cd "${1:?usage: probes.sh <package dir> <record dir> [build root]}" && pwd)"
OUT="${2:?usage: probes.sh <package dir> <record dir> [build root]}"
RUNS="${3:-$HOME/cigre_verify/systemmodeler/runs}"
WSM="${WSM_TARGET:-/usr/local/Wolfram/SystemModeler/15.0}"
P="$HOME/cigre_verify/systemmodeler/probes"
rm -rf "$P"; mkdir -p "$P"
LIB="$PKG/Resources/Library/linux64"
B="$RUNS/SCRX9__dassl"
{
echo "### probes.sh $(date '+%Y-%m-%d %H:%M:%S'); package $PKG; kernel $("$WSM/bin/WSMKernelX" --version 2>&1 | tail -n1)"

echo; echo "=== P1 SCRX9.exe without LD_LIBRARY_PATH"
( cd "$P" && env -u LD_LIBRARY_PATH "$B/SCRX9.exe" -f "$B/SCRX9.sim" -r "$P/p1.mat" 2>&1 | head -5; echo "exit ${PIPESTATUS[0]}" )
echo "-- readelf -d (NEEDED, RUNPATH, RPATH)"; readelf -d "$B/SCRX9.exe" | grep -E 'NEEDED|RUNPATH|RPATH'
echo "-- shipped library: readelf -d"; readelf -d "$LIB/libSCRX9.so" | grep -E 'NEEDED|SONAME|RUNPATH|RPATH|FLAGS'

echo; echo "=== P2 SCRX9.exe -v5 -ls nonlin,init (the initial nonlinear system [init:246] and its residual)"
( cd "$P" && LD_LIBRARY_PATH="$LIB" "$B/SCRX9.exe" -f "$B/SCRX9.sim" -r "$P/p2.mat" -v5 -ls nonlin,init 2>&1 | cat > "$P/p2_full.txt"; echo "exit ${PIPESTATUS[0]} (stderr merged through a pipe, see P5)" )
head -n 420 "$P/p2_full.txt" > "$P/p2_log.txt"
grep -m 3 -A 7 'Accepting solution' "$P/p2_full.txt" > "$P/p2_accepting.txt"
echo "-- the full log: $(wc -l < "$P/p2_full.txt") lines; 'Accepting solution' lines: $(grep -c 'Accepting solution' "$P/p2_full.txt"); first ones with their residuals:"
cat "$P/p2_accepting.txt"
rm -f "$P/p2_full.txt"
rm -f "$P/p1.mat" "$P/p2.mat"

echo; echo "=== P5 the executable's stderr when stdout and stderr go to one file (Windows' sim_out.txt has the warning)"
W5="$P/p5"; mkdir -p "$W5"
( cd "$W5" && LD_LIBRARY_PATH="$LIB" "$B/SCRX9.exe" -f "$B/SCRX9.sim" -r "$W5/a.mat" > a_out.txt 2> a_err.txt
  LD_LIBRARY_PATH="$LIB" "$B/SCRX9.exe" -f "$B/SCRX9.sim" -r "$W5/b.mat" > b_merged.txt 2>&1
  LD_LIBRARY_PATH="$LIB" "$B/SCRX9.exe" -f "$B/SCRX9.sim" -r "$W5/c.mat" 2>&1 | cat > c_pipe.txt
  for f in a_out.txt a_err.txt b_merged.txt c_pipe.txt; do
    echo "$f: $(wc -c < "$f") bytes, $(wc -l < "$f") lines, warning lines: $(grep -c 'Accepting solution' "$f")"; done
  echo "-- a_err.txt"; cat a_err.txt
  echo "-- b_merged.txt identical to a_out.txt (stdout alone): $(cmp -s a_out.txt b_merged.txt && echo yes || echo no)"
  rm -f a.mat b.mat c.mat a.jsonl b.jsonl c.jsonl )

echo; echo "=== P3 the kernel's validation entry points"
W3="$P/p3"; mkdir -p "$W3"; cd "$W3" || exit 1
printf '%s\n%s\n' "$WSM/L/Modelica 4.0.0" "$WSM/L/SystemModelerExtras" > ModelicaPath.txt
cat > p3.mos <<MOS
setStopOnError(false);
setTempDirectoryPath("$W3");
setCompilerPath("/opt/openipsl-kit/bin/g++-nopie");
loadLibrary(Modelica);
loadFile("$PKG/package.mo");
loadFile("$HERE/experiments/WSMExperimentsRound2.mo");
mce_getUnitViolationSeverity();
mce_checkModel(OpenIPSL.Tests.Controls.IEEE_CIGRE.GFM.GFL_Fault);
mce_checkModel(OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer);
instantiateModelTest(OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer);
checkModel(OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer);
validateModel(OpenIPSL.Electrical.Controls.IEEE_CIGRE.GFM.Components.EMTPTransformer);
instantiateModelTest(WSMExperimentsRound2.UnitCheckNegativeControl);
MOS
echo "-- p3.mos"; cat p3.mos
echo "-- kernel output"
"$WSM/bin/WSMKernelX" p3.mos 2>&1 | grep -v -E 'making a PIE|^\[|^FAILED|^"g\+\+|^/usr/bin/ld|^collect2|^ninja' | cut -c1-400 | head -60
cd "$P" || exit 1

echo; echo "=== P4 the external-function evaluator, through a logging compiler wrapper (probe only)"
W4="$P/p4"; mkdir -p "$W4/keep"; cd "$W4" || exit 1
cat > g++-log <<'WR'
#!/bin/sh
# probe only: log every compiler call, run the kit's g++-nopie, keep each linked output
echo "cwd=$(pwd) :: $*" >> "$PROBE_DIR/gxx_calls.txt"
/opt/openipsl-kit/bin/g++-nopie "$@"; rc=$?
out=""; prev=""
for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
case "$out" in *.o|"") ;; *) [ -f "$out" ] && cp "$out" "$PROBE_DIR/keep/" ;; esac
exit $rc
WR
chmod +x g++-log
printf '%s\n%s\n' "$WSM/L/Modelica 4.0.0" "$WSM/L/SystemModelerExtras" > ModelicaPath.txt
cat > p4.mos <<MOS
setStopOnError(false);
setTempDirectoryPath("$W4");
setCompilerPath("$W4/g++-log");
loadLibrary(Modelica);
loadFile("$PKG/package.mo");
buildModel(OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9, fileNamePrefix="$W4/SCRX9");
MOS
PROBE_DIR="$W4" "$WSM/bin/WSMKernelX" p4.mos 2>&1 | cat > kernel_out.txt; echo "kernel exit ${PIPESTATUS[0]}"
echo "-- every compiler call (cwd :: arguments)"; cat gxx_calls.txt
echo "-- kept outputs"; ls -la keep
echo "-- evaluator.exe: readelf -d"; readelf -d keep/evaluator.exe | grep -E 'NEEDED|RUNPATH|RPATH'
echo "-- evaluator.exe run directly, without LD_LIBRARY_PATH"; ( cd keep && env -u LD_LIBRARY_PATH timeout 5 ./evaluator.exe < /dev/null 2>&1 | head -3 )
echo "-- the kernel binary names LD_LIBRARY_PATH: $(strings "$WSM/SystemFiles/WSM/Binaries/Linux-x86-64/WSMKernelX" | grep -c '^LD_LIBRARY_PATH$') times"
echo "-- lib/linux64/libserializer.a: R_X86_64_32 relocations: $(readelf -r "$WSM/lib/linux64/libserializer.a" | grep -c R_X86_64_32)"
echo "-- g++ default PIE: $(/usr/bin/g++ -v 2>&1 | grep -o -- '--enable-default-pie')"
echo; echo "### done $(date '+%H:%M:%S')"
} 2>&1 | tee "$P/probes.txt"
mkdir -p "$OUT/diagnostics/probes"
rm -f "$OUT/diagnostics/probes/p2_log.txt"
cp "$P/probes.txt" "$P/p2_log.txt" "$P/p2_accepting.txt" "$OUT/diagnostics/probes/" 2>/dev/null
cp "$P/p3/p3.mos" "$P/p4/p4.mos" "$P/p4/gxx_calls.txt" "$P/p4/kernel_out.txt" "$OUT/diagnostics/probes/" 2>/dev/null
[ -f "$P/p3/p3.out.json" ] && cp "$P/p3/p3.out.json" "$OUT/diagnostics/probes/"
echo "copied to $OUT/diagnostics/probes"
