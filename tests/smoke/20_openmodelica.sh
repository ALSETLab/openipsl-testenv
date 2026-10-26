#!/usr/bin/env bash
# Smoke test 20 (normal user): OpenModelica builds and simulates the SCRX9 DLL test with the shipped
# libSCRX9.so, and shows how the simulation executable finds the library (link flags, RUNPATH, ldd).
# Usage: bash tests/smoke/20_openmodelica.sh <package dir .../OpenIPSL>
set -uo pipefail
PKG="$(cd "${1:?usage: 20_openmodelica.sh <package dir .../OpenIPSL>}" && pwd)"
MODEL=OpenIPSL.Tests.Controls.IEEE_CIGRE.SCRX9.SCRX9
W="$HOME/cigre_verify/smoke/openmodelica"
rm -rf "$W"; mkdir -p "$W"; cd "$W" || exit 1
cat > smoke.mos <<EOF
print("OMC_VERSION " + getVersion() + "\n");
okm := loadModel(Modelica, {"4.0.0"}, requireExactVersion=true);
print("MSL_LOADED " + String(okm) + " " + getVersion(Modelica) + "\n");
print(getErrorString());
okl := loadFile("$PKG/package.mo");
print("LIB_LOADED " + String(okl) + "\n");
print(getErrorString());
r := simulate($MODEL, startTime=0, stopTime=10, numberOfIntervals=2000, tolerance=1e-06, method="dassl",
  outputFormat="mat", variableFilter="time|sCRX9\\\\.EFD|gENROU\\\\.w");
print(r.resultFile + "\n" + r.messages + "\n");
print(getErrorString());
print("EFD_0 " + String(val(sCRX9.EFD, 0.0, "${MODEL}_res.mat")) + "\n");
print("EFD_10 " + String(val(sCRX9.EFD, 10.0, "${MODEL}_res.mat")) + "\n");
EOF
t0=$(date +%s.%N)
omc smoke.mos > omc.log 2>&1
echo "omc exit $?, $(echo "$(date +%s.%N) - $t0" | bc 2>/dev/null || true) s"
grep -E "OMC_VERSION|MSL_LOADED|LIB_LOADED|EFD_|Error|error|Warning|SimulationResult|LOG_SUCCESS|The simulation finished" omc.log | head -30
echo "== how the executable finds libSCRX9.so"
grep -o -E -- '-L"?[^ "]*linux64[^ "]*"?|-Wl,-rpath=?"?[^ "]*"?|-lSCRX9' "$MODEL.makefile" 2>/dev/null | sort -u
readelf -d "$MODEL" 2>/dev/null | grep -E 'NEEDED.*SCRX9|RUNPATH|RPATH'
ldd "$MODEL" 2>/dev/null | grep -E 'SCRX9|not found'
grep -q "EFD_10" omc.log && ! grep -q "not found" <(ldd "$MODEL" 2>/dev/null)
