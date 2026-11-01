# OpenIPSL macOS (Apple Silicon) verification kit

Scripts, patches and recipes with which the IEEE/CIGRE DLL package of OpenIPSL (pull request #433, `b05fa044`) was
verified natively on an Apple Silicon Mac on 2026-10-31, so that the verification can be repeated. The record of that
run is `ARM_MACOS_VERIFICATION.md` in the records folder; this kit holds only what is needed to redo it. License: BSD
3-Clause (top-level `LICENSE`). No vendor software is included: System Modeler is Wolfram's, OpenModelica is built
from source (recipe below) or taken from the release assets of this repository (`arm-macos-2026-10-31`).

Status: first version, 2026-10-31. Companion of the Linux kit in the top folder of this repository (the macOS runners are
ports of its `tests/systemmodeler/wsm_run_linux.py` and `tests/openmodelica/omc_verify.py`; same run list, same CSV
contract, same metrics fields, so the three platforms compare run by run).

## What it needs

| Item | Used here |
|---|---|
| Mac | Mac mini, Apple M2 Pro, 32 GB, macOS 27.0.1 (26A434) during the runs, 27.2 afterwards |
| Xcode | 27.2 (27B52), Apple clang 21.0.0; `xcodebuild -version`, licence accepted |
| Homebrew | cmake 4.4.5, ninja 1.13.2, python@3.15 with numpy (`brew install numpy python@3.15`; `python3.15 -m pip install --user --break-system-packages matplotlib` for the figures); for the omc build also autoconf automake openjdk pkg-config make ccache flex bison boost libomp gettext libiconv |
| System Modeler | 15.0 [14], kernel `WSMKernelX --version` 15.0.0.4 (14.3 gave the same folder-lookup result); the standalone kernel only, `/Applications/SystemModeler.app/Contents/MacOS/WSMKernelX`; licence as installed (no MathLM needed for the kernel) |
| OpenModelica | none exists for arm64 macOS: build it (below) or unpack `omc-v1.27.1-cmake-arm64-macos.tar.xz` from the release assets into `om/` |
| Modelica Standard Library for omc | `Modelica 4.0.0+maint.om` at commit `96032134c36668898e1693e69bd9f81aa38de3dd` of `OpenModelica/OpenModelica-ModelicaStandardLibrary` (the entry of OpenModelica `v1.27.1`'s `libraries/index.json`), laid out as `omlibrary/{Modelica 4.0.0+maint.om, Complex 4.0.0+maint.om.mo, ModelicaServices 4.0.0+maint.om}`; release asset `msl-4.0.0+maint.om-96032134-omlibrary.tar.xz`. omc reads `OPENMODELICALIBRARY`, not `MODELICAPATH` |
| OpenIPSL | the commit under test, cloned to `OpenIPSL/`, with `patches/0001..0003` applied (`git am`) |
| Python for the scripts | `/opt/homebrew/bin/python3.15 -I` |

## Steps

1. Clone OpenIPSL, check out the commit, apply the patches:
   `git -C OpenIPSL am ../patches/*.patch` (0001 platform folders `aarch64-darwin`/`aarch64-linux`, 0002
   `-ffp-contract=off`, 0003 absolute install names and the `arm64-darwin -> aarch64-darwin` link).
2. Build and install the libraries (never inside a synced folder):
   ```
   cmake -S OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE -B build/ieee_cigre -G Ninja -DCMAKE_BUILD_TYPE=Release
   cmake --build build/ieee_cigre && ctest --test-dir build/ieee_cigre --output-on-failure && cmake --install build/ieee_cigre
   ```
   Result: `OpenIPSL/OpenIPSL/Resources/Library/aarch64-darwin/lib{SCRX9,GFM_GFL_IBR}.dylib` (arm64, absolute
   install names, no FMA instructions: `otool -tv ... | grep -c fmadd` must print 0) and the link `arm64-darwin`.
3. System Modeler, the 15 contract runs (one kernel at a time):
   `bash scripts/run_all_macos.sh OpenIPSL/OpenIPSL raw/systemmodeler/record --work build/wsm_runs`
   `wsm_run_macos.py` sets the kernel's compiler in the `.mos` (`setCompilerPath` to Xcode's clang++, SDK, arch
   arm64, os osx, version); without that a fresh kernel's `buildModel` returns `{false,"",""}` silently.
4. OpenModelica, all steps (env, checks, extras, 15 runs, timing x3, binding, compare, table):
   `OMC=<omc> WIN_RECORD=<Windows record>/openmodelica bash scripts/run_all_om_macos.sh OpenIPSL/OpenIPSL raw/openmodelica/record build/om_runs`
   (`run_all_om_macos.sh` exports `OPENMODELICALIBRARY=$HOME/arm-verify/om/libs/omlibrary` unless set.)
5. Comparison against the x64 records (needs `report/linux/compare_linux.py` next to the records, imported for the
   statistics functions):
   `python3.15 scripts/compare_arm.py --sm raw/systemmodeler/record --om raw/openmodelica/record --om-raw build/om_runs --win <report>/verification_round2 --linux <report>/linux --out raw/comparison_final`

## Building omc from source (what finally worked, five attempts; see the record's section 7.1)

```
git clone --branch v1.27.1 --depth 1 --recurse-submodules --shallow-submodules https://github.com/OpenModelica/OpenModelica.git om/OpenModelica
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/opt/flex/bin:/opt/homebrew/opt/bison/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
export SDKROOT=$(xcrun --sdk macosx --show-sdk-path)
cmake -S om/OpenModelica -B om/build_cmake -Wno-dev -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DOM_OMC_ENABLE_FORTRAN=OFF -DOM_OMC_ENABLE_OPTIMIZATION=OFF -DOM_OMC_ENABLE_MOO=OFF -DOM_OMC_ENABLE_COLPACK=OFF \
  -DOM_ENABLE_GUI_CLIENTS=OFF -DOM_USE_CCACHE=ON \
  -DCMAKE_PREFIX_PATH="/opt/homebrew/opt/libiconv;/opt/homebrew/opt/gettext;/opt/homebrew/opt/boost;/opt/homebrew/opt/flex;/opt/homebrew/opt/bison;/opt/homebrew/opt/openjdk;/opt/homebrew/opt/libomp;/opt/homebrew" \
  -DCMAKE_C_FLAGS="-I/opt/homebrew/opt/libomp/include" -DCMAKE_CXX_FLAGS="-I/opt/homebrew/opt/libomp/include" \
  -DCMAKE_EXE_LINKER_FLAGS="-L/opt/homebrew/opt/libomp/lib -lomp" -DCMAKE_SHARED_LINKER_FLAGS="-L/opt/homebrew/opt/libomp/lib -lomp" -DCMAKE_MODULE_LINKER_FLAGS="-L/opt/homebrew/opt/libomp/lib -lomp" \
  -DCMAKE_INSTALL_PREFIX=$PWD/om/install
cmake --build om/build_cmake --parallel 10 --target install
```
ColPack is off because its SMPGC sources need `omp.h` and `std::random_shuffle`, which Apple clang 21 and its libc++
no longer provide; the C++ runtime's Peer solver needs Homebrew libomp's header and `-lomp`. About ten minutes on
ten cores. The result is `om/install/bin/omc`, `v1.27.1-cmake`, arm64.

## Traps measured (details and evidence in the record)

1. Clang contracts `a*b+c` into fused multiply-add on arm64 by default; the GFM model's start-up turns that into a
   different trajectory. `-ffp-contract=off` (patch 0002) is mandatory for agreement with x64.
2. System Modeler resolves `LibraryDirectory` only to `aarch64-darwin`; OpenModelica searches the base folder,
   `arm64-darwin` and `darwin64`. Patch 0003 serves both.
3. Neither tool's executable has an rpath to the library folder; `@rpath` install names fail at run time. Patch 0003
   gives absolute install names, so macOS libraries are built on each machine and never shipped.
4. The standalone kernel needs the compiler configuration in the `.mos` on a fresh macOS (see step 3).
5. `gh`, `omc` and the kernel print their versions in seconds: record them per run (System Modeler was upgraded from
   14.3 to 15.0 in the middle of the first session).
