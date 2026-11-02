*Copy of the project's ARM macOS verification record (2026-10-31), placed here when the kit was made public on 2026-11-01. Since then OpenIPSL#433 ships static archives instead of the per-machine dylibs described here (see this folder's README). Files it names outside this repository are in the project's records.*

# ARM macOS (Apple Silicon) verification of the IEEE/CIGRE DLL package (OpenIPSL #433, `b05fa044`)

Date: 2026-10-31, 17:38 to 18:50 local. Machine: Mac mini, Apple M2 Pro (10 cores), 32 GB, macOS 27.0.1 (26A434).
Session: Claude Fable 5.1 (sub-session of the ARM verification lead), working folder `~/arm-verify/` on the Mac.
Package under test: OpenIPSL branch `feature/ieee-cigre-dll`, head `b05fa04440809291d61f13045f8586d186613f66`
(pull request #433), cloned to `~/arm-verify/OpenIPSL/`, plus three local commits on the branch `arm-platform-folders`
(sections 2, 3 and 11 D.1; patches `0001` to `0003` in `~/arm-verify/patches/`; nothing pushed). The x64 references are the Windows round-2
record (`records/report/verification_round2/`) and the Linux x86_64 record (`records/report/linux/`), read only.
Every number below is read from `raw/comparison_final/comparison_arm.json` (written by `scripts/compare_arm.py`,
which imports the statistics functions of `report/linux/compare_linux.py`) or from a file named in the sentence.
Paths are relative to `~/arm-verify/` unless absolute.

## TL;DR

I built the IEEE/CIGRE libraries natively on Apple Silicon and ran the 15 contract runs in System Modeler 15.0 and in
an OpenModelica 1.27.1 compiled from source: with one added compiler flag, both tools reproduce their x64 results at the
CSV print floor (the largest difference, 2.0e-9 relative, is GFL_Fault's start-up, the same place and size as Linux
against Windows), with equal event counts. Without that flag, clang's default fused multiply-add on arm64 makes the
GFM inverter runs visibly different (P off by 2.6 Sbase), and the two tools disagree on the platform folder name on
macOS: System Modeler searches only `aarch64-darwin`, OpenModelica only `arm64-darwin`, `darwin64` and the base folder.
Luigi decided D.1 on 2026-10-31 (install locally into both folders, ship no macOS binaries; commit `54f983e7`,
verified in both tools without environment variables); nothing is pushed; D.2, D.4, D.6 and D.7 are still open.

## Key points

- **The CMake platform change (D.1 ARM) builds and installs into `aarch64-darwin`** (patch 0001, commit `f457b90f`):
  Release build with Apple clang 21.0.0, 6 of 6 C tests pass, two arm64 `.dylib` files of 51,728 and 68,392 bytes,
  each depending on `/usr/lib/libSystem.B.dylib` only, the 12 expected exports. The Apple toolchain adds no warning of
  its own beyond gcc's: 121 `-Wunused-variable` in the two vendor model sources, 2 `-Wunused-parameter`
  (`Model_Terminate`), and 2 `-Wunknown-warning-option` for the gcc-only pragma `-Wmaybe-uninitialized` in
  `test/layout_test.c`. The adapter is warning-free.
- **Fused multiply-add changes the GFM results (the main technical finding; patch 0002, commit `18e920d1`).** With the
  default build (clang contracts `a*b+c` into FMA on arm64, 75 such instructions in `libGFM_GFL_IBR.dylib`, 5 in
  `libSCRX9.dylib`), System Modeler's GFM runs depart from the x64 results from the first DLL sample: `out[6]` (Iqref)
  off by 0.38 pu at 5.9 ms, P (`out[11]`) by up to 26 MW on the 10 MVA base in the first 0.4 s of GFL_POCFault,
  GFL_FrequencyStep, GFL_VoltageStep and GFM_EMTPFull, one to three extra current-zero state events, and 2.5e-3 of
  Sbase in GFL_PowerRamp (the GFL_FaultPSCAD parameter set, SCRX9 and the network-only tests were unaffected). With
  `-ffp-contract=off` the same runs equal Windows to 2.0e-9 relative (GFL_Fault `out[6]` at 0.1999 s, the known
  start-up amplification) and every other run to the CSV floor (at most 1.5e-11), with identical counters. The
  optimisation level is not the cause (`-O0` still contracts and still differs; `-O0 -ffp-contract=off` agrees).
- **System Modeler** (15.0 [14], kernel 15.0.0.4, standalone kernel route as on Linux): 13 of 15 runs ok, the same two
  native-SCRX build failures as on both x64 platforms ("Variables have `start` values that are determined in the same
  block of equations as the variables themselves"). Counters equal in 51 of 52 fields (DASSL's function evaluations in
  GFL_PowerRamp: 59,031,922 against 59,032,219 on Windows and 59,031,817 on Linux, with the same events and output
  points). Simulation wall time ARM over Windows 0.75 to 1.53 (median 0.88), ARM over Linux 1.42 to 2.57 (median
  2.19); translation 0.29 to 0.74 of Windows'. Settled values: no flag (none above 1e-3 relative against either x64
  platform).
- **System Modeler's folder lookup on Apple Silicon: `aarch64-darwin`, then the base folder, nothing else.** With the
  libraries only in `aarch64-darwin` or in both `aarch64-darwin` and `darwin64`, the build and the run succeed and the
  `.sim` records `.../Resources/Library/aarch64-darwin`; with them only in `darwin64`, only in `arm64-darwin` or
  absent, the kernel's external-function evaluator fails to link twice per model (`ld: library 'SCRX9' not found`,
  `-L<pkg>/Resources/Library` only) and the build stops. Measured with both System Modeler 14.3 and 15.0 (section 4).
- **OpenModelica's folder lookup is different: `Resources/Library/`, `arm64-darwin` and `darwin64`, never
  `aarch64-darwin`.** `OPENMODELICA_SPEC_PLATFORM` is `${CMAKE_SYSTEM_PROCESSOR}-${OMC_TARGET_SYSTEM_NAME}` in
  `OMCompiler/Compiler/runtime/CMakeLists.txt:176`, and Apple's CMake processor name is `arm64`. With x86-64 binaries in
  `darwin64` (what a package built on an Intel Mac would ship) the arm64 omc tries them and fails: `ld: warning:
  ignoring file '.../darwin64/libSCRX9.dylib': found architecture 'x86_64', required architecture 'arm64'`.
- **Neither tool's executable finds the `.dylib` at run time by itself.** The CMake default install name is
  `@rpath/lib<Name>.dylib`; System Modeler's executable has no `LC_RPATH` at all, OpenModelica's only its own
  `lib/omc` and `lib`. Run outside the tool, System Modeler's executable aborts with "Library not loaded:
  @rpath/libSCRX9.dylib, Reason: no LC_RPATH's found" (the runner sets `DYLD_LIBRARY_PATH`, as the Linux runner sets
  `LD_LIBRARY_PATH`); OpenModelica's own `simulate()` aborts the same way, and `DYLD_LIBRARY_PATH` does not reach it
  because omc starts the executable through `/bin/sh`, a system binary that drops `DYLD_*`. The OpenModelica runs
  therefore use libraries built with an absolute install name (`-DCMAKE_INSTALL_NAME_DIR=<folder>`; same code, the
  disassembly is identical), which both tools load without any environment variable.
- **OpenModelica had to be built from source** (no arm64 macOS binary exists). Tag `v1.27.1` (`4a7248c1`,
  2026-09-06), CMake build with Apple clang, Fortran, optimisation and GUI clients off; five configure attempts were
  needed (section 7): the graph-colouring library ColPack does not compile with Apple clang 21 (`omp.h` missing, then
  `std::random_shuffle` gone from libc++), so it is disabled (`OM_OMC_ENABLE_COLPACK=OFF`), and the C++ runtime's Peer
  solver needs Homebrew's libomp headers and `-lomp`. The Modelica Standard Library is OpenModelica's own
  `Modelica 4.0.0+maint.om` at the commit named in `v1.27.1`'s `libraries/index.json` (`96032134`).
- **OpenModelica results: 15 of 15 runs ok** (it builds master's native SCRX, as on x64), `checkModel` and
  `--unitChecking` 51 of 51 classes without a message, `translateModel` 13 of 13. Against Windows round 2 the largest
  difference is again GFL_Fault's `out[6]` at 0.1999 s, 4.6e-9 relative (9.9e-9 pu; the Linux record's own value was
  4.5e-9), every other run at the 10-digit CSV floor (at most 9.2e-10); against Linux every run is at the floor, GFL_Fault
  included (4.2e-10). Counters equal in 68 of 68 fields against both platforms (DASSL's 7,583,152 steps and 9,938,486
  function evaluations in GFL_PowerRamp included). SCRX9 DLL against native SCRX: DLL minus native EFD 1.219e-6 pu
  before the fault and 0.039914 pu at the 5 ms samples after it, 7.47e-5 at 10 s; the SCRX9 test against the native
  test before 2 s: EFD 4.54e-6, GEN1.v 3.04e-7, speed 1.45e-7; the same computation on the Windows and Linux
  OpenModelica CSVs gives the same numbers to the printed digits. Simulation wall time ARM over Windows 1.10 to 2.09
  (median 1.34), over Linux 1.14 to 2.73 (median 1.52); translation about twice Windows' (omc's front end), compile
  0.33 of Windows'. The FMA control in OpenModelica (`raw/openmodelica/record_fma_default/`, the unpatched `b05fa044`
  build): GFL_Fault `out[6]` 0.18 at 0.0059 s and GFL_VoltageStep `out[11]` 2.57 Sbase at 0.3931 s, the same numbers as
  System Modeler's, so the effect is in the library, not in a tool.
- **Cross-tool on ARM equals cross-tool on x64.** OpenModelica minus System Modeler, worst relative difference of the
  key signals per run (OpenModelica rebuilt from its raw result with the round-2 instant rule, as on x64): identical to
  the Windows and Linux numbers to the three printed digits in every one of the 13 runs both tools finish, for example
  GFL_Fault 5.591e-7, GFL_VoltageStep 3.409e-8, GFM_EMTPFull 5.047e-2, SCRX9 DASSL 3.659e-5. Settled values: no flag;
  the largest relative change of any settled value against x64 is 4.0e-12 (System Modeler) and 5.9e-13 (OpenModelica).
- **D.1 implemented (commit `54f983e7`, patch `0003`).** On Apple Silicon the CMake install now gives each library an
  absolute install name (`INSTALL_NAME_DIR` = the installed folder) and creates the link
  `Resources/Library/arm64-darwin -> aarch64-darwin`. Measured on the checkout: System Modeler builds and runs SCRX9
  with no `DYLD_LIBRARY_PATH` (dyld loads `.../aarch64-darwin/libSCRX9.dylib` by its install name), and omc links
  through `arm64-darwin` and simulates SCRX9 (10 s) and GFL_Fault (0.5 s) with no environment variable
  (`raw/systemmodeler/d1_check/`, `raw/openmodelica/d1_check/`). macOS libraries are built on the user's machine and
  not shipped (the two folders stay untracked).
- **System Modeler changed from 14.3 to 15.0 while the session ran.** `/Applications/SystemModeler.app` reported
  14.3 [8] (kernel 14.3.0.3) from 17:38 to 17:58 and 15.0 [14] (kernel 15.0.0.4) from 18:02 on; Luigi installed
  version 15 on the Mac at that time (D.3, answered). Every run of the record (both record sets, the FMA experiment, the controls) used
  15.0.0.4; only the first folder-lookup experiment used 14.3.0.3 and it was repeated with 15.0.0.4 with the same
  result (D.3 asks Luigi to confirm the installation).
- **Two kernel traps on macOS.** (1) The fresh 14.3 kernel had an empty compiler path (`getCompilerConf()`: "Compiler
  path:" blank) and `buildModel` returned `{false,"",""}` with no message after "Step 1 of 4"; `setCompilerPath(<Xcode
  clang++>)`, `setCompilerSDKPath`, `setCompilerTargetArch("arm64")`, `setCompilerTargetOS("osx")` and
  `setCompilerVersion` in the `.mos` fix it, and the kernel then persists the configuration in
  `~/Library/Preferences/com.wolfram.SystemModeler150002.plist` (a file that did not exist before 18:12). (2) The
  `.sim`'s `<ExternalLibraries>` path is the only record of the folder the kernel chose; the runner reads it.

## 1. Environment (source: `raw/env/environment.txt`, the metrics files, the build logs)

| Item | Value |
|---|---|
| Machine | Mac mini, Apple M2 Pro, 10 cores, 32 GB; `uname -a`: Darwin Mac.lan 27.0.0, xnu-13432.1.9~1/RELEASE_ARM64_T6020, arm64 |
| macOS | 27.0.1, build 26A434 (`sw_vers`) |
| Rosetta 2 | not installed (`arch -x86_64 /usr/bin/true`: "Bad CPU type in executable"), so no x86-64 control run on this Mac |
| Xcode / clang | Xcode 27.2 (27B52), SDK MacOSX27.2; Apple clang version 21.0.0 (clang-2100.4.1.1), target arm64-apple-darwin27.0.0 |
| CMake, Ninja, Homebrew | cmake 4.4.5, ninja 1.13.2, Homebrew 7.0.11 |
| Python | Homebrew python 3.15.2 with numpy 2.5.4 (matplotlib 3.11.2 in the user site for the figures); the system python 3.9.6 has no numpy |
| git, gh | git 2.54.0 (Apple Git-157); gh 2.103.3 (not logged in; not needed) |
| OpenIPSL | `b05fa04440809291d61f13045f8586d186613f66` (feature/ieee-cigre-dll, 2026-10-28), branch `arm-platform-folders` with `f457b90f` (platform folders) and `18e920d1` (`-ffp-contract=off`), both local |
| Libraries built here | `OpenIPSL/Resources/Library/aarch64-darwin/libSCRX9.dylib` (51,728 bytes, SHA-256 `6edec9777dc86296f18023b5e674eb983b162066cedf00dc10bb6b5d8a8ad24b`) and `libGFM_GFL_IBR.dylib` (68,392 bytes, `ff776a2b6f8d77c223b678ceeef44fb5b73da3e3c5e8584bf39a9edd3ecec035`), Release, `-ffp-contract=off`. The default-contraction build of the same sources: `ef92d244...` and `1d864820...` (same sizes) |
| Compile flags | `-O3 -DNDEBUG -std=c11 -arch arm64 -fPIC -fvisibility=hidden -Wall -Wextra -ffp-contract=off -DOIPSL_PREFIX=<Name>` (`raw/build/compile_commands_nofma.json`); link `-dynamiclib`, install name `@rpath/lib<Name>.dylib`, `LC_BUILD_VERSION` platform macOS, minos 27.0 (the deployment target defaults to the host) |
| System Modeler | until 17:58: 14.3 [8], `WSMKernelX --version` 14.3.0.3; from 18:02: 15.0 [14], 15.0.0.4. Universal binary, "Kernel is running natively on Apple ARM". Standalone kernel route (`Contents/MacOS/WSMKernelX` with a `.mos`), as the Linux record; compiler `setCompilerPath(/Applications/Xcode.app/.../clang++)`, SDK MacOSX27.2, arch arm64, os osx, version 21.0.0. MSL 4.0.0 from `Contents/L/Modelica 4.0.0`. Licence: works without the campus MathLM server (no question needed) |
| OpenModelica | `v1.27.1-cmake`, built from tag `v1.27.1` = `4a7248c1ab64f4205eb4222b6b009bbf2b0df383` (2026-09-06), arm64 Mach-O, `~/arm-verify/om/install/`; options in section 7; omc's C compiler `clang` (Apple clang 21.0.0), `CFLAGS -DOM_HAVE_PTHREADS -fPIC`; MSL `Modelica 4.0.0+maint.om` (OpenModelica/OpenModelica-ModelicaStandardLibrary `96032134c36668898e1693e69bd9f81aa38de3dd`, the entry of `libraries/index.json` at `v1.27.1`), `OPENMODELICALIBRARY=~/arm-verify/om/libs/omlibrary` |
| x64 references | Windows round 2 (System Modeler 15.0 kernel 15.0.0.4 on Windows 11, MSVC; OpenModelica v1.27.1 64-bit) and Linux x86_64 (Ubuntu 24.04.5 under WSL2, System Modeler 15.0.0.4 with g++ 13.3 through the kit's `g++-nopie`, OpenModelica 1.27.1 with clang 18.1.3), the records in `records/report/` |
| Dymola | not installed on the Mac (and no Apple Silicon Dymola exists); out of scope here |

How to reproduce (all scripts in `scripts/`, all runs made from `~/arm-verify/`):

```
cmake -S OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE -B build/ieee_cigre -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/ieee_cigre && ctest --test-dir build/ieee_cigre && cmake --install build/ieee_cigre
bash scripts/run_all_macos.sh pkg/record/OpenIPSL raw/systemmodeler/record --work build/wsm_runs
WIN_RECORD=$PWD/records/report/verification_round2/openmodelica bash scripts/run_all_om_macos.sh pkg/record_om/OpenIPSL raw/openmodelica/record build/om_runs
python3.15 scripts/compare_arm.py --sm raw/systemmodeler/record --om raw/openmodelica/record --sm-lookup raw/systemmodeler/lookup --win records/report/verification_round2 --linux records/report/linux --out raw/comparison_final
```

`pkg/<name>/OpenIPSL` are copies of the checkout with the libraries in the folders named by `<name>` (section 4);
`pkg/record` is the checkout as installed (`aarch64-darwin`), `pkg/record_om` the same with the libraries also in
`arm64-darwin` and with absolute install names (section 5).

## 2. The CMake change (step 2) and the build

`OpenIPSL/Resources/C-Sources/IEEE_CIGRE/CMakeLists.txt` mapped the platform folder by operating system and pointer
size only (`win32|win64|linux32|linux64|darwin64`), so on this Mac the unpatched `b05fa044` configures
"IEEE/CIGRE libraries install into .../Library/darwin64" (measured, `build/ieee_cigre_b05_unpatched`). Commit
`f457b90f` (patch `patches/0001-...aarch64-linux-and-...patch`, 9 insertions, 3 deletions) adds one branch:
`CMAKE_SYSTEM_PROCESSOR` matching `aarch64|arm64|ARM64` on Linux or Darwin selects `aarch64-<lower-case os>`, so
`aarch64-darwin` here and `aarch64-linux` on the Raspberry Pi; x86 keeps the five names. Windows on ARM is left as
it was (out of scope). Two limits worth knowing for the follow-up pull request: a cross build with
`-DCMAKE_OSX_ARCHITECTURES=x86_64` on an Apple Silicon host still sees the host's `arm64` processor and would install
into `aarch64-darwin` (pass `-DOIPSL_PLATFORM=darwin64`, which the project already accepts, as done in section 4), and
a universal (`arm64;x86_64`) build is not handled.

Build (`raw/build/build_log.txt` for the default-contraction build, `raw/build/build_log_nofma.txt` after commit
`18e920d1`): configure 1.0 s, build about 4 s, `ctest` 6 of 6 passed in 1.5 s (`adapter_test_SCRX9`,
`layout_test_SCRX9`, `adapter_test_GFM_GFL_IBR`, `layout_test_GFM_GFL_IBR`, `two_libraries_test_scrx9_first`,
`two_libraries_test_gfm_first`), install into `OpenIPSL/Resources/Library/aarch64-darwin/`. `file`: "Mach-O 64-bit
dynamically linked shared library arm64"; `otool -L`: `@rpath/lib<Name>.dylib` and `/usr/lib/libSystem.B.dylib
(compatibility version 1.0.0, current version 1359.40.3)`; `nm -gU`: `Model_CheckParameters`, `Model_GetInfo`,
`Model_Initialize`, `Model_Outputs`, `Model_PrintInfo`, `Model_Terminate` and `<Name>_oipsl_count`, `_create`, `_free`,
`_sampleTime`, `_status`, `_step`. Warnings of the Apple toolchain: the same unused-variable warnings as gcc's in the
vendor sources (16 in `SCRX9.c`, 107 in `GFM_GFL_IBR.c`, left alone by design rule 8), `-Wunused-parameter` on
`Model_Terminate`'s `instance` (both models), and `warning: unknown warning group '-Wmaybe-uninitialized'` for the gcc
pragma in `test/layout_test.c:42` (harmless; a `#if defined(__GNUC__) && !defined(__clang__)` guard would silence
it). `-Bsymbolic` is Linux-only in the project and is not needed on macOS (two-level namespace); the
`two_libraries_test` in both orders passes.

## 3. Fused multiply-add: the one platform difference that is not round-off (commit `18e920d1`)

The first full System Modeler run set (`raw/systemmodeler/record_fma_default/`, default clang build) gave this against
Windows round 2 (source: `raw/comparison_sm_fma_default/comparison_arm_tables.md`):

| run | worst signal, ARM minus Windows (all grid points) | counters |
|---|---|---|
| GFL_Fault__euler | `out[6]` 0.18 relative (0.38 pu) at 0.0059 s | equal |
| GFL_POCFault__euler | `out[11]` (P) 2.6 Sbase (26 MW) at 3.4425 s; 2.5 before the first disturbance (0.4 s) | f_evaluations 5,203,014 / 5,203,012; state events 1,444 / 1,443 |
| GFL_FrequencyStep__euler | `out[11]` 2.6 at 2.2151 s | equal |
| GFL_VoltageStep__euler | `out[11]` 2.6 at 0.3931 s | equal |
| GFM_EMTPFull__euler | `out[11]` 2.6 at 5.4135 s | f_evaluations 7,804,458 / 7,804,452; state events 2,166 / 2,163 |
| GFM_EMTPFault__euler | `out[9]` 0.35 at 5.0225 s | equal |
| GFL_PowerRamp__euler, __dassl | `out[11]` 2.5e-3 and 2.7e-3 at 0.28 s | equal; DASSL f_evaluations 59,032,834 / 59,032,219 |
| GFL_FaultPSCAD__euler | `out[8]` 9.3e-12 (CSV floor) | equal |
| SCRX9 (both), EMTPTransformerZeroSeq, SmoothShortFault | 1e-12 to 1.4e-11 (CSV floor) | equal |

The difference is present from the first DLL sample: at t = 0 `out[6]` is -7.2e-8 on ARM and -0 on both x64 platforms,
at 5 ms -0.3045 against -0 (Windows and Linux agree to 10 digits throughout). The trajectories reconverge after the
start-up (1e-5 relative at 2 s) and separate again at each disturbance. Four rebuilds of the same sources, run on
GFL_Fault in System Modeler (`raw/systemmodeler/variants/`, `pkg/{nofma,O0,nofma_O0}`):

| library build | FMA instructions in `libGFM_GFL_IBR.dylib` | `out[6]` vs Windows | `out[11]` vs Windows |
|---|---|---|---|
| `-O3` (default) | 75 | 0.18 relative at 0.0059 s | 8.5e-2 at 0.0086 s |
| `-O0` (Debug) | 63 | 0.18 at 0.0059 s | 8.5e-2 at 0.0086 s |
| `-O3 -ffp-contract=off` | 0 | 2.0e-9 at 0.1999 s | 1.3e-9 at 0.2029 s |
| `-O0 -ffp-contract=off` | 0 | 1.8e-9 at 0.1999 s | 1.2e-9 at 0.2029 s |

So the difference follows contraction, not optimisation. Clang contracts within expressions by default
(`-ffp-contract=on`, also in `-std=c11` mode); gcc defaults to `off` in ISO C mode (`-std=c11`), which is what the
`linux64` and future `aarch64-linux` gcc builds get, and MSVC does not contract under `/fp:precise`. x86-64 has FMA
only with `-mfma`/`-march=haswell`, which no build here uses, so the x64 binaries never contract. The GFM start-up
amplifies last-bit differences (the Linux record's section 5 measured 1e6 times), and here the first-sample
difference of 7e-8 is already far above one rounding (a cancellation inside the model's first-sample arithmetic;
`out[6]` is exactly -0 on x64 at 0 and 5 ms, a clamp that ARM does not hit), so the trajectories go through the
start-up limiter differently. Commit `18e920d1` (patch `0002`) adds `-ffp-contract=off` for every non-MSVC compiler;
the record set `raw/systemmodeler/record/` and every OpenModelica run use that build. The PR's statement that the
libraries give "bit-identical outputs" across builds should be read as "on x86-64 with the stated tool chains".

## 4. Which `Resources/Library/<folder>` each tool uses on Apple Silicon (the key finding for the follow-up PR)

Method: copies of the package with the two libraries in different folders (`pkg/<layout>/OpenIPSL`), the SCRX9 Euler
test built and run in each tool; the folder is read from System Modeler's `.sim` `<ExternalLibraries>` path and link
line, and from omc's generated makefile and its "Could not find library" list. Sources:
`raw/systemmodeler/lookup/` (System Modeler 15.0.0.4), `raw/systemmodeler/lookup_wsm14.3/` (14.3.0.3, same result),
`raw/openmodelica/lookup/LOOKUP_RESULTS.txt`.

| libraries in | System Modeler 15.0 (and 14.3) | OpenModelica 1.27.1 (arm64, from source) |
|---|---|---|
| `aarch64-darwin` only | **builds and runs**; `.sim` path `.../Library/aarch64-darwin`; link `-L.../Library/aarch64-darwin -lSCRX9` | **not found**: "Could not find library SCRX9 in either of" `.../Library//`, `.../Library/arm64-darwin`, `.../Library/darwin64`, `.../Library` (as `.a` then `.dylib`), build fails |
| `arm64-darwin` only | evaluator link fails twice (`ld: library 'SCRX9' not found`), build stops | linked (`-L.../Library/ -L.../arm64-darwin -L.../darwin64 -L.../Library -lSCRX9`); run-time abort without an absolute install name (section 5) |
| `darwin64` only (arm64 binaries) | fails as above | linked; same run-time abort |
| `darwin64` only (x86-64 binaries, as an Intel build would ship) | not tried by the kernel (would fail as above) | `ld: warning: ignoring file '.../darwin64/libSCRX9.dylib': found architecture 'x86_64', required architecture 'arm64'`, then undefined symbols: build fails |
| base folder `Resources/Library/` only | fails (the kernel's evaluator has `-L.../Library` but the record shows the search needs the platform folder for the main link too) | linked; same run-time abort |
| `aarch64-darwin` and `darwin64` | uses `aarch64-darwin` | uses `darwin64` |
| `aarch64-darwin` and `arm64-darwin` | uses `aarch64-darwin` | uses `arm64-darwin` |
| none | fails | not found |

Where the names come from. System Modeler ships its own runtime in `Contents/lib/aarch64-darwin` and
`Contents/lib/darwin64` (its `runtime-manifest.json`: `"platform" : "aarch64-darwin"`), and resolves
`modelica://OpenIPSL/Resources/Library` to `<dir>/aarch64-darwin` when that folder exists. OpenModelica's search list is
`getLinkerLibraryPaths` (`OMCompiler/Compiler/SimCode/SimCodeFunctionUtil.mo:2000`): the library directory itself,
`OPENMODELICA_SPEC_PLATFORM` = `${CMAKE_SYSTEM_PROCESSOR}-${OMC_TARGET_SYSTEM_NAME}` = `arm64-darwin` on Apple
Silicon (`OMCompiler/Compiler/runtime/CMakeLists.txt:176`; on aarch64 Linux the same rule gives `aarch64-linux`),
`MODELICA_SPEC_PLATFORM` = `darwin64` (line 180), and the base folder again. The handover's reading that
OpenModelica would try `aarch64-darwin` was wrong for macOS: Apple names the processor `arm64`. Consequence for the
package: on macOS one folder cannot serve both tools; see D.1.

## 5. How the executables bind the library at run time (source: `raw/systemmodeler/binding_evidence.txt`, `raw/openmodelica/lookup/`, the OpenModelica `binding.json` of section 7)

| | System Modeler 15.0 | OpenModelica 1.27.1 |
|---|---|---|
| Link line | `clang++ ... -L<WSM>/lib/aarch64-darwin -L<pkg>/Tests/Controls/IEEE_CIGRE/SCRX9 -L<pkg>/Resources/Library/aarch64-darwin -L<same> -lSCRX9 -lmmcom -lsim ...` (from the kernel's ninja file, `keep_SCRX9.ninja`); no `-Wl,-rpath` for the package | `clang -I. -o SCRX9 ... -L<pkg>/Resources/Library/ -L.../arm64-darwin -L.../darwin64 -L.../Library -lSCRX9 ... -Wl,-rpath,<omc>/lib//omc -Wl,-rpath,<omc>/lib` (generated makefile) |
| Executable | Mach-O arm64; `otool -L`: `@rpath/libSCRX9.dylib`; **no `LC_RPATH`** | Mach-O arm64; `@rpath/libSCRX9.dylib`; `LC_RPATH` `<omc>/lib//omc` and `<omc>/lib` only |
| Launch with the CMake-default install name `@rpath/lib<Name>.dylib` | `dyld: Library not loaded: @rpath/libSCRX9.dylib, Reason: no LC_RPATH's found`, exit -6 (`raw/systemmodeler/controls/no_dyld_path/`) | the same abort inside `simulate()` ("Simulation execution failed", `Abort trap: 6`); `DYLD_LIBRARY_PATH` in omc's environment does not help, omc runs the executable through `/bin/sh -c`, which strips `DYLD_*` |
| What the runner does | `DYLD_LIBRARY_PATH=<the .sim's ExternalLibraries path>` for the executable (as `LD_LIBRARY_PATH` on Linux); with it dyld loads `.../aarch64-darwin/libSCRX9.dylib` (`DYLD_PRINT_LIBRARIES`) | the OpenModelica record uses libraries built with `-DCMAKE_INSTALL_NAME_DIR=<absolute folder>` (`LC_ID_DYLIB` = the absolute path; `pkg/record_om`), which dyld loads with no environment variable; the disassembly of `__TEXT` is identical to the record libraries (md5 of `otool -tv` equal) |
| `Ts` of the wrappers | `EVAL_PARAM` 0.005 and 1e-05 (evaluated at translation; the evaluator links fine with Apple clang) | read from the library at initialisation as on x64 |

For the follow-up PR this means: a macOS `.dylib` meant to be loaded by OpenModelica's executable needs an absolute
install name (hence it must be built on the user's machine; a binary shipped in git would carry the builder's path),
or OpenModelica would have to add `-Wl,-rpath` for its `-L` folders as it does on Linux (`DT_RPATH` with the seven
folders in the Linux record). System Modeler's Simulation Center may set the path itself when it runs the executable
(not measured: GUI route not used, D.6).

## 6. System Modeler results (source: `raw/comparison_final/comparison_arm_tables.md`, record `raw/systemmodeler/record/`)

Runs: 13 of 15 ok; `SCRX9_vs_SCRX` and `SCRX` fail at the build with the same message as on Windows and Linux (master's
native `PSSE.ES.SCRX`, "Variables have `start` values that are determined in the same block of equations as the
variables themselves: `sCRX.simpleLagLim.y`"); the x64 columns for those two runs come from the diagnostic runs with
the separate fix `b48d49e8` (not repeated here). No DLL status other than 0 (`wsm_dll_status_max_abs`), no non-finite
value, the SCRX9 init warning `[init:...] Accepting solution to nonlinear system` as on x64.

ARM against each x64 platform, worst signal per run (all grid points; relative to Sbase for P and Q, 60 Hz for f, 1 pu
for speed, the x64 signal range otherwise; "floor" = within two units of the 12th printed digit):

| run | vs Windows | vs Linux | counters (steps, f-evals, time events, state events, points) |
|---|---|---|---|
| SCRX9__dassl | ETERM 1.4e-12 (floor) | 1.4e-12 (floor) | equal |
| SCRX9__euler | PELEC 1.1e-12 (floor) | 1.1e-12 (floor) | equal |
| GFL_Fault__euler | `out[6]` 2.0e-9, 4.3e-9 pu at 0.1999 s | 1.1e-9, 2.4e-9 pu at 0.1999 s | equal |
| GFL_POCFault__euler | `out[8]` 9.2e-12 (floor) | `out[12]` 1.0e-11 (floor) | equal |
| GFL_FrequencyStep__euler | 9.9e-12 (floor) | 1.0e-11 (floor) | equal |
| GFL_VoltageStep__euler | 9.9e-12 (floor) | `out[6]` 1.5e-11 | equal |
| GFL_PowerRamp__euler | 1.0e-11 (floor) | 1.0e-11 (floor) | equal |
| GFL_FaultPSCAD__euler | 9.3e-12 (floor) | 9.3e-12 (floor) | equal |
| GFM_EMTPFault__euler | 4.6e-12 (floor) | 4.6e-12 (floor) | equal |
| GFM_EMTPFull__euler | 9.2e-12 (floor) | 9.2e-12 (floor) | equal |
| EMTPTransformerZeroSeq__euler | `Cd.v` 1.0e-12 (floor) | 1.0e-12 (floor) | equal |
| SmoothShortFault__euler | `A.v` 2.7e-12 (floor) | 2.7e-12 (floor) | equal |
| GFL_PowerRamp__dassl | 1.0e-11 (floor) | 1.0e-11 (floor) | f_evaluations 59,031,922 vs 59,032,219 (Win) and 59,031,817 (Linux); the rest equal |

The Linux record's own GFL_Fault start-up maximum against Windows was 9e-10 for System Modeler; ARM is 2.0e-9 against
Windows and 1.1e-9 against Linux, in the same `out[6]` at the same instant. Steady start of SCRX9 (t < 2 s): EFD(0)
1.43510692023, max |EFD - EFD(0)| 7.16e-5, max |w| 1.08e-6, GEN1.v range 3.68e-6, equal to the Windows and Linux
System Modeler values to the printed digits. Settled values (mean of P, Q, f over the last 0.1 s, current and voltage
peaks over the last 0.05 s, SCRX final values): no difference above 1e-3 relative against either platform (0 flags).

Wall times (ARM / x64, from the metrics files; the ARM runs had nothing else running except the first two of the FMA
set, which overlapped an OpenModelica compile for 24 s):

| | translate | compile | simulate |
|---|---|---|---|
| ARM over Windows round 2 | 0.29 to 0.74, median 0.34 | 0.26 to 0.39, median 0.28 | 0.75 to 1.53, median 0.88 |
| ARM over Linux x86_64 (WSL2) | 0.84 to 1.19, median 1.06 | 0.57 to 1.66, median 1.09 | 1.42 to 2.57, median 2.19 |

The simulation executables are compiled by System Modeler without an `-O` flag on every platform; the M2 Pro core
runs them about twice as slowly as the Linux host's x86-64 core and about as fast as the Windows host's.

Controls: with `--compiler default` (no `setCompilerPath`) the 15.0 kernel builds now that its preferences domain
holds a compiler configuration (section "Key points", trap 1; the 14.3 kernel without that file did not); without
`DYLD_LIBRARY_PATH` the executable aborts (section 5). Validation of the 57 classes (`checkModelTest`) was not run
here (section 10).

## 7. OpenModelica

### 7.1 Building omc from source (source: `om/logs/configure_build_attempt{1..5}.log`)

`README-macOS.md` does not exist at `v1.27.1`; `README.md` points to `OMCompiler/README.Linux.md` ("Linux/WSL/OSX
Instructions"), which says that on macOS only the CMake build is supported and refers to `README.cmake.md` section
3.3 (Homebrew route: `brew install autoconf automake openjdk pkg-config cmake make ccache`, configure with
`-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DOM_OMC_ENABLE_FORTRAN=OFF -DOM_OMC_ENABLE_OPTIMIZATION=OFF
-DOM_OMC_ENABLE_MOO=OFF -DOM_ENABLE_GUI_CLIENTS=OFF`). Clone: `git clone --branch v1.27.1 --depth 1
--recurse-submodules --shallow-submodules` (2 min 24 s, 1.4 GB). Homebrew packages added: autoconf 2.73, automake
1.19, openjdk 27.0.1, pkgconf 3.0.10, make 4.4.1, ccache 4.14.2, flex 2.6.4, bison 3.8.2, boost 1.92.0, libomp 23.1.4,
gettext 1.0, libiconv 1.19.1. Generator Ninja, `CMAKE_BUILD_TYPE=Release`, `SDKROOT` set, `PATH` reduced to
`/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin` plus openjdk, flex and bison.

| attempt | change | result |
|---|---|---|
| 1 (17:52 to 17:55) | the README's Homebrew command line | fails at 3,573 of 5,154 targets: `OMCompiler/3rdParty/ColPack/src/SMPGC/SMPGCColoring.h:9: fatal error: 'omp.h' file not found` (Apple clang ships no OpenMP header) |
| 2 (18:01, 24 s) | `-I/opt/homebrew/opt/libomp/include` and `-lomp` on the linker flags | ColPack fails again: `SMPGCColoringD1.cpp:473: error: no member named 'random_shuffle' in namespace 'std'` (removed in C++17; the target compiles with `-std=c++17` and Xcode 27's libc++ has dropped it) |
| 3 (18:13 to 18:14) | `-DOM_OMC_ENABLE_COLPACK=OFF`, libomp flags removed | fails at 3,581 of 3,678: `OMCompiler/SimulationRuntime/OMSICpp/runtime/src/Solver/Peer/Peer.cpp:40: fatal error: 'omp.h' file not found` (the C++ runtime's Peer solver, compiled with `-Xclang -fopenmp`) |
| 4 (18:23 to 18:24) | ColPack off plus `-I/opt/homebrew/opt/libomp/include`, `-L/opt/homebrew/opt/libomp/lib` | fails at the last link: `libOMCppPeer.dylib`: `Undefined symbols for architecture arm64: ___kmpc_fork_call ...` |
| 5 (18:24:53 to 18:24:56) | plus `-lomp` on the exe, shared and module linker flags | **installs** `~/arm-verify/om/install/bin/omc` (`v1.27.1-cmake`, arm64), 68 MB |

The task allowed two attempts; attempts 3 to 5 were cheap configure changes of the same build tree (ccache, 70 per
cent hits), the compile time of all five together about 6 minutes of wall time on 10 cores. The two deviations from a
stock omc: no ColPack (graph colouring for sparse Jacobians; not used by the DASSL and Euler runs here, which have
dense Jacobians), and the OpenMP runtime from Homebrew's libomp. No Modelica library is installed by the CMake
build (`libraries/CMakeLists.txt` only has a `libs-for-testing` target); the MSL was downloaded as the exact commit of
`libraries/index.json` and named `Modelica 4.0.0+maint.om`, `Complex 4.0.0+maint.om.mo`, `ModelicaServices
4.0.0+maint.om` under `om/libs/omlibrary/`, pointed to with `OPENMODELICALIBRARY` (omc ignores `MODELICAPATH`).
`loadModel(Modelica, {"4.0.0"}, requireExactVersion=true)` loads it and `getVersion(Modelica)` returns `4.0.0`, as in
the Linux record.

### 7.2 Results (source: `raw/openmodelica/record/` with its `logs/runs_table.md`, `logs/checks_summary.json`, `logs/binding.json`, `logs/self_comparison.md`; `raw/comparison_final/comparison_arm_tables.md`)

Recipe per run as on x64: `loadModel(Modelica, {"4.0.0"}, requireExactVersion=true); loadFile(<pkg>/package.mo);
simulate(<test>, ..., method="dassl"|"euler", outputFormat="mat", variableFilter=<contract signals>,
simflags="-lv=LOG_STATS")`, Euler step = output interval (1e-5 s GFM, 0.005 s SCRX9), CSV resampled to the contract
grid with 10 significant digits; timing pass without `LOG_STATS`, median of 3. Package `pkg/record_om/OpenIPSL`
(libraries in `aarch64-darwin` and `arm64-darwin`, absolute install names; omc linked `-L.../Library/
-L.../arm64-darwin -L.../darwin64 -L.../Library -lSCRX9`, `ld -t` and `DYLD_PRINT_SEARCHING` both name
`.../arm64-darwin/libSCRX9.dylib`, loaded without any environment variable). Static checks: `checkModel` 51 of 51
classes "completed successfully" with no message, the same with `--unitChecking`; `translateModel` 13 of 13 tests;
the `UnitProbe` negative controls behave as on x64 (`logs/unitprobe/`).

| run | outcome | translate (s) | compile (s) | simulate, no LOG_STATS median (s) | counters (steps, f-evals, Jacobians, time ev., state ev., points) | vs Windows, worst signal | vs Linux, worst signal |
|---|---|---|---|---|---|---|---|
| SCRX9__dassl | ok | 0.94 | 0.45 | 3.53 | 20,909 / 22,652 / 18,763 / 2,000 / 3 / 5,777, all equal | PELEC 1.1e-11 (floor) | w 1.0e-15 (floor) |
| SCRX9__euler | ok | 0.94 | 0.38 | 0.20 | equal | w 1.0e-14 (floor) | 1.0e-14 (floor) |
| SCRX9_vs_SCRX__dassl | ok | 1.86 | 0.59 | 6.68 | 21,498 / 23,373 / 19,270 / 2,000 / 4 / 5,779, equal | native.w 1.0e-13 (floor) | native EFD 1.0e-12 (floor) |
| SCRX__dassl | ok | 0.98 | 0.47 | 0.20 | equal | ETERM 1.4e-10 (floor) | 1.4e-10 (floor) |
| GFL_Fault__euler | ok | 0.26 | 0.33 | 2.16 | 580,003 time ev., 3 state ev., 1,730,051 points, equal | `out[6]` 4.6e-9, 9.9e-9 pu at 0.1999 s | `out[4]` 4.2e-10 (floor) |
| GFL_POCFault__euler | ok | 0.60 | 0.41 | 2.82 | 400,000 / 6 / 1,190,091, equal | `out[6]` 4.2e-10 | 4.2e-10 |
| GFL_FrequencyStep__euler | ok | 0.45 | 0.39 | 1.56 | 300,000 / 1 / 890,081, equal | `out[5]` 4.2e-10 (floor) | 4.2e-10 (floor) |
| GFL_VoltageStep__euler | ok | 0.42 | 0.35 | 1.71 | 300,000 / 1 / 890,081, equal | `out[11]` 1.0e-10 (floor) | 1.0e-10 (floor) |
| GFL_PowerRamp__euler | ok | 0.42 | 0.36 | 2.02 | 360,000 / 2 / 1,070,086, equal | `out[11]` 1.0e-10 (floor) | 1.0e-10 (floor) |
| GFL_FaultPSCAD__euler | ok | 0.31 | 0.33 | 2.32 | 580,003 / 3 / 1,730,051, equal | `out[5]` 1.1e-10 (floor) | current 4.7e-10 (floor) |
| GFM_EMTPFault__euler | ok | 0.41 | 0.37 | 4.69 | 590,006 / 6 / 1,760,068, equal | `out[10]` 1.7e-10 (floor) | 1.7e-10 (floor) |
| GFM_EMTPFull__euler | ok | 0.64 | 0.49 | 4.89 | 600,006 / 6 / 1,790,062, equal | `out[8]` 9.2e-10 (floor) | 9.2e-10 (floor) |
| EMTPTransformerZeroSeq__euler | ok | 0.37 | 0.35 | 0.53 | 0 / 0 / 300,002, equal | VSecABLL1.v 5.9e-11 (floor) | 5.9e-11 (floor) |
| SmoothShortFault__euler | ok | 0.32 | 0.35 | 0.77 | 0 / 5 / 550,012, equal | A.v 2.7e-11 (floor) | 2.7e-11 (floor) |
| GFL_PowerRamp__dassl | ok | 0.48 | 0.47 | 49.74 | 7,583,152 / 9,938,486 / 4,568,408 / 360,000 / 2 / 755,014, equal | current 3.3e-10 (floor) | `out[10]` 1.7e-10 (floor) |

Timings, ARM over x64 (OpenModelica's own `timeSimulation` without `LOG_STATS`, median of 3; `translate` = front end
+ back end + SimCode + templates; `compile` = `timeCompile`):

| | translate | compile | simulate |
|---|---|---|---|
| ARM over Windows round 2 | 1.64 to 2.93, median 2.06 | 0.15 to 0.40, median 0.33 | 1.10 to 2.09, median 1.34 |
| ARM over Linux x86_64 (WSL2) | 1.41 to 3.27, median 2.06 | 0.72 to 1.13, median 0.90 | 1.14 to 2.73, median 1.52 |

The model code is compiled with `-Os` by clang on all three platforms. The self-built omc's front end is about twice
as slow as the released binaries' (an unoptimised MetaModelica runtime is possible; not investigated). The OpenModelica
runs had nothing else running except the FMA control package build (a few seconds).

SCRX9 against native SCRX in OpenModelica on ARM (CSV basis, the same three numbers on the Windows and Linux
OpenModelica CSVs): steady start EFD(0) 1.43510692, max |EFD - EFD(0)| 7.165e-5, max |w| 1.080e-6, GEN1.v range 3.676e-6
before 2 s; `SCRX9_vs_SCRX` DLL minus native EFD 1.219e-6 pu before the fault (at 0.790 s), 0.039914 pu at the 5 ms
samples after it, 7.472e-5 at 10 s, GEN1.v 1.58e-3 and speed 6.28e-5 at the samples after the fault; the SCRX9 test
against the native test before 2 s: EFD 4.54e-6 (at 1.629 s), GEN1.v 3.04e-7, speed 1.452e-7.

Run-time binding (`logs/binding.json`): the executable depends on the absolute path
`<pkg>/Resources/Library/arm64-darwin/lib<Name>.dylib` (the install name), `LC_RPATH` only `<omc>/lib//omc` and
`<omc>/lib`; dyld "found: dylib-from-disk" at that path. omc's compile of `SCRX9_functions.c` warns
`-Wparentheses-equality` (generated code, as on Linux).

## 8. Cross-tool on ARM (source: `runs/<run>/cross_tool_arm` and `cross_tool_x64_worst` in `raw/comparison_final/comparison_arm.json`)

OpenModelica minus System Modeler on the contract grid, OpenModelica rebuilt from its raw `.mat` result with the
round-2 instant rule (stored points closer than 1e-9 s are one instant, post-event value on an instant), relative to
Sbase for P and Q, 60 Hz for f, 1 pu for speed, the signal range otherwise; worst over the key signals, all grid
points (the "excl" variant gives the same values):

| run | ARM | Windows round 2 | Linux x64 |
|---|---|---|---|
| SCRX9__dassl | PELEC 3.659e-5 | 3.659e-5 | 3.659e-5 |
| SCRX9__euler | EFD 1.152e-6 | 1.152e-6 | 1.152e-6 |
| GFL_Fault__euler | phase-a current 5.591e-7 | 5.591e-7 | 5.591e-7 |
| GFL_POCFault__euler | phase-c current 2.615e-1 | 2.615e-1 | 2.615e-1 |
| GFL_FrequencyStep__euler | `out[12]` 3.966e-7 | 3.966e-7 | 3.966e-7 |
| GFL_VoltageStep__euler | `out[11]` 3.409e-8 | 3.409e-8 | 3.409e-8 |
| GFL_PowerRamp__euler | `out[12]` 4.220e-7 | 4.220e-7 | 4.220e-7 |
| GFL_FaultPSCAD__euler | phase-a voltage 5.032e-7 | 5.032e-7 | 5.032e-7 |
| GFM_EMTPFault__euler | phase-a voltage 3.344e-3 | 3.344e-3 | 3.344e-3 |
| GFM_EMTPFull__euler | phase-b current 5.047e-2 | 5.047e-2 | 5.047e-2 |
| EMTPTransformerZeroSeq__euler | Ad.v 5.875e-13 (CSV floor) | 1.030e-12 | 5.878e-13 |
| SmoothShortFault__euler | A.v 8.914e-3 | 8.914e-3 | 8.914e-3 |
| GFL_PowerRamp__dassl | phase-c current 7.855e-7 | 7.855e-7 | 7.855e-7 |

(`SCRX9_vs_SCRX` and `SCRX` have no System Modeler result on any platform without the separate fix.) The
cross-tool differences are properties of the tools' Euler and event handling, not of the platform: identical to the
x64 values wherever the CSVs resolve them. Settled values (GFM: mean P, Q, f over the last 0.1 s, current and voltage
peaks over the last 0.05 s): no pair differs by more than 1e-3 relative (0 flags); GFL_FaultPSCAD's settled P and Q
over the last 0.1 s are 40.16925 MW and -71.71756 Mvar in both tools.

## 9. Everything that differs from x64, and why

1. Floating-point contraction (section 3): the only difference above round-off, removed by `-ffp-contract=off`.
2. Platform folder names (section 4): System Modeler `aarch64-darwin`, OpenModelica `arm64-darwin` (then `darwin64`,
   base). On x64 both tools agree on `win64`/`linux64`.
3. Run-time binding (section 5): no rpath to the package in either tool's executable, and dyld's `@rpath` install
   name convention. On Linux, OpenModelica writes a `DT_RPATH` with the library folders; on macOS it does not.
4. Tool versions: System Modeler 15.0.0.4 as on both x64 platforms (after the mid-session upgrade); OpenModelica
   `v1.27.1-cmake` built here without ColPack, against the released 1.27.1 binaries on x64.
5. Compilers: Apple clang 21.0.0 for the libraries (gcc 15.2 Linux, MSVC 19.51 Windows), for System Modeler's model
   code (g++ 13.3 Linux, MSVC Windows) and for OpenModelica's (clang 18.1 Linux, clang 22.1 Windows). Maths library:
   Apple libSystem (glibc 2.39, UCRT).
6. The MSL of OpenModelica came from a zip of the `index.json` commit rather than the `omlibrary` package; the same
   files.
7. Timings (section 6 and 7): translation faster than Windows, simulation about Windows' speed and about half of
   the Linux host's; indicative only.
8. Round-off: GFL_Fault's start-up at 1 to 2e-9 (System Modeler) and 4.6e-9 (OpenModelica against Windows; at the
   floor against Linux), everything else at the CSV floor; the same pattern and size as Linux against Windows.

## 10. What is NOT verified

1. Dymola: not available on macOS (no Apple Silicon Dymola).
2. The GUIs: System Modeler's Model Center and Simulation Center (whether Simulation Center sets `DYLD_LIBRARY_PATH`
   or copies the library), OMEdit (not built: GUI clients off).
3. System Modeler validation of the 57 classes with `checkModelTest` (the Linux record did it; the kernel route is
   the same here and could be run with `kit/.../tests/systemmodeler/validate_classes.py` ported).
4. The Windows-WSMLink route and `WSMValidate`: no Wolfram Language kernel was used (Mathematica 13.2 is installed
   but WSMLink needs matching versions).
5. x86-64 control runs on this Mac: Rosetta 2 is not installed. The `-ffp-contract=off` evidence rests on the four
   library builds of section 3 and the agreement with both x64 records.
6. A stock OpenModelica (with ColPack) on arm64 macOS: none exists; a nightly or a MacPorts-clang build would have
   ColPack.
7. Whether System Modeler 14.3 gives the same simulation results as 15.0: only the lookup experiment ran on 14.3.
8. Both libraries in one Modelica model (covered by the C `two_libraries_test` only, as on x64).
9. An installed, shipped `aarch64-darwin` binary used from another checkout path (the absolute install name of the
   OpenModelica route is path-bound by design).
10. Raspberry Pi (aarch64 Linux): separate session.

## 11. Open questions and decisions for Luigi

D.1 **Platform folders on macOS.** System Modeler loads only `aarch64-darwin`; OpenModelica only `arm64-darwin`,
    `darwin64` or the base folder, and its executable cannot load an `@rpath` dylib anyway (section 5). Options:
    (i) ship no macOS binaries; let the CMake project install a locally built library into both `aarch64-darwin`
    and `arm64-darwin` (two `install()` destinations) with an absolute install name (`CMAKE_INSTALL_NAME_DIR` set to
    the destination), and say so in the README classes (recommended: it is the only layout measured to work in both
    tools without environment variables, and git would otherwise carry path-bound binaries); (ii) ship
    `aarch64-darwin` binaries for System Modeler only and document the OpenModelica build step; (iii) ship both
    folders with `@rpath` binaries and document `DYLD_LIBRARY_PATH` for System Modeler executables run outside the
    tool, accepting that OpenModelica on macOS cannot use them. The D.1 decision of 2026-10-31 (`aarch64-darwin`,
    `aarch64-linux`) stands for System Modeler and for Linux; `arm64-darwin` is OpenModelica's name on macOS.
D.2 **`-ffp-contract=off` (commit `18e920d1`).** (i) take it into #433 now (the `linux64` gcc build already runs
    without contraction in ISO C mode, so its binaries do not change in behaviour; MSVC is unaffected; recommended);
    (ii) keep it for the ARM follow-up PR. Either way the x64 README sentence on bit-identical rebuilds should name
    the condition. A source-level `#pragma STDC FP_CONTRACT OFF` in the three C files would protect builds that
    bypass CMake; clang honours it, gcc ignores it (gcc is off in ISO mode anyway).
D.3 **System Modeler 15.0 was installed on the Mac between 17:58 and 18:02 while this session ran** (14.3 [8] before,
    15.0 [14] after; preferences domain `com.wolfram.SystemModeler150002.plist` created 18:12). Please confirm it was
    you, so the record can say so; all result sets used 15.0.0.4.
D.4 **Deployment target.** The dylibs built here have `minos 27.0`. If macOS binaries are ever shipped,
    `CMAKE_OSX_DEPLOYMENT_TARGET` (for example 12.0) belongs in the CMake project; with D.1 (i) it does not matter.
D.5 **OpenModelica reference on macOS.** Accept the self-built `v1.27.1-cmake` without ColPack as the macOS
    OpenModelica of this record (recommended; the runs do not use ColPack), or wait for an official arm64 macOS build.
D.6 **Report to Wolfram?** (a) the fresh standalone kernel's silent `buildModel` failure when no compiler is
    configured (14.3; 15.0 after the GUI had written its preferences did build without `setCompilerPath`), (b) the
    executable has no `LC_RPATH` for `<ExternalLibraries>` on macOS (as no `RUNPATH` on Linux). Recommended: (b)
    together with the earlier `libserializer` report.
D.7 **Report to OpenModelica?** omc on macOS puts the `LibraryDirectory` folders on `-L` but not on `-Wl,-rpath`
    (unlike Linux), so any `@rpath` dylib from a Modelica library fails to load; and the `aarch64`/`arm64` naming
    difference with System Modeler. Recommended: yes, both, citing this record.

Decisions taken by Luigi, 2026-10-31 ~18:50 (after the first version of this record):
  - D.1: (i), "proceed". Implemented as commit `54f983e7` (patch `0003`): `INSTALL_NAME_DIR` = the installed folder
    on Apple, `install(CODE file(CREATE_LINK ...))` for `arm64-darwin -> aarch64-darwin` when the platform is
    `aarch64-darwin`; the README wording belongs to the follow-up pull request. Verified in both tools without
    environment variables (key points). Limit: the install name is fixed at configure time, so `cmake --install
    --prefix <other>` would leave a wrong path; the default prefix (the checkout's `Resources`) is the intended use.
  - D.3: Luigi installed System Modeler 15 on the Mac (not on the Pi, where it cannot run); the record stands.
  - D.5: accepted, there is no other OpenModelica for arm64 macOS.
  - D.2: agreed on the flag; it goes to #433 together with everything else only after the whole ARM process
    (this record, the Raspberry Pi session, the follow-up) is finished, in one push decided by Luigi. Nothing is pushed
    until then.
  - D.4: closed, no action (nothing is shipped).
  - D.6 and D.7: agreed in substance, but not now: the reports to Wolfram and to OpenModelica are written after the
    main work and the sub-sessions are done, not as parallel side tasks.

## 12. Files of this record

- `ARM_MACOS_VERIFICATION.md` (this file).
- `patches/0001-build-IEEE_CIGRE-platform-folders-aarch64-linux-and-.patch` (commit `f457b90f`),
  `patches/0002-build-IEEE_CIGRE-no-floating-point-contraction-on-gc.patch` (commit `18e920d1`),
  `patches/0003-build-IEEE_CIGRE-macOS-install-names-and-the-arm64-d.patch` (commit `54f983e7`, D.1); the branch
  `arm-platform-folders` in `OpenIPSL/` (not pushed). `raw/systemmodeler/d1_check/` and `raw/openmodelica/d1_check/`
  hold the D.1 verification runs; `raw/build/build_log_d1.txt` the build.
- `scripts/`: `wsm_run_macos.py`, `run_all_macos.sh`, `runs.json` (System Modeler); `omc_verify_macos.py`,
  `run_all_om_macos.sh`, `UnitProbe.mo` (OpenModelica); `compare_arm.py` (the comparison; imports
  `records/report/linux/compare_linux.py`).
- `raw/env/environment.txt`; `raw/build/` (build logs, `compile_commands*.json`).
- `raw/systemmodeler/record/` (the 15 contract runs with the `-ffp-contract=off` libraries: CSV, `_metrics.json`,
  `_raw_points.txt`, `logs/<run>/` with the kernel output, `.sim`, ninja file, simulation stdout and stderr),
  `record_fma_default/` (the same with the default build), `variants/` (section 3), `lookup/` and
  `lookup_wsm14.3/` (section 4), `controls/`, `probe1_licence/` to `probe4_compiler/` (the kernel traps),
  `binding_evidence.txt`.
- `raw/openmodelica/record/` (env, checks, extras, the 15 runs with CSV, `_metrics.json`, `_raw_points.txt`,
  `logs/<run>/run.mos` and `log.txt`, timing, `logs/binding.json`, `logs/self_comparison.{json,md}`,
  `logs/runs_table.md`), `record_fma_default/` (the FMA control, three GFM runs with the unpatched build), `lookup/`
  with `LOOKUP_RESULTS.txt`, `smoke/`.
- `raw/comparison_final/` (`comparison_arm.json`, `comparison_arm_tables.md`, `figs/`), `raw/comparison_sm_nofma/`,
  `raw/comparison_sm_fma_default/`.
- `om/` (OpenModelica source clone, `build_cmake/`, `install/`, `libs/omlibrary/`, `logs/`), `build/` (CMake trees
  and the tools' build trees with the raw `.mat` results), `pkg/` (the package copies).
