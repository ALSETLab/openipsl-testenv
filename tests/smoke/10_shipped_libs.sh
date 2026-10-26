#!/usr/bin/env bash
# Smoke test 10 (normal user): the package's own C tests, compiled here and linked against the SHIPPED
# Resources/Library/linux64/lib<Name>.so (not a rebuild), so the shipped binaries are exercised on this
# distro's glibc. Mirrors the CMake project's ctest: adapter_test_<Name>, layout_test_<Name>,
# two_libraries_test_{scrx9_first,gfm_first}. Also prints the ELF facts a reviewer asks for.
# Usage: bash tests/smoke/10_shipped_libs.sh <exported package dir .../OpenIPSL>
set -uo pipefail
PKG="${1:?usage: 10_shipped_libs.sh <package dir .../OpenIPSL>}"
SRC="$PKG/Resources/C-Sources/IEEE_CIGRE"
LIB="$PKG/Resources/Library/linux64"
OUT="$HOME/cigre_verify/smoke/shipped_libs"
rm -rf "$OUT"; mkdir -p "$OUT"
W="-std=c11 -O2 -Wall -Wextra"
ok=0; bad=0
run() { local name="$1"; shift; if "$@" > "$OUT/$name.log" 2>&1; then echo "PASS  $name"; ok=$((ok+1)); else echo "FAIL  $name (exit $?, log $OUT/$name.log)"; bad=$((bad+1)); fi; }

echo "system: $(. /etc/os-release && echo "$PRETTY_NAME"), glibc $(ldd --version | head -n1 | awk '{print $NF}'), $(gcc --version | head -n1)"
for so in "$LIB"/lib*.so; do
  echo "== $(basename "$so"): sha256 $(sha256sum "$so" | cut -c1-16)..., $(readelf -d "$so" | grep -E 'SONAME|SYMBOLIC|RUNPATH|RPATH' | sed 's/^ *0x[0-9a-f]* *//' | tr -s ' ' | tr '\n' ';')"
  echo "   GLIBC versions needed: $(objdump -T "$so" | grep -oE 'GLIBC_[0-9.]+' | sort -u -V | tr '\n' ' ')"
done

for N in SCRX9 GFM_GFL_IBR; do
  gcc $W -I"$SRC/include" -DOIPSL_PREFIX=$N -DIEEE_CIGRE_IMPORT -DOIPSL_TEST_$N "$SRC/test/adapter_test.c" \
      -L"$LIB" -l$N -Wl,-rpath,"$LIB" -lm -o "$OUT/adapter_test_$N" || { echo "FAIL  build adapter_test_$N"; bad=$((bad+1)); continue; }
  run "adapter_test_$N" "$OUT/adapter_test_$N"
  gcc $W -I"$SRC/include" -I"$SRC/src" -DOIPSL_PREFIX=$N -DOIPSL_TEST_$N "$SRC/test/layout_test.c" \
      -L"$LIB" -l$N -Wl,-rpath,"$LIB" -lm -o "$OUT/layout_test_$N" || { echo "FAIL  build layout_test_$N"; bad=$((bad+1)); continue; }
  run "layout_test_$N" "$OUT/layout_test_$N"
done
for order in scrx9_first gfm_first; do
  if [ $order = scrx9_first ]; then libs="-lSCRX9 -lGFM_GFL_IBR"; else libs="-lGFM_GFL_IBR -lSCRX9"; fi
  # shellcheck disable=SC2086
  gcc $W -I"$SRC/include" -DIEEE_CIGRE_IMPORT "$SRC/test/two_libraries_test.c" -L"$LIB" $libs -Wl,-rpath,"$LIB" -lm \
      -o "$OUT/two_libraries_test_$order" || { echo "FAIL  build two_libraries_test_$order"; bad=$((bad+1)); continue; }
  run "two_libraries_test_$order" "$OUT/two_libraries_test_$order"
done
for f in "$OUT"/*.log; do echo "-- $(basename "$f"): $(grep -iE 'checks|failed|pass' "$f" | tail -n1)"; done
echo "passed $ok, failed $bad"
[ "$bad" -eq 0 ]
