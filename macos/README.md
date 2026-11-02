# OpenIPSL macOS (Apple Silicon) verification kit

Scripts and recipes with which the IEEE/CIGRE DLL package of OpenIPSL (pull request #433) was verified natively on an
Apple Silicon Mac, so that the verification can be repeated. Since `43f6efd7` the pull request ships the macOS libraries
itself, as static archives `lib{SCRX9,GFM_GFL_IBR}.a` in `Resources/Library/aarch64-darwin` and `arm64-darwin`; this
kit runs both tools against them as shipped. The record of the first run (2026-10-31, `b05fa044` with the patches of
`patches/`) is [`ARM_MACOS_VERIFICATION.md`](ARM_MACOS_VERIFICATION.md) in this folder. License: BSD 3-Clause
(top-level `LICENSE`). No vendor software is included: System Modeler is Wolfram's, OpenModelica is built from source
(recipe below).

Status: first version 2026-10-31; updated 2026-11-01 for the shipped archives (rerun that day: System Modeler 13 of 15
and OpenModelica 15 of 15, result files byte-identical to those of 2026-10-31, no environment variable set). Companion of the Linux kit in the top folder of this repository (the macOS runners are
ports of its `tests/systemmodeler/wsm_run_linux.py` and `tests/openmodelica/omc_verify.py`; same run list, same CSV
contract, same metrics fields, so the three platforms compare run by run).

## What it needs

| Item | Used here |
|---|---|
| Mac | Mac mini, Apple M2 Pro, 32 GB, macOS 27.0.1 (26A434) during the runs, 27.2 afterwards |
| Xcode | 27.2 (27B52), Apple clang 21.0.0; `xcodebuild -version`, licence accepted |
| Homebrew | cmake 4.4.5, ninja 1.13.2, python@3.15 with numpy (`brew install numpy python@3.15`; `python3.15 -m pip install --user --break-system-packages matplotlib` for the figures); for the omc build also autoconf automake openjdk pkg-config make ccache flex bison boost libomp gettext libiconv |
| System Modeler | 15.0 [14], kernel `WSMKernelX --version` 15.0.0.4 (14.3 gave the same folder-lookup result); the standalone kernel only, `/Applications/SystemModeler.app/Contents/MacOS/WSMKernelX`; licence as installed (no MathLM needed for the kernel) |
| OpenModelica | none exists for arm64 macOS: build it (below) into `om/install` |
| Modelica Standard Library for omc | `Modelica 4.0.0+maint.om` at commit `96032134c36668898e1693e69bd9f81aa38de3dd` of `OpenModelica/OpenModelica-ModelicaStandardLibrary` (the entry of OpenModelica `v1.27.1`'s `libraries/index.json`), laid out as `omlibrary/{Modelica 4.0.0+maint.om, Complex 4.0.0+maint.om.mo, ModelicaServices 4.0.0+maint.om}`; release asset `msl-4.0.0+maint.om-96032134-omlibrary.tar.xz`. omc reads `OPENMODELICALIBRARY`, not `MODELICAPATH` |
| OpenIPSL | the commit under test, cloned to `OpenIPSL/`: `43f6efd7` or later of `feature/ieee-cigre-dll` (or master once #433 is merged), used as it is. Only to repeat the run of 2026-10-31: `b05fa044` with `patches/0001..0003` applied (`git am`) |
| Python for the scripts | `/opt/homebrew/bin/python3.15 -I` |

## Steps

1. Clone OpenIPSL and check out the commit (no patches). The libraries are the shipped files
   `OpenIPSL/OpenIPSL/Resources/Library/aarch64-darwin/lib{SCRX9,GFM_GFL_IBR}.a`, with identical copies in
   `arm64-darwin`; their sizes and SHA-256 are in `Resources/Library/README.md` (`shasum -a 256`).
2. Optional, the C tests and the reproducibility check (never inside a synced folder; Unix Makefiles, the generator of
   the shipped archives):
   ```
   cmake -S OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE -B build/ieee_cigre -DCMAKE_BUILD_TYPE=Release
   cmake --build build/ieee_cigre && ctest --test-dir build/ieee_cigre --output-on-failure && cmake --install build/ieee_cigre
   git -C OpenIPSL status --short OpenIPSL/Resources/Library
   ```
   ctest runs 8 tests (on macOS also `two_archives_test`, which links both archives in both orders). The install
   rewrites the archives in both folders; with the same tool chain they are bit-identical (measured with Xcode 27.2,
   Apple clang 21.0.0, CMake 4.4.5), so `git status` prints nothing. Another Xcode may give other bytes; the runs below
   then use the rebuilt archives. No FMA instructions: `otool -tv ... | grep -c fmadd` prints 0.
3. System Modeler, the 15 contract runs (one kernel at a time):
   `bash scripts/run_all_macos.sh OpenIPSL/OpenIPSL raw/systemmodeler/record --work build/wsm_runs --no-dyld-path`
   (`--no-dyld-path` runs the executable without `DYLD_LIBRARY_PATH`: the archives are linked into it. Without the
   flag the runner sets the path as on Linux, which the archives do not need.)
   `wsm_run_macos.py` sets the kernel's compiler in the `.mos` (`setCompilerPath` to Xcode's clang++, SDK, arch
   arm64, os osx, version); without that a fresh kernel's `buildModel` returns `{false,"",""}` silently.
4. OpenModelica, all steps (env, checks, extras, 15 runs, timing x3, binding, compare, table):
   `OMC=<omc> WIN_RECORD=<Windows record>/openmodelica bash scripts/run_all_om_macos.sh OpenIPSL/OpenIPSL raw/openmodelica/record build/om_runs`
   (`run_all_om_macos.sh` exports `OPENMODELICALIBRARY=$HOME/arm-verify/om/libs/omlibrary` unless set.)
5. Comparison against the x64 records. It needs the Windows round-2 record (`verification_record_1244ae93.zip`,
   attached to the comment of 2026-10-25 on OpenIPSL#433) and the Linux record with its `compare_linux.py`, whose
   statistics functions it imports (`../linux_record/LINUX_VERIFICATION.md` describes it; the CSV files are in the project's
   records, on request):
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
   different trajectory. `-ffp-contract=off` is mandatory for agreement with x64 (patch 0002, now in #433 as
   `34985981`).
2. System Modeler resolves `LibraryDirectory` only to `aarch64-darwin`; OpenModelica searches the base folder,
   `arm64-darwin` and `darwin64`. #433 ships the same archives in both folders, as copies (a symbolic link would not
   survive a checkout on Windows).
3. Neither tool's executable has an rpath to the library folder, and OpenModelica starts it through `/bin/sh`, which
   drops `DYLD_LIBRARY_PATH`: a dylib with an `@rpath` install name fails at launch, one with an absolute install name
   (patch 0003) loads only on the machine that built it. Static archives are linked into the executable and need
   nothing at run time; inside each the standard's `Model_*` entry points are renamed `<Name>_Model_*`, so two
   archives link into one model (#433, `6165c7f0`, which replaces patch 0003).
4. The standalone kernel needs the compiler configuration in the `.mos` on a fresh macOS (see step 3).
5. `gh`, `omc` and the kernel print their versions in seconds: record them per run (System Modeler was upgraded from
   14.3 to 15.0 in the middle of the first session).
