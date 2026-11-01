# ARM Linux (aarch64, Raspberry Pi 400) verification of the IEEE/CIGRE DLL package (OpenIPSL #433, `b05fa044`)

Date: 2026-11-01, 01:20 to 10:20 local (EST). Machine: Raspberry Pi 400 Rev 1.0, 4 x Cortex-A72 at 1.8 GHz, 3.7 GiB
RAM, Raspberry Pi OS 64-bit (Debian 13 trixie), kernel 6.18.50+rpt-rpi-v8; `vcgencmd get_throttled` = `0x0` at the end
(no throttling or under-voltage since boot). Session: Claude Opus 5.5 (sub-session of the parent session of the ARM
verification), working folder `/home/<pi-user>/arm-verify/` on the Pi.
Package under test: OpenIPSL branch `feature/ieee-cigre-dll`, head `b05fa04440809291d61f13045f8586d186613f66`
(pull request #433), cloned to `/home/<pi-user>/arm-verify/OpenIPSL/`, plus the three commits of the macOS record applied with
`git am` on the local branch `arm-platform-folders` (`9ad85173`, `f2e201d2`, `deeb1fa7`; the same patches as macOS's
`f457b90f`, `18e920d1`, `54f983e7`, new hashes because `git am` writes a new committer date; nothing pushed).
References, read only: the Windows round-2 record (`records/report/verification_round2/`), the Linux x86_64 record
(`records/report/linux/`) and the macOS arm64 record (`records/iterations/2026-10-31_I9-arm-verification/macos/`, its
15 OpenModelica CSVs and metrics in `.../macos/raw/openmodelica/` and its `comparison_final/comparison_arm.json`).
Every number below is read from `comparison_final/comparison_arm.json` (written by `scripts/compare_arm.py`, which
imports the statistics functions of `records/report/linux/compare_linux.py`) or from a file named in the sentence.
Paths are relative to `/home/<pi-user>/arm-verify/` unless absolute.

## TL;DR

The IEEE/CIGRE libraries build natively on the Pi with gcc 14.2 (6 of 6 C tests), install into `aarch64-linux` with
patch 0001, and OpenModelica 1.27.2 from the OpenModelica arm64 apt repository (trixie) runs all 15 contract runs:
15 of 15 ok, all 68 counters equal to Windows, Linux x86_64 and macOS arm64, every key signal at the CSV print floor
against Linux x86_64 (worst 9.2e-10 relative) and against macOS (worst 7.4e-10), and against Windows only the known
GFL_Fault start-up (4.5e-9 at 0.1999 s, the same place and size macOS and Linux have against Windows). Settled values:
0 flags. omc on aarch64 Linux searches `Resources/Library/`, `aarch64-linux` and the base folder, never `linux64`, so
without patch 0001 the build fails; the executable finds the library by its `DT_RPATH`, no environment variable. The
CMake build does not contract `a*b+c` (gcc in ISO C mode), so patch 0002 changes nothing here, but a gcc build in GNU
mode does, and that build sends GFL_VoltageStep to a different operating point (P -9.2 instead of 5.0 MW, f 62.5 Hz at
3 s): patch 0002 protects against a real failure, not a cosmetic one. The Pi is 7.5 to 13.9 times slower than the
Linux x86_64 host in simulation (median 12.0). No System Modeler (none exists for Linux arm64). Decisions D.1 to D.4
at the end; nothing is pushed.

## Key points

- **Build (section 2).** CMake 3.31.6 + Ninja 1.12.1, Release, gcc 14.2.0 (Debian 14.2.0-19), `-std=c11
  -ffp-contract=off` from patch 0002. 6 of 6 `ctest` tests pass in 0.05 s. Two aarch64 ELF shared objects,
  `libGFM_GFL_IBR.so` 75,160 bytes (NEEDED `libm.so.6`, `libc.so.6`) and `libSCRX9.so` 72,328 bytes (NEEDED
  `libc.so.6` only), SONAME `lib<Name>.so`, 12 exported symbols each, no RPATH/RUNPATH. 130 compiler warnings, all in
  the vendor model sources: 121 `-Wunused-variable`, 2 `-Wunused-parameter` (`Model_Terminate`), 7
  `-Wmaybe-uninitialized` in `GFM_GFL_IBR.c` (`del_omega`, `Idref`, `Iqref`, lines 1333 to 1494). The adapter is
  warning-free.
- **Patch 0001 is required on Linux aarch64.** The unpatched project installs into `linux64`; omc never searches
  `linux64` on this machine, and a library only there fails to link (`cannot find -l<Name>`, measured with the probe
  library of section 4). With 0001, `CMAKE_SYSTEM_PROCESSOR` = `aarch64` gives `aarch64-linux`, which omc does search.
- **Folder lookup (section 4), measured with eight layouts of a probe library that returns its folder number.**
  omc 1.27.2 puts `-L<pkg>/Resources/Library/ -L<pkg>/Resources/Library/aarch64-linux -L<pkg>/Resources/Library` on
  the link line (and the same list on `-Wl,-rpath`). `aarch64-linux` alone: loaded. `linux64` alone or `arm64-linux`
  alone: build fails. A copy in the base folder shadows the one in `aarch64-linux` (the base folder comes first, with
  a trailing slash). The x86-64 `linux64` binaries that the repository ships are never tried on ARM.
- **Fused multiply-add (section 3).** gcc 14 in `-std=c11` mode produces no `fmadd`/`fmsub`/`fnmadd`/`fnmsub` with or
  without `-ffp-contract=off` (identical `.text`); `-std=gnu11` or `-ffp-contract=fast` gives 76 fused instructions in
  `GFM_GFL_IBR.o` and 3 in `SCRX9.o`. With those contracted libraries (FMA control, three runs): GFL_Fault `out[6]`
  (Iqref) off by 0.384 pu at 5.9 ms and GFL_VoltageStep P off by 25.7 MW (2.57 Sbase) at 0.3931 s, the same values
  and instants as macOS's clang FMA control; GFL_VoltageStep also ends in another state (P -9.18 MW, Q -5.33 Mvar, f 62.47 Hz averaged over the last
  0.1 s, against 4.985 MW, 2.276 Mvar, 60.003 Hz), with equal event counts; SCRX9 is unaffected (1.2e-13, the CSV floor).
- **OpenModelica 1.27.2 against 1.27.1 (the x64 and macOS records).** The four commits between the tags
  (`562f07f037` FMU export nominal values, `6db4671648` zip extraction, `9f04f714ac` connection operators in algorithms,
  `4f2b2b1d94` autoconf C23) touch none of the C runtime solvers, the event handling, the external-library linking or
  SimCode; the contract models have no connection operators in algorithm sections, and the results equal the 1.27.1
  records. No difference in this record needs the version change to explain it.
- **Results (section 6).** 15 of 15 ok; counters 68 of 68 equal against each of Windows, Linux x86_64 and macOS
  arm64; worst relative difference per platform: Windows 4.5e-9 (GFL_Fault `out[6]`, 9.6e-9 pu at 0.1999 s, the only
  value above the CSV floor), Linux 9.2e-10 (GFM_EMTPFull `out[8]`, floor), macOS 7.4e-10 (GFL_POCFault `out[6]`,
  1.8e-9 pu at 0.3024 s, two print units). `checkModel` 51 of 51 classes without message, the same with
  `--unitChecking`; `translateModel` of the 13 tests ok; the `UnitProbe` negative controls flag the wrong unit as on x64.
- **Run-time binding (section 5).** The simulation executable has a `DT_RPATH` (omc links with
  `--disable-new-dtags`) of `/usr/lib/aarch64-linux-gnu/omc`, `/usr/lib`, `~/.openmodelica/binaries/OpenIPSL` and the
  three package folders; `LD_DEBUG=libs` shows `libSCRX9.so` and `libGFM_GFL_IBR.so` loaded from
  `<pkg>/Resources/Library/aarch64-linux/`, "RPATH from file", no `LD_LIBRARY_PATH`; run by hand outside omc the
  executable finishes with return code 0.
- **Timings (section 6).** Simulation ARM over Linux x86_64 7.50 to 13.87 (median 11.97), over Windows 4.13 to 12.20
  (median 10.02), over macOS 2.87 to 9.84 (median 7.67); C compile of the generated code 13.5 to 19.4 times the Linux
  host's (clang 19 at `-Os` on four A72 cores); translation 3.9 to 6.9 times. GFL_PowerRamp with DASSL takes 242 s
  (median of 3). Indicative only.

## 1. Environment (source: `ENVIRONMENT_2026-11-01.txt`, `raw/openmodelica/record/logs/env.txt`, `raw/build/`)

| item | value |
|---|---|
| Machine | Raspberry Pi 400 Rev 1.0, Cortex-A72 x 4, max 1800 MHz, flags `fp asimd evtstrm crc32 cpuid` |
| Memory, disk | 3.7 GiB RAM, 58 GB SD card (`/dev/mmcblk0p2`, 40 GB free) |
| OS | Debian GNU/Linux 13 (trixie), Raspberry Pi OS 64-bit; kernel `6.18.50+rpt-rpi-v8`; glibc 2.41-12+rpt1+deb13u4 |
| Library build | CMake 3.31.6, Ninja 1.12.1, gcc 14.2.0 (Debian 14.2.0-19) |
| OpenModelica | `omc` 1.27.2 (`/usr/bin/omc`), from `https://build.openmodelica.org/apt trixie stable`, packages `omc`, `omlibrary 1.27.2-1`; generated code compiled by Debian clang 19.1.7 |
| MSL | Modelica 4.0.0+maint.om (`loadModel(Modelica, {"4.0.0"}, requireExactVersion=true)`), unpacked from the omlibrary zip cache into `~/.openmodelica/libraries/` |
| Python | 3.13 with numpy; no matplotlib (no packages installed, Luigi's rule: no sudo, no new packages), so no figures |
| Wolfram | `wolfram-engine` 15.0.1 installed, no System Modeler kernel (`WSMKernel`) for Linux arm64 |

The column label for this platform in the tables is "OpenModelica 1.27.2 (arm64 apt, trixie)" (Luigi's decision).
The runs were serial (RAM), with only this session's shell running beside them.

## 2. The CMake change and the build (source: `raw/build/{configure,build,ctest,install}_log.txt`)

Source folder `OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE` (two `OpenIPSL` levels), build tree
`build/ieee_cigre`:

```
cmake -S OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE -B build/ieee_cigre -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/ieee_cigre
ctest --test-dir build/ieee_cigre --output-on-failure
cmake --install build/ieee_cigre
```

Install: `-- Installing: .../OpenIPSL/OpenIPSL/Resources/Library/aarch64-linux/libSCRX9.so` and `libGFM_GFL_IBR.so`
(the folder is untracked in the checkout). `file`: "ELF 64-bit LSB shared object, ARM aarch64". The three patches:

| patch | commit here | effect on the Pi |
|---|---|---|
| 0001 platform folders | `9ad85173` | required: `aarch64-linux` instead of `linux64` |
| 0002 `-ffp-contract=off` | `f2e201d2` | no change to the CMake build's code (gcc does not contract in ISO C mode); guards GNU-mode builds (section 3) |
| 0003 macOS install names | `deeb1fa7` | macOS only; inactive on Linux |

## 3. Fused multiply-add (source: `build/fma_variants/fma_counts.txt`, `raw/openmodelica/record_fma_gnu11/`)

Each library source compiled once per flag set (object names in `fma_counts.txt`), fused instructions counted with
`objdump -d`
(`fmadd`, `fmsub`, `fnmadd`, `fnmsub`, `fmla`, `fmls`):

| flags | `GFM_GFL_IBR.o` | `SCRX9.o` | adapter |
|---|---|---|---|
| `-std=c11` (CMake's mode) | 0 | 0 | 0 |
| `-std=c11 -ffp-contract=off` (patch 0002) | 0, `.text` identical to the line above | 0, identical | 0 |
| `-std=c11 -ffp-contract=fast` | 76 | 3 | 0 |
| `-std=gnu11` (gcc's default mode) | 76, `.text` identical to `fast` | 3 | 0 |
| `-std=c11 -O0 -ffp-contract=fast` | 0 | 0 | 0 |

The installed libraries have 0 fused instructions. Unlike clang (which contracts at `-O0` on macOS), gcc does not
contract without optimisation.

FMA control: a copy of the package (`pkg/fma_gnu11/OpenIPSL`) with the `-std=gnu11` libraries
(`build/fma_variants/so_gnu11/`, 76 and 3 fused instructions) in `aarch64-linux`, the same recipe, three runs
(`raw/openmodelica/run_fma_nohup.log`; diffs by `scripts/fma_diff.py` in
`raw/openmodelica/record_fma_gnu11/fma_diff_vs_{record,windows}.txt`):

| run | counters | largest difference against this record (and against Windows, the same) | first sample above 1e-6 of scale |
|---|---|---|---|
| GFL_Fault__euler | equal (580,003 / 3 / 1,730,051) | `out[6]` (Iqref) 0.384 pu at 5.9 ms (0.32 of its range); phase-c current 403 A at 5.9 ms; P `out[11]` 0.848 MW at 8.6 ms; settled P 7.0180 against 7.0185 MW | 0.1 ms |
| GFL_VoltageStep__euler | equal (300,000 / 1 / 890,081) | P `out[11]` 25.7 MW at 0.393 s; f `out[10]` 3.13 Hz; the run ends elsewhere: last 0.1 s P -9.185 MW, Q -5.326 Mvar, f 62.474 Hz (reference 4.985, 2.276, 60.003); f sits at 62.727 Hz from about 1.5 to 2.5 s | 0.2 ms |
| SCRX9__dassl | equal (20,909 steps, 22,652 f-evals, 18,763 Jacobians, 2,000 / 3 / 5,777) | `PELEC` 1.2e-13 (CSV floor) | none |

Both worst values are the macOS ones (GFL_Fault `out[6]` 0.38 pu at 0.0059 s, GFL_VoltageStep `out[11]` 2.57
Sbase at 0.3931 s, with clang's 75 fused instructions), so gcc's and clang's contraction hit the same model
arithmetic. The macOS record gives no settled values for its FMA control, so whether its GFL_VoltageStep also ended
at 62.5 Hz is not known here. The control libraries were not installed and the record runs did not use them.

## 4. Which `Resources/Library/<folder>` omc uses on Linux aarch64 (source: `raw/openmodelica/lookup/LOOKUP_RESULTS.txt`)

`scripts/probe_folders.sh` builds `scripts/folder_probe.c` once per folder with its own `FOLDER_ID`, places the copies
by layout, and simulates `FolderProbe.M` (`y = probeValue(time)`, `Library="FolderProbe"`); `y` at the end tells which
copy was loaded (1 base, 2 `aarch64-linux`, 3 `linux64`, 4 `arm64-linux`).

| layout | `y` | result |
|---|---|---|
| none | - | build fails: `cannot find -lFolderProbe` |
| `aarch64-linux` | 2 | ok |
| `linux64` | - | build fails |
| `arm64-linux` | - | build fails |
| base | 1 | ok |
| `aarch64-linux` + `linux64` | 2 | ok |
| `aarch64-linux` + base | 1 | ok, base shadows `aarch64-linux` |
| base + `aarch64-linux` + `linux64` + `arm64-linux` | 1 | ok, base |

Link line in every layout: `-L/usr/bin/../lib/aarch64-linux-gnu/omc -L/usr/bin/../lib/
-L~/.openmodelica/binaries/FolderProbe -L<pkg>/Resources/Library/ -L<pkg>/Resources/Library/aarch64-linux
-L<pkg>/Resources/Library`. omc's platform name is `${CMAKE_SYSTEM_PROCESSOR}-linux` = `aarch64-linux`; the x86-64
build has `x86_64-linux` then `linux64`. The name agrees with the D.1 decision of 2026-10-31 (`aarch64-linux`).

## 5. How the executable binds the library at run time (source: `raw/openmodelica/record/logs/binding.json`, `logs/binding_{SCRX9,GFL_Fault}/`)

For SCRX9 and GFL_Fault: the `DT_RPATH` holds `/usr/bin/../lib/aarch64-linux-gnu/omc:/usr/bin/../lib/:
/home/<pi-user>/.openmodelica/binaries/OpenIPSL:<pkg>/Resources/Library/:<pkg>/Resources/Library/aarch64-linux:
<pkg>/Resources/Library`. `LD_DEBUG=libs` tries the first four and finds `<pkg>/Resources/Library/aarch64-linux/
lib<Name>.so` ("RPATH from file .../SCRX9"); one process loads it; no `LD_LIBRARY_PATH` and no system path in the
trace. Run by hand without environment variables, `ldd` names the same file and the run ends with return code 0. As on
x86-64 Linux; unlike macOS, where omc writes no rpath to the package.

## 6. OpenModelica results (source: `raw/openmodelica/record/` with `logs/runs_table.md`, `logs/checks_summary.json`, `logs/self_comparison.md`; `comparison_final/comparison_arm_tables.md`)

Recipe per run as on x64 and macOS: `loadModel(Modelica, {"4.0.0"}, requireExactVersion=true); loadFile(<pkg>/
package.mo); simulate(<test>, ..., method="dassl"|"euler", outputFormat="mat", variableFilter=<contract signals>,
simflags="-lv=LOG_STATS")`, Euler step = output interval (1e-5 s GFM, 0.005 s SCRX9), CSV resampled to the contract
grid with 10 significant digits; timing pass with `simflags="-s=<method>"` without `LOG_STATS`, median of 3. Package
`pkg/record/OpenIPSL` (a `git archive` of `deeb1fa7` plus the installed `aarch64-linux` libraries; `COMMIT` file).
Driver `scripts/run_all_om_pi.sh` (steps env, checks, extras, run, timing, binding, compare, table), 01:35:42 to
02:28:23, every step exit 0 (`raw/openmodelica/run_all_nohup.log`).

Static checks: `checkModel` 51 of 51 classes "completed successfully" with no message (12.0 s), the same with
`--unitChecking` (10.9 s); `translateModel` of the 13 tests ok (with the usual alias-conflict warning);
`UnitProbe.WrongUnit` reports "The following equation is INCONSISTENT due to specified unit information: i = v" as on
x64 (`logs/unitprobe/`).

| run | outcome | translate (s) | compile (s) | simulate, no LOG_STATS median (s) | counters | vs Windows, worst | vs Linux x64, worst | vs macOS, worst |
|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | ok | 1.96 | 7.69 | 21.18 | 20,909 / 22,652 / 18,763 / 2,000 / 3 / 5,777, all equal | PELEC 1.1e-11 (floor) | 1.1e-13 (floor) | 1.1e-13 (floor) |
| SCRX9__euler | ok | 2.03 | 7.87 | 0.56 | 2,002 / 2 / 5,775, equal | w 1e-16 (floor) | 1e-16 (floor) | w 1e-14 (floor) |
| SCRX9_vs_SCRX__dassl | ok | 4.41 | 11.15 | 44.65 | 21,498 / 23,373 / 19,270 / 2,000 / 4 / 5,779, equal | native.w 1e-13 (floor) | native EFD 1e-12 (floor) | native.w 1e-13 (floor) |
| SCRX__dassl | ok | 2.08 | 7.57 | 0.59 | 463 / 542 / 61 / 0 / 4 / 2,010, equal | ETERM 1.4e-10 (floor) | 1.4e-10 (floor) | 1.4e-10 (floor) |
| GFL_Fault__euler | ok | 0.78 | 5.14 | 19.10 | 580,003 / 3 / 1,730,051, equal | `out[6]` 4.5e-9, 9.6e-9 pu at 0.1999 s | `out[4]` 4.2e-10 (floor) | `out[4]` 4.2e-10 (floor) |
| GFL_POCFault__euler | ok | 1.74 | 8.54 | 27.73 | 400,000 / 6 / 1,190,091, equal | `out[4]` 4.2e-10 (floor) | 4.2e-10 (floor) | `out[6]` 7.4e-10, 1.8e-9 pu at 0.3024 s |
| GFL_FrequencyStep__euler | ok | 1.18 | 6.62 | 12.04 | 300,000 / 1 / 890,081, equal | `out[11]` 1e-10 (floor) | 1e-10 (floor) | `out[5]` 4.2e-10 (floor) |
| GFL_VoltageStep__euler | ok | 1.20 | 6.83 | 13.12 | 300,000 / 1 / 890,081, equal | `out[10]` 1.7e-10 (floor) | 1.7e-10 (floor) | 1.7e-10 (floor) |
| GFL_PowerRamp__euler | ok | 1.20 | 6.78 | 18.32 | 360,000 / 2 / 1,070,086, equal | `out[11]` 1e-10 (floor) | 1e-10 (floor) | 1e-10 (floor) |
| GFL_FaultPSCAD__euler | ok | 0.90 | 5.31 | 18.28 | 580,003 / 3 / 1,730,051, equal | `out[5]` 1.1e-10 (floor) | current 4.7e-10 (floor) | `out[5]` 1.1e-10 (floor) |
| GFM_EMTPFault__euler | ok | 1.10 | 6.33 | 38.51 | 590,006 / 6 / 1,760,068, equal | `out[10]` 1.7e-10 (floor) | 1.7e-10 (floor) | `out[11]` 1e-10 (floor) |
| GFM_EMTPFull__euler | ok | 1.72 | 8.44 | 42.77 | 600,006 / 6 / 1,790,062, equal | `out[8]` 9.2e-10 (floor) | 9.2e-10 (floor) | `out[11]` 1e-10 (floor) |
| EMTPTransformerZeroSeq__euler | ok | 1.02 | 6.14 | 3.57 | 0 / 0 / 300,002, equal | VSecABLL1.v 5.9e-11 (floor) | 5.9e-11 (floor) | 5.9e-11 (floor) |
| SmoothShortFault__euler | ok | 0.93 | 5.70 | 3.69 | 0 / 5 / 550,012, equal | A.v 2.7e-11 (floor) | 2.7e-11 (floor) | 0 (identical) |
| GFL_PowerRamp__dassl | ok | 1.22 | 6.84 | 241.65 | 7,583,152 / 9,938,486 / 4,568,408 / 360,000 / 2 / 755,014, equal | `out[10]` 1.7e-10 (floor) | current 3.3e-10 (floor) | current 3.3e-10 (floor) |

Counters: DASSL runs steps / f-evaluations / Jacobians / time events / state events / output points; Euler runs time
events / state events / output points (SCRX9__euler 2,002 time events). "Floor" = the difference is the 10th
significant digit of the CSV. The GFL_Fault start-up at 0.1999 s against Windows is the difference that Linux x86_64
and macOS also have against Windows (4.6e-9 on macOS); the Pi equals Linux x86_64 there.

Settled values (`comparison_arm_tables.md`, GFM: mean P, Q, f over the last 0.1 s, current and voltage peaks over the
last 0.05 s; SCRX9: final values): 0 flags; the largest relative change against any platform is 5.7e-13 (SCRX
`gENROU.w` against macOS).

SCRX9 against native SCRX on ARM (CSV basis): steady start EFD(0) 1.4351069, max |EFD - EFD(0)| 7.2e-5 (SCRX9 dassl),
max |w| 1.1e-6, GEN1.v range 3.7e-6 before 2 s; `SCRX9_vs_SCRX` DLL minus native EFD 1.22e-6 pu before the fault,
0.0399 pu at the 5 ms samples after it, 7.47e-5 at 10 s; GEN1.v 1.58e-3 and speed 6.28e-5 after the fault. The same
numbers as on macOS and x64.

Timings, ARM over the other platforms (OpenModelica's `timeSimulation` without `LOG_STATS`, median of 3; `translate` =
front end + back end + SimCode + templates; `compile` = `timeCompile`):

| | translate | compile | simulate |
|---|---|---|---|
| Pi over Windows round 2 | 4.35 to 8.39, median 4.92 | 2.54 to 7.32, median 5.80 | 4.13 to 12.20, median 10.02 |
| Pi over Linux x86_64 (WSL2) | 3.93 to 6.87, median 5.65 | 13.53 to 19.41, median 15.69 | 7.50 to 13.87, median 11.97 |
| Pi over macOS arm64 (M2 Pro, self-built omc) | 2.09 to 2.96, median 2.71 | 14.63 to 21.05, median 17.27 | 2.87 to 9.84, median 7.67 |

The Pi's translate ratio against macOS is low because macOS's self-built omc front end is about twice as slow as the
released binaries. The SCRX DASSL runs (0.6 s on the Pi) are dominated by start-up.

## 7. Cross-tool on ARM

None: no System Modeler for Linux arm64, so no OpenModelica-minus-System-Modeler numbers on this machine. The
cross-tool differences measured on x64 and macOS are properties of the tools, not of the platform (macOS record,
section 8).

## 8. Everything that differs from x64 and macOS, and why

1. Platform folder: `aarch64-linux` (omc's `${CMAKE_SYSTEM_PROCESSOR}-linux`), with `linux64` never searched. Patch
   0001 handles it; macOS needs `aarch64-darwin` and `arm64-darwin`.
2. Floating-point contraction: none in the CMake build (gcc ISO C mode); 76 and 3 fused instructions in a GNU-mode gcc
   build, with the large GFM departures of section 3. Patch 0002 keeps the flag explicit.
3. Tool version: OpenModelica 1.27.2 (apt binaries) against 1.27.1 on Windows, Linux x86_64 and macOS. Checked
   against the four commits between the tags; nothing in them touches what the contract runs exercise, and no result
   differs.
4. Compilers: gcc 14.2.0 for the libraries (gcc 15.2 Linux x86_64, MSVC 19.51 Windows, Apple clang 21 macOS); Debian
   clang 19.1.7 for omc's generated code (clang 18.1 Linux x86_64, clang 22.1 Windows, Apple clang macOS); glibc 2.41.
5. Round-off: GFL_Fault's start-up at 4.5e-9 against Windows; every other value at the CSV floor against all three
   platforms (two print units, 7.4e-10, at most, GFL_POCFault against macOS).
6. Timings: 4 to 21 times slower than the other machines (section 6); indicative only.
7. Warnings: gcc 14 reports 7 `-Wmaybe-uninitialized` in `GFM_GFL_IBR.c` beside the 121 unused variables and 2 unused
   parameters; all in the vendor source.

## 9. What is NOT verified

1. System Modeler and Dymola: neither exists for Linux arm64.
2. Figures: no matplotlib on the Pi and no packages installed (Luigi's rule); the parent can render them from the CSVs.
3. OMEdit and the OpenModelica GUI route.
4. A 32-bit Raspberry Pi OS (armhf): not tried; `CMAKE_SYSTEM_PROCESSOR` would be `armv7l` and the folder name
   untested.
5. An omc 1.27.1 on the Pi (the apt repository serves 1.27.2; a downgrade needs Luigi's word and was not asked for,
   since no difference needed it).
6. A clang-built library on the Pi (clang 19 is installed; its contraction default would match macOS's, not measured).
7. Both libraries in one Modelica model (covered by the C `two_libraries_test` only, as on x64).
8. The vendor `-Wmaybe-uninitialized` paths: not analysed (no result depends on them in the 15 runs).

## 10. Decisions for Luigi

D.1 **Patch 0001 on Linux aarch64.** It is required (section 4) and works as decided on 2026-10-31. Proposed: no
    further change; the README sentence of the follow-up pull request names `aarch64-linux` for 64-bit ARM Linux and
    states that `linux64` holds x86-64 binaries only.
D.2 **Patch 0002 (`-ffp-contract=off`).** The Pi adds a gcc case to macOS's clang case: a gcc build in GNU mode
    (gcc's default when no `-std=c11` is given, as in a hand-written `gcc -O2 -fPIC` command) contracts, gives the same
    departures as clang on macOS and changes GFL_VoltageStep's final operating point (section 3).
    Proposed: keep it in the one push you planned after the ARM process, and mention in the README that a build
    outside CMake needs `-ffp-contract=off`.
D.3 **OpenModelica 1.27.2 as the Pi's reference.** Proposed: accept it as recorded (column "OpenModelica 1.27.2
    (arm64 apt, trixie)"); the 1.27.1 to 1.27.2 change list explains nothing here, and the results equal the 1.27.1
    records.
D.4 **Kit folder.** `kit-raspberrypi/` is ready as the `raspberrypi/` folder of `ALSETLab/openipsl-testenv` (same
    shape as `macos/`: `README.md`, `scripts/`, `patches/`, `env/`). Proposed: add it in the same push as the macOS
    folder; nothing is pushed until you say so.

## 11. Files of this record (all under `/home/<pi-user>/arm-verify/`)

- `ARM_LINUX_AARCH64_VERIFICATION.md` (this file); `ENVIRONMENT_2026-11-01.txt`.
- `OpenIPSL/` (the clone, branch `arm-platform-folders`, not pushed; `Resources/Library/aarch64-linux/` untracked);
  `build/ieee_cigre/` (CMake tree); `raw/build/` (configure, build, ctest and install logs).
- `build/fma_variants/` (variant objects, `fma_counts.txt`, `so_gnu11/`); `pkg/fma_gnu11/OpenIPSL` (FMA control
  package); `raw/openmodelica/record_fma_gnu11/` (three FMA control runs, `fma_diff_vs_{record,windows}.txt`);
  `build/om_runs_fma/`; `raw/openmodelica/run_fma_nohup.log`.
- `raw/openmodelica/lookup/` (`LOOKUP_RESULTS.txt` and one run folder per layout).
- `pkg/record/OpenIPSL` (the package under test); `raw/openmodelica/record/` (the 15 runs: CSV, `_metrics.json`,
  `_raw_points.txt`; `logs/<run>/` with `run.mos` and `log.txt`, `logs/<run>_nostats/`, `logs/env.txt`,
  `logs/checks_summary.json`, `logs/unitprobe/`, `logs/init_diag/`, `logs/translate_all/`, `logs/binding.json`,
  `logs/self_comparison.{json,md}`, `logs/runs_table.md`); `build/om_runs/` (omc build trees with the `.mat` results);
  `raw/openmodelica/run_all_nohup.log`; `raw/openmodelica/smoke/`.
- `comparison_final/` (`comparison_arm.json`, `comparison_arm_tables.md`; no figures); `raw/openmodelica/
  compare_final_log.txt`.
- `raw/om_changes/` (`compare_v1.27.1_v1.27.2.json`, `changes_v1.27.1_v1.27.2.txt`, from the GitHub compare API).
- `scripts/` (`omc_verify_pi.py`, `run_all_om_pi.sh`, `compare_arm.py`, `make_pkg.sh`, `probe_folders.sh`,
  `folder_probe.c`, `FolderProbe/`, `UnitProbe.mo`, `runs.json`, `fma_diff.py`).
- `kit-raspberrypi/` (the future `raspberrypi/` folder of `ALSETLab/openipsl-testenv`).
