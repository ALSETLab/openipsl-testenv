#!/usr/bin/env bash
# Smoke test 40 (normal user): System Modeler's standalone kernel (WSMKernelX, System Modeler's own licence)
# builds the SCRX9 DLL test with the shipped libSCRX9.so; the built executable simulates it from the .sim;
# shows how the executable finds the library (.sim ExternalLibraries, RUNPATH, ldd).
# Usage: bash tests/smoke/40_systemmodeler.sh <package dir .../OpenIPSL> [<site.env>]
# WSM_CXX=/opt/openipsl-kit/bin/g++-nopie adds setCompilerPath(...) to the .mos (see provision/30_systemmodeler.sh).
set -uo pipefail
PKG="$(cd "${1:?usage: 40_systemmodeler.sh <package dir .../OpenIPSL>}" && pwd)"
KIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
. "${2:-$KIT_DIR/site.env}"
MODEL=OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9
SHORT=SCRX9
W="$HOME/cigre_verify/smoke/systemmodeler${WSM_CXX:+_$(basename "$WSM_CXX")}"
rm -rf "$W"; mkdir -p "$W"; cd "$W" || exit 1
printf '%s\n%s\n' "$WSM_TARGET/L/Modelica 4.0.0" "$WSM_TARGET/L/SystemModelerExtras" > ModelicaPath.txt
cat > build.mos <<EOF
setStopOnError(false);
setTempDirectoryPath("$W");
${WSM_CXX:+setCompilerPath(\"$WSM_CXX\");}
loadLibrary(Modelica);
loadFile("$PKG/package.mo");
buildModel($MODEL, fileNamePrefix="$W/$SHORT");
EOF
t0=$(date +%s)
"$WSM_TARGET/bin/WSMKernelX" build.mos > kernel.log 2>&1
echo "WSMKernelX exit $?, $(( $(date +%s) - t0 )) s"
grep -i -E 'Resolved|error|warning|licen|built|success|FAILED|PIE' kernel.log | head -30
echo "external-function evaluator link failures: $(grep -c 'can not be used when making a PIE object' kernel.log)"
ls -la "$W" | grep -E "$SHORT" | head
exe="$(ls -1 "$W/$SHORT" "$W/$SHORT.exe" 2>/dev/null | head -n1)"
[ -n "$exe" ] || { echo "no executable built"; tail -n 40 kernel.log; exit 1; }
echo "== .sim external libraries"
grep -i -E 'ExternalLibrar|<Library' "$W/$SHORT.sim" | head
echo "== how the executable finds libSCRX9.so"
readelf -d "$exe" | grep -E 'NEEDED|RUNPATH|RPATH'
ldd "$exe" | grep -E 'SCRX9|not found'
libdir="$(grep -o -E 'path="[^"]*linux64[^"]*"' "$W/$SHORT.sim" | head -n1 | sed 's/path="//; s/"$//')"
echo "== run the executable (LD_LIBRARY_PATH=${libdir:-unset})"
t0=$(date +%s)
# stdout and stderr go to separate files: with "> run.log 2>&1" the executable's stdout overwrote its stderr text
# (measured by the System Modeler verification run, tests/systemmodeler/probes.sh P5).
LD_LIBRARY_PATH="${libdir}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$exe" -f "$W/$SHORT.sim" -r "$W/$SHORT.mat" > run.out 2> run.err
echo "executable exit $?, $(( $(date +%s) - t0 )) s"
echo "-- stdout (last 15 lines)"; tail -n 15 run.out
echo "-- stderr (last 15 lines)"; tail -n 15 run.err
[ -s "$W/$SHORT.mat" ]
