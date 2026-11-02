*Copy of the project's Linux verification record (2026-10-25), placed here when the kit was made public on 2026-11-01. Machine paths are replaced by placeholders: `<records>` the project's records folder, `<temp>` the Windows temporary folder, `<home>` the Windows user folder, `/home/<user>` the WSL user's home. Files it names under `<records>` are not in this repository.*

# Linux verification of the IEEE/CIGRE DLL package (OpenIPSL `feature/ieee-cigre-dll`, 1244ae93)

Branch `feature/ieee-cigre-dll`, commit `1244ae93` (`1244ae9328d1ff671c6385bbcc922ee4dbd6ea49`), OpenIPSL; the round-2 head that replaces pull
request #362. Record of the Linux verification workflow of 2026-10-25: three tool runs on Linux (records
`linux/dymola/`, `linux/openmodelica/`, `linux/systemmodeler/`, each with its README) and this synthesis
(`linux/compare_linux.py`, `linux/comparison_linux.json`, `linux/comparison_linux_tables.md`, `linux/figs/`,
`linux/experiments/gfl_fault_startup_sensitivity/`). This file is rendered from `linux/synthesis/LINUX_VERIFICATION.src.md`
by `compare_linux.py --render`: every number below is read from `linux/comparison_linux.json` (which also collects the
tool agents' metrics files, their stored-point comparisons and the Windows round-2 numbers), unless a sentence names
another file. Each table names its source. Paths in this file are relative to
`<records>\report\`.

Commit names after the history rewrite of 2026-10-25 ~20:30 (DECISIONS.md: Hao Chang added as co-author to every
commit, before any push): the tested `1244ae93` is now `5cdb045f`, with the identical tree
(`1c723452dc5cc4f8499109b343a02a92ae5c914a` for both, `git rev-parse <commit>^{tree}`). The branch head `501fdf9d`
adds one commit on top, "docs(IEEE_CIGRE): wording that the round-2 measurements contradicted", which changes only
Documentation HTML in `Tests/Controls/IEEE_CIGRE/README.mo` and `SCRX9/SCRX9_vs_SCRX.mo`; no equation, parameter or
annotation that affects a simulation changes, so every Linux result below also holds for `501fdf9d`.

Windows files compared against (read only): `verification_round2/{dymola,openmodelica,systemmodeler}/<run>.csv` and
`<run>_metrics.json` (the 15 contract runs per tool), `verification_round2/systemmodeler/diagnostics/scrx_fix_b48d49e8/`
(System Modeler's two diagnostic runs), `verification_round2/comparison.json` (its cross-tool, steady-start,
DLL-against-native, D.3 and static-check blocks) and `verification_round2/dymola/event_instants.json` (the
disturbance instants). `VERIFICATION_round2.md` was read for context; no number below is copied from it. The Windows
raw result files in `<temp>\cigre_verify\<tool>\round2\` were read too: by the tool agents
for the stored points (section 4.3), by the experiment (section 5), and by this synthesis for OpenModelica's Windows
series rebuilt at full precision (section 4.2) and Dymola's stored time vectors (section 4.3). This synthesis keeps
exact copies of what it took from them in `linux/synthesis/`; section 12 says what cannot be rerun once that Temp
folder is cleaned.

## TL;DR

I built and ran the IEEE/CIGRE DLL package at 1244ae93 on Ubuntu 24.04 (WSL2) in Dymola, OpenModelica and System
Modeler with the shipped linux64 libraries: 43 of 45 runs finish, with the same two System Modeler build failures as on
Windows. Every tool reproduces its Windows result within 4.5e-9
relative (the largest, in GFL_Fault's start-up), with the same events and cross-tool differences. Nothing here holds
the linux64 libraries back.

## Key points

- **Runs.** Linux: Dymola 15/15, OpenModelica 15/15,
  System Modeler 13/15, exactly as on Windows round 2
  (15, 15, 13).
  System Modeler's two failures are master's native `PSSE.ES.SCRX` (alone and inside `SCRX9_vs_SCRX`), which fails at
  the build on both platforms and runs on both with the separate fix b48d49e8 (diagnostic runs). No run came near the
  30-minute cap (longest: OpenModelica GFL_PowerRamp with DASSL, 32.6 s).
- **Each tool against itself on Windows, contract CSV grid.** Largest relative difference over all signals and runs:
  Dymola 4e-10, OpenModelica 4.5e-9,
  System Modeler 9e-10, all three in GFL_Fault's `out[6]` at
  0.1999 s, in the converter's start-up from rest, 1.8 s before the first
  disturbance. The largest of every other run: Dymola 1e-11
  (GFL_FrequencyStep__euler and GFL_PowerRamp__dassl, out[12], max abs 1e-10, one unit of the 12th significant digit there: at the CSV floor), OpenModelica
  1.3e-11 (the series rebuilt from the
  raw results, both platforms at full precision; its 10-digit CSVs give
  4.7e-10, one unit of their last digit), System
  Modeler 1.1e-11. Relative means against Sbase
  for P and Q, 60 Hz for f, 1 pu for speed and the signal's range otherwise.
- **Counts.** Steps, f-evaluations, Jacobians, time events, state events and result points are equal in
  88 of 90 Dymola fields,
  68 of 68 OpenModelica fields and
  51 of 52 System Modeler fields (the
  fields each tool reports, in the runs that finish on both platforms). The three
  exceptions are a stored event pair counted on one platform and not the other (Dymola, +1 and -1 result points at a state
  event 1.08e-12 s after a fault clearing) and DASSL's step choice in System Modeler's GFL_PowerRamp (59031817 against
  59032219 f-evaluations, with the same events and output instants).
- **Why GFL_Fault's start-up is the largest (experiment, section 5).** On Linux alone, raising the source amplitude by
  1e-15 changes `out[6]` (Iqref) by 1.3e-14 before 0.05 s and by
  2.2e-10 at 0.23 s, and the
  change shrinks again after 0.3 s, in the window of the Linux-Windows difference
  (6.7e-15 before 0.05 s,
  9.6e-9 at 0.1999 s).
  The start-up transient amplifies last-bit differences, and the platform difference is consistent with round-off
  amplified by it. The experiment does not show that round-off is all the platform adds: the Linux-Windows difference
  grows more (1.4e6 times against
  1.6e4) and stays larger in 0.3-1 s
  (9.1e-11 against 3e-12;
  the 1e-12 perturbation gives 6.3e-11).
- **Cross-tool on Linux equals cross-tool on Windows.** Above the CSV floor, the worst relative difference per run and
  tool pair differs from the Windows round-2 number by at most
  8.4e-6 of itself
  (OpenModelica - System Modeler,
  GFL_VoltageStep__euler:
  3.409229e-8 against
  3.4092e-8; section 6). The largest change in all,
  0.43 of itself
  (OpenModelica - System Modeler, EMTPTransformerZeroSeq__euler:
  5.878323e-13 against 1.030006e-12),
  is print rounding: its signal `transformer.Ad.v` differs by
  5.71e-9 on Linux and
  1e-8 on Windows, within two units of the 12th digit
  there (a unit is 1e-8), at the CSV floor. Round 2 also took
  OpenModelica from its 12-digit cache: with the Windows OpenModelica series rebuilt at full precision the Windows
  number is 5.878791e-13. The largest change of any key
  signal's cross-tool difference between the platforms is
  3.5e-9 of its scale
  (OpenModelica - System Modeler, GFL_Fault P). No settled value differs between the tools by more than 1e-3 (flags:
  0). GFL_FaultPSCAD's settled Q (D.3) is -71.58891582 Mvar in Dymola
  and System Modeler and -71.58891587 Mvar in OpenModelica, each equal to its
  Windows value.
- **SCRX9 DLL against master's native SCRX** gives Windows' numbers in every tool: on the same SMIB, DLL minus native EFD
  1.03e-6 pu before the fault and
  0.0399 pu at the 5 ms samples
  after it (Dymola; OpenModelica 0.0399).
- **How the executables find `lib<Name>.so`** differs per tool: Dymola writes a
  DT_RUNPATH, OpenModelica a DT_RPATH with seven folders (`linux64` is the sixth), System Modeler none, so a System
  Modeler executable run outside the tool needs `LD_LIBRARY_PATH=<OpenIPSL>/Resources/Library/linux64` (section 2).
  The shipped `.so` files need glibc symbol versions up to `GLIBC_2.4`; built on glibc 2.43, they load on 2.39.
- **Cost.** Simulation wall time, Linux over Windows: Dymola 0.59-1.29
  (median 0.89), OpenModelica 0.53-1.23
  (median 0.89), System Modeler 0.32-0.79
  (median 0.38). Both platforms ran the three tool agents at
  once, so these are indicative.
- **One setting had to be matched by hand.** The Windows round-2 Dymola runs had `Evaluate = true` from a persistent
  flag in Luigi's Windows `setup.dymx`, not from their scripts; the Linux runs set it explicitly. With Dymola's default
  `false` the translation differs and the transformer tests take about 3 times as long (Dymola record, section 9).

## 1. Environment and how to reproduce

### 1.1 Platform and tools (source: `tools` in comparison_linux.json, from the GFL_Fault metrics files; the kit README)

| Item | Linux (this record) | Windows round 2 |
|---|---|---|
| Machine | the same PC: Intel Core Ultra 9 285K, 24 vCPUs and 62 GB RAM in WSL2 | Windows 11 Pro |
| OS | WSL2 distro `openipsl-verify-24.04`, Ubuntu 24.04.5 LTS, glibc 2.39, kernel 6.18.33.2-microsoft-standard-WSL2, user `luigi` without sudo; `platform` field: linux64, Ubuntu 24.04.5, glibc 2.39 | Windows 11 |
| Kit | `linux-env` version 0.1.0 (`linux-env\VERSION`); its `provision`, `windows` and `smoke` folders and `site.env` unchanged by this workflow (the tool agents added `tests/<tool>/`) | - |
| Package | `1244ae93` exported read-only by `linux-env/tests/export_package.sh` to `/home/<user>/cigre_verify/pkg/1244ae93/OpenIPSL`; `libSCRX9.so` SHA-256 `974323eb...`, `libGFM_GFL_IBR.so` `2591aa18...`, equal to the worktree's | `git archive` export of the same commit |
| Dymola | Dymola Version 2026x Refresh 1, 2026-04-08; MSL 4.1.0 (the only MSL in Dymola 2026x Refresh 1 for Linux, /opt/dymola-2026xRefresh1-x86_64/Modelica/Library/Modelica 4.1.0/package.mo; OpenIPSL uses 4.0.0, Dymola reports no conversion needed) | Dymola Version 2026x Refresh 1, 2026-04-08 |
| Dymola compiler | GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 (dymosim .comment; dsbuild.sh "Using CC=cc -Wl,--no-as-needed", cc -> /usr/bin/x86_64-linux-gnu-gcc-13); dsbuild.sh defaults, no user options: -O1 -D_LINUX64 -DUNIX -DSkip_f2c_Undefs, PIE (Ubuntu gcc default), -Wl,--no-as-needed -Wl,--no-undefined -Wl,--allow-multiple-definition; the library linked with -L<pkg>/Resources/Library/linux64 -Wl,-rpath=<same> -l<Name> (DT_RUNPATH) | MSVC, Visual Studio 18 Community, 64-bit |
| OpenModelica | OpenModelica 1.27.1 (apt `omc 1.27.1-1`); MSL 4.0.0 | OpenModelica v1.27.1 (64-bit) |
| OpenModelica compiler | clang 18.1.3 (Ubuntu clang version 18.1.3 (1ubuntu1); /usr/bin/clang -> /usr/lib/llvm-18/bin/clang; CC=clang in the generated makefile, -Os); links Ubuntu's reference LAPACK/BLAS 3.12.0 | clang 22.1.4 of MSYS2 ucrt64 (generated makefile CC=clang; the round-1 record said gcc 16.1.0); OpenBLAS |
| System Modeler | System Modeler 15.0.0 for Linux (standalone kernel WSMKernelX --version 15.0.0.4, installation .VersionID 15.0.0.0); no WSMLink (System Modeler for Linux ships no Wolfram kernel); MSL 4.0.0 | System Modeler 15.0 (standalone kernel WSMKernelX.exe, Simulation Center 15.0.0.6; WSMLink 15.0.0 / Wolfram 15.0.1 for validation and the cross-check) |
| System Modeler compiler | g++ through /opt/openipsl-kit/bin/g++-nopie (runs /usr/bin/g++, adds -no-pie when linking an executable); g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0 | MSVC cl 19.44.35229 x64 (Visual Studio 2022 Build Tools), /MT |
| Shipped libraries | `Resources/Library/linux64/lib{SCRX9,GFM_GFL_IBR}.so`, gcc 15.2.0 on Ubuntu 26.04.1 (glibc 2.43); NEEDED `libc.so.6` (and `libm.so.6` for GFM), SONAME `lib<Name>.so`, `-Bsymbolic`, glibc symbol versions `GLIBC_2.2.5`, `GLIBC_2.3.4`, `GLIBC_2.4` (`linux/smoke/10_shipped_libs.txt`, `linux/openmodelica/logs/env.txt`, `build_c.md`) | `Resources/Library/win64/<Name>.{dll,lib}`, MSVC 19.51, `/MT` |
| Load | the three tool agents ran in the same distro at the same time (load average 1.4-4.2 of 24 CPUs, in the tool READMEs) | the three Windows agents ran at the same time |

### 1.2 How to reproduce (the kit README `linux-env\README.md`, then the tool folders)

Preconditions: the licence servers of Dymola and System Modeler (the VPN), one Dymola or System Modeler instance at a
time; an OpenIPSL clone, for the `SCRX.mo` of b48d49e8 (step 4); the Windows round-2 raw results in
`<temp>\cigre_verify\{dymola,openmodelica,systemmodeler}\round2\` for the stored-point
comparisons of steps 3 and 4 and for the experiment of step 5 (section 12, item 11). Every command below is run from
Windows; in Git Bash prefix it with `MSYS_NO_PATHCONV=1`. Abbreviations: `<kit>` =
`<records>/linux-env`, `<pkg>` = `/home/<user>/cigre_verify/pkg/1244ae93/OpenIPSL`,
`<rec>` = `<records>/report/linux`, `<W>` =
`<records>/report/verification_round2`, `wsl` =
`wsl.exe -d openipsl-verify-24.04 -e`.

1. Copy `linux-env\site.env.example` to `site.env` (installer paths, licence servers, user, OpenIPSL repository), then
   from a Windows terminal in the kit folder: `powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1`
   (creates `openipsl-verify-24.04` and runs `provision/00_base.sh`, `10_openmodelica.sh`, `20_dymola.sh`,
   `30_systemmodeler.sh`, `40_licences.user.sh`).
2. Smoke tests and the package export, in the kit README's order:
   - `wsl bash <kit>/tests/smoke/00_distro.sh`
   - `wsl bash <kit>/tests/export_package.sh 1244ae93`
   - `wsl bash <kit>/tests/smoke/10_shipped_libs.sh <pkg>`
   - `wsl bash <kit>/tests/smoke/20_openmodelica.sh <pkg>`
   - `wsl /opt/openipsl-kit/venv-dymola/bin/python -I <kit>/tests/smoke/30_dymola.py <pkg> <kit>/site.env`
   - `wsl env WSM_CXX=/opt/openipsl-kit/bin/g++-nopie bash <kit>/tests/smoke/40_systemmodeler.sh <pkg>`
3. The contract runs, one tool after the other (`linux-env/tests/<tool>/README.md`):
   - `wsl bash <kit>/tests/openmodelica/run_all.sh <pkg> <rec>/openmodelica`
   - `wsl bash <kit>/tests/dymola/run_all.sh <pkg> <rec>/dymola`
   - `wsl bash <kit>/tests/systemmodeler/run_all.sh <pkg> <rec>/systemmodeler`

   The OpenModelica and Dymola drivers also make their static checks, their binding diagnostics and their
   stored-point comparison with the Windows raw results (section 4.3). System Modeler's `run_all.sh` makes only the
   15 contract runs; the rest of its record is step 4.
4. The extra sets of the record, which step 3 does not make:
   - Dymola with `Evaluate = false` (section 11.7, `linux/dymola/evaluate_false/`):
     `wsl env EVALUATE=false BUILD=/home/<user>/cigre_verify/dymola/evaluate_false "STEPS=checks runs compare" bash <kit>/tests/dymola/run_all.sh <pkg> /home/<user>/cigre_verify/dymola/evaluate_false/record`,
     then that record without its CSVs copied to `<rec>/dymola/evaluate_false/` (Dymola record, section 9.E).
   - System Modeler, the full "How to run" block of `linux-env/tests/systemmodeler/README.md`, in this order: the two
     default-g++ runs of section 11.4
     (`wsl bash <kit>/tests/systemmodeler/run_all.sh <pkg> <rec>/systemmodeler/default_gpp --compiler default --work /home/<user>/cigre_verify/systemmodeler/runs_default_gpp --stage /home/<user>/cigre_verify/systemmodeler/record_default_gpp SCRX9__dassl GFL_Fault__euler`),
     the validation of section 9 (`wsl bash <kit>/tests/systemmodeler/run_validation.sh <pkg> <rec>/systemmodeler <W>/systemmodeler/logs/wsm_validate.json`),
     the b48d49e8 diagnostics of sections 3, 4, 6 and 7 (`wsl bash <kit>/tests/systemmodeler/run_diag_scrxfix.sh <pkg> <SCRX.mo of b48d49e8> <rec>/systemmodeler/diagnostics/scrx_fix_b48d49e8`),
     the probes of section 2 (`wsl bash <kit>/tests/systemmodeler/probes.sh <pkg> <rec>/systemmodeler`) and the
     comparisons of sections 4.3 and 11.4
     (`wsl bash <kit>/tests/systemmodeler/run_analysis.sh <rec>/systemmodeler <W>/systemmodeler <temp>/cigre_verify/systemmodeler/round2/runs`).
     The `SCRX.mo` of b48d49e8 comes read-only from an OpenIPSL clone:
     `git -C <clone> show b48d49e8:OpenIPSL/Electrical/Controls/PSSE/ES/SCRX.mo > SCRX_b48d49e8.mo`, SHA-256
     `8a7c618928ca1348a8c5981d328c1f274874345c5d26dc0950d124a315d6a16c`. Without the diagnostics, `compare_linux.py`
     writes other cross-tool, steady-start and DLL-against-native blocks for the two native-SCRX runs.
5. This synthesis and the experiment of section 5:
   - `wsl bash <rec>/run_compare_linux.sh` (stages in `~/cigre_verify/synthesis/out`, renders this file from
     `synthesis/LINUX_VERIFICATION.src.md`, copies with `cp`). It reads the Linux build trees and the Windows
     OpenModelica and Dymola raw results; with `--no-raw`, or where those files are missing, it uses the exact caches
     of `linux/synthesis/` (`openmodelica_rebuilt/`, `openmodelica_rebuilt_windows/`, `dymola_time_vectors.json`) and
     writes the same numbers.
   - `wsl bash <rec>/experiments/gfl_fault_startup_sensitivity/run.sh` (the Linux OpenModelica build tree and the
     Windows OpenModelica GFL_Fault result).

Never pass a one-liner through `wsl.exe -- bash -c '...'` from PowerShell: wsl.exe parses the line again and
`$variables` are lost. Write a script and run it with `-e bash <script>`.

## 2. How each tool found `lib<Name>.so` (sources: `binding` in comparison_linux.json and the tool READMEs, section named in each cell)

| | Dymola 2026x Refresh 1 | OpenModelica 1.27.1 | System Modeler 15.0 |
|---|---|---|---|
| What the model code records | `dsmodel.c`: the absolute file in `dllLibraryPath[]` under `#elif !defined(_WIN32) && defined(__x86_64__)`: `/home/<user>/cigre_verify/pkg/1244ae93/OpenIPSL/Resources/Library/linux64/libSCRX9.so` (`extra/build/dsmodel_dllLibraryPath`) | the generated makefile derives seven `-L`/`-Wl,-rpath` folders from `LibraryDirectory`: `/usr/bin/../lib/x86_64-linux-gnu/omc`, `/usr/bin/../lib/`, `~/.openmodelica/binaries/OpenIPSL`, `Resources/Library/`, `Resources/Library/x86_64-linux`, `Resources/Library/linux64`, `Resources/Library` (`library_binding/link_rpath`) | the `.sim` lists `<Library name="libSCRX9.so" uri="modelica://OpenIPSL/Resources/Library/linux64" path="<pkg>/Resources/Library/linux64"/>` (`wsm_sim_external_libraries`) |
| Link line (build time) | `dsbuild.sh -L '<pkg>/Resources/Library/linux64' -l SCRX9` turns into one `cc` call: `-Wl,-rpath=<pkg>/Resources/Library/linux64 ... -L<pkg>/Resources/Library/linux64 -lSCRX9 -lSCRX9 -lds ...` (gcc 13.3, `-O1`, PIE; `logs\strace_SCRX9.txt`, README section 2) | `clang ... -L<the seven folders> -Wl,-rpath=<the seven folders> -lSCRX9`, `RUNTIME_LIBS` with `-Wl,--disable-new-dtags`; `ld --verbose`: "attempt to open .../Resources/Library/linux64/libSCRX9.so succeeded" after 12 failed attempts (README section 3.1) | `g++-nopie ... -L<WSM>/lib/linux64 -L<pkg>/Tests/Controls/IEEE_CIGRE/SCRX9 -L<pkg>/Resources/Library/linux64 -L<pkg>/Resources/Library/linux64 -lSCRX9 -lmmcom -lsim ...`, no `-Wl,-rpath` (`wsm_link_line`, from the kernel's own ninja file) |
| Dynamic section of the executable | NEEDED `libSCRX9.so`, `libds.so`, `libstdc++.so.6`, `libm.so.6`, `libc.so.6`; **DT_RUNPATH** `<pkg>/Resources/Library/linux64:<dymola>/bin/lib64` (Ubuntu's ld writes new dtags); no DT_RPATH | NEEDED `libSCRX9.so`, `libSimulationRuntimeC.so`, `liblapack.so.3`, `libblas.so.3`, `libm.so.6`, `libomcgc.so.1`, `libc.so.6`; **DT_RPATH** (`RPATH`) with the seven folders plus `/usr/bin/../lib`, `linux64` sixth | NEEDED `libSCRX9.so`, `libstdc++.so.6`, `libm.so.6`, `libgcc_s.so.1`, `libc.so.6`; **no RUNPATH, no RPATH** (`wsm_executable/has_runpath` = no) |
| `ldd` without any environment | `libSCRX9.so => <pkg>/Resources/Library/linux64/libSCRX9.so` | `libSCRX9.so => <pkg>/Resources/Library/linux64/libSCRX9.so` | `libSCRX9.so => not found`; run by hand the executable exits 127 with "error while loading shared libraries: libSCRX9.so: cannot open shared object file" (`diagnostics/probes/probes.txt` P1) |
| Run time | `LD_DEBUG=libs`, `LD_LIBRARY_PATH` unset: "search path=...linux64...(RUNPATH from file ./dymosim)", one `calling init`, no second `dlopen` by `DymosimEnsureDLLLoaded` (README section 2.4) | `LD_DEBUG=libs` inside omc's own `simulate()`: "(RPATH from file .../GFL_Fault)", 18 "trying file=" lines, the last `.../linux64/libGFM_GFL_IBR.so`; `LD_LIBRARY_PATH` unset in the environment and absent from the trace (README section 3.2) | the runner sets `LD_LIBRARY_PATH` = `/home/<user>/cigre_verify/pkg/1244ae93/OpenIPSL/Resources/Library/linux64` (the `.sim` path), the role `PATH` has on Windows; the kernel's own evaluator (translation-time `sampleTime()`, `count()`) also has no RUNPATH and works only under the kernel (README section 3) |
| Environment needed | none | none | `LD_LIBRARY_PATH=<OpenIPSL>/Resources/Library/linux64` outside the tool; whether Simulation Center sets it was not measured |
| What a user should know | the absolute package path is compiled in (RUNPATH and `dllLibraryPath[]`): a `dymosim` moved within the machine still finds the library; a moved or deleted package, or a `dymosim` copied to a machine without the package at that path, needs `LD_LIBRARY_PATH` (not run) | DT_RPATH is searched before `LD_LIBRARY_PATH` and puts five folders before `linux64`: OpenModelica's two library folders (`/usr/bin/../lib/x86_64-linux-gnu/omc`, `/usr/bin/../lib/`), then `~/.openmodelica/binaries/OpenIPSL`, `Resources/Library/` and `Resources/Library/x86_64-linux`; the loader tries their 15 candidate files before the three of `linux64` (README section 3.2), so a stale `lib<Name>.so` in any of them would shadow the shipped one | see the row above |
| Windows round 2, for contrast | the absolute `win64\<Name>.dll` in `dllLibraryPath[]`, delay-loaded | the MSVC import library `-L.../win64 -l<Name>`, the generated `.bat` puts `win64` on PATH | the `.sim` lists the folder, the runner puts it on PATH |

The GFM tests are the same with `libGFM_GFL_IBR.so`. The two network-only tests and master's native SCRX link no
external library.

## 3. What was run (source: `runs/<run>/outcome`, `meta/event_instants_check`)

Same 15 runs as Windows round 2, per tool, with the same solvers, steps, tolerances (1e-6), output intervals, CSV grids
(1 ms for the SCRX tests, 0.1 ms otherwise) and signal names (the tool agents checked the CSV headers; the column
"rows" of section 4 repeats it). L / W = Linux / Windows outcome.

| run | test (OpenIPSL.Tests.Controls.) | solver | DLL Ts (s) | stop (s) | disturbance instants (s) | Dymola L / W | OpenModelica L / W | System Modeler L / W |
|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | IEEE_CIGRE.SCRX9.SCRX9 | dassl | 0.005 | 10 | 2.0025, 2.1525 | ok / ok | ok / ok | ok / ok |
| SCRX9__euler | IEEE_CIGRE.SCRX9.SCRX9 | euler | 0.005 | 10 | 2.0025, 2.1525 | ok / ok | ok / ok | ok / ok |
| SCRX9_vs_SCRX__dassl | IEEE_CIGRE.SCRX9.SCRX9_vs_SCRX | dassl | 0.005 | 10 | 2.0025, 2.1525 | ok / ok | ok / ok | failed / failed (diagnostic with b48d49e8: ok / ok) |
| SCRX__dassl | PSSE.ES.SCRX | dassl | 0.005 | 10 | 2, 2.15 | ok / ok | ok / ok | failed / failed (diagnostic with b48d49e8: ok / ok) |
| GFL_Fault__euler | IEEE_CIGRE.GFM.GFL_Fault | euler | 1e-5 | 5.8 | 2.000005, 5.000005, 5.100005 | ok / ok | ok / ok | ok / ok |
| GFL_POCFault__euler | IEEE_CIGRE.GFM.GFL_POCFault | euler | 1e-5 | 4 | 2.000005, 3.000005, 3.100005 | ok / ok | ok / ok | ok / ok |
| GFL_FrequencyStep__euler | IEEE_CIGRE.GFM.GFL_FrequencyStep | euler | 1e-5 | 3 | 2.000005 | ok / ok | ok / ok | ok / ok |
| GFL_VoltageStep__euler | IEEE_CIGRE.GFM.GFL_VoltageStep | euler | 1e-5 | 3 | 2.000005 | ok / ok | ok / ok | ok / ok |
| GFL_PowerRamp__euler | IEEE_CIGRE.GFM.GFL_PowerRamp | euler | 1e-5 | 3.6 | 2.000005, 2.800005 | ok / ok | ok / ok | ok / ok |
| GFL_FaultPSCAD__euler | IEEE_CIGRE.GFM.GFL_FaultPSCAD | euler | 1e-5 | 5.8 | 2.000005, 5.000005, 5.100005 | ok / ok | ok / ok | ok / ok |
| GFM_EMTPFault__euler | IEEE_CIGRE.GFM.GFM_EMTPFault | euler | 1e-5 | 5.9 | 2.000005, 5.000005, 5.100005 | ok / ok | ok / ok | ok / ok |
| GFM_EMTPFull__euler | IEEE_CIGRE.GFM.GFM_EMTPFull | euler | 1e-5 | 6 | 2.000005, 5.000005, 5.100005 | ok / ok | ok / ok | ok / ok |
| EMTPTransformerZeroSeq__euler | IEEE_CIGRE.GFM.Components.EMTPTransformerZeroSeq | euler | 1e-5 | 3 | - | ok / ok | ok / ok | ok / ok |
| SmoothShortFault__euler | IEEE_CIGRE.GFM.Components.SmoothShortFault | euler | 1e-5 | 5.5 | 5, 5.03 | ok / ok | ok / ok | ok / ok |
| GFL_PowerRamp__dassl | IEEE_CIGRE.GFM.GFL_PowerRamp | dassl | 1e-5 | 3.6 | 2.000005, 2.800005 | ok / ok | ok / ok | ok / ok |

The disturbance instants are the table of `verification_round2/compare.py`; against the Windows
`event_instants.json`:

| run | disturbance instants used (s) | against event_instants.json |
|---|---|---|
| SCRX9__dassl | 2.0025, 2.1525 | equal |
| SCRX9__euler | 2.0025, 2.1525 | equal |
| SCRX9_vs_SCRX__dassl | 2.0025, 2.1525 | equal |
| SCRX__dassl | 2, 2.15 | equal |
| GFL_Fault__euler | 2.000005, 5.000005, 5.100005 | equal |
| GFL_POCFault__euler | 2.000005, 3.000005, 3.100005 | equal |
| GFL_FrequencyStep__euler | 2.000005 | equal |
| GFL_VoltageStep__euler | 2.000005 | equal |
| GFL_PowerRamp__euler | 2.000005, 2.800005 | the json has no entry at 2.800005 s (it lists: P ramp starts; Q ramp starts) |
| GFL_FaultPSCAD__euler | 2.000005, 5.000005, 5.100005 | equal |
| GFM_EMTPFault__euler | 2.000005, 5.000005, 5.100005 | equal |
| GFM_EMTPFull__euler | 2.000005, 5.000005, 5.100005 | equal |
| EMTPTransformerZeroSeq__euler | - | equal (no disturbance; no entry in the json) |
| SmoothShortFault__euler | 5, 5.03 | equal |
| GFL_PowerRamp__dassl | 2.000005, 2.800005 | the json has no entry at 2.800005 s (it lists: P ramp starts; Q ramp starts) |

The json lists the instants its script measured; the end of GFL_PowerRamp's ramps (2.800005 s) is not among them,
so the table of `compare.py` is used, as on Windows.

## 4. Linux against Windows, the same tool (source: `runs/<run>/linux_vs_windows`, `runs/<run>/metrics_delta`, `summary`)

Differences are Linux minus Windows on the common CSV grid. "excl." leaves out the grid points within one DLL sample
(Ts) of a disturbance instant. "rel" is relative to Sbase for P and Q, 60 Hz for f, 1 pu for speed and the Windows
signal's range otherwise (for `transformer.VabcSum.y`, zero by construction, the range of `transformer.Ad.v`). The CSVs
print 12 significant digits (Dymola, System Modeler) or 10 (OpenModelica), so about 1e-12 (1e-10) of a value is the
floor of this comparison. A difference within two units of the last printed digit at the instant of its maximum is
marked "at the CSV floor" (`at_floor` in comparison_linux.json; tables 4.1 and 6): the comparison cannot resolve it.
Per-signal numbers (max, RMS, time of the max, before the first disturbance, final values) are in
comparison_linux.json.

### 4.1 Summary

| tool | runs compared | largest relative difference (run, signal, t) | largest of the other runs | largest with +-Ts of disturbances excluded | runs with identical CSV values | count fields of the runs ok on both |
|---|---|---|---|---|---|---|
| Dymola | 15 | GFL_Fault__euler, out[6]: 4e-10 (0.1999 s) | GFL_FrequencyStep__euler, out[12]: 1e-11 (tie with GFL_PowerRamp__dassl; at the 12-digit CSV floor) | GFL_Fault__euler, out[6]: 4e-10 | SmoothShortFault__euler | 88 equal, 2 different |
| OpenModelica | 15 | GFL_Fault__euler, out[6]: 4.5e-9 (0.1999 s) | GFL_FaultPSCAD__euler, grid_sensor_a.current: 4.7e-10 (at the 10-digit CSV floor) | GFL_Fault__euler, out[6]: 4.5e-9 | SmoothShortFault__euler | 68 equal, 0 different |
| System Modeler | 13 | GFL_Fault__euler, out[6]: 9e-10 (0.1999 s) | GFL_VoltageStep__euler, out[6]: 1.1e-11 | GFL_Fault__euler, out[6]: 9e-10 | none | 51 equal, 1 different |
| OpenModelica (rebuilt) | 15 | GFL_Fault__euler, out[6]: 4.5e-9 (0.1999 s) | GFL_PowerRamp__dassl, grid_sensor_c.current: 1.3e-11 | GFL_Fault__euler, out[6]: 4.5e-9 | none | - |
| System Modeler (with b48d49e8) | 2 | SCRX__dassl, gENROU.ETERM: 8.7e-11 (4.115 s) | SCRX9_vs_SCRX__dassl, dll.gENROU.ETERM: 1.4e-11 (at the 12-digit CSV floor) | SCRX__dassl, gENROU.ETERM: 8.7e-11 | none | 6 equal, 2 different |

Count fields that differ (all others equal):

| tool | run | field | Linux | Windows | L - W |
|---|---|---|---|---|---|
| Dymola | SCRX9_vs_SCRX__dassl | result_points | 4009 | 4008 | +1 |
| Dymola | SCRX__dassl | result_points | 2007 | 2008 | -1 |
| System Modeler | GFL_PowerRamp__dassl | f_evaluations | 59031817 | 59032219 | -402 |
| System Modeler (with b48d49e8) | SCRX9_vs_SCRX__dassl | f_evaluations | 238534 | 238573 | -39 |
| System Modeler (with b48d49e8) | SCRX__dassl | f_evaluations | 11153 | 11108 | +45 |

- Dymola's two result-point differences: the native exciter's limiter leaves its limit in a state event 1.08e-12 s
  after the clearing time event; Linux stores that event as a pre/post pair in SCRX9_vs_SCRX and Windows in the native
  SCRX test (Dymola record, section 8.D.3). Event counts are equal; the stored values agree to 12 digits.
- System Modeler's DASSL f-evaluations: DASSL's step-size control feels the round-off; the events and the output
  instants are the same (System Modeler record, section 5).

### 4.2 Per tool, every run

Dymola (`linux/dymola/`, `verification_round2/dymola/`):

| run | rows L / W | CSV digits L / W | signals identical | worst signal (all points) | max abs | t of max (s) | rel | RMS of it | worst rel, excl. +-Ts of disturbances | worst rel before the first disturbance |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | 10001 / 10001 | 12 / 12 | 2 of 6 | gENROU.PELEC | 1e-12 | 4.626 | 1.1e-12 | 1.7e-14 | gENROU.PELEC, 1.1e-12 | gENROU.w, 5e-18 |
| SCRX9__euler | 10001 / 10001 | 12 / 12 | 2 of 6 | gENROU.ETERM | 1e-12 | 3.258 | 1.4e-12 | 1.7e-14 | gENROU.ETERM, 1.4e-12 | gENROU.w, 1.4e-17 |
| SCRX9_vs_SCRX__dassl | 10001 / 10001 | 12 / 12 | 2 of 8 | native.gENROU.ETERM | 1e-12 | 5.454 | 1.4e-12 | 1e-14 | native.gENROU.ETERM, 1.4e-12 | dll.gENROU.w, 1e-17 |
| SCRX__dassl | 10001 / 10001 | 12 / 12 | 0 of 6 | sCRX.EFD | 2e-11 | 2.087 | 2e-12 | 8.2e-13 | sCRX.EFD, 2e-12 | gENROU.PELEC, 1.1e-12 |
| GFL_Fault__euler | 58001 / 58001 | 12 / 12 | 6 of 21 | out[6] | 8.7e-10 | 0.1999 | 4e-10 | 1.5e-11 | out[6], 4e-10 | out[6], 4e-10 |
| GFL_POCFault__euler | 40001 / 40001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 1.2633 | 9.2e-12 | 1.3e-13 | out[8], 9.2e-12 | out[8], 9.2e-12 |
| GFL_FrequencyStep__euler | 30001 / 30001 | 12 / 12 | 3 of 21 | out[12] | 1e-10 | 0.169 | 1e-11 | 1.9e-12 | out[12], 1e-11 | out[12], 1e-11 |
| GFL_VoltageStep__euler | 30001 / 30001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 1.5873 | 9.9e-12 | 6.1e-14 | out[8], 9.9e-12 | out[8], 9.9e-12 |
| GFL_PowerRamp__euler | 36001 / 36001 | 12 / 12 | 3 of 21 | grid_sensor_b.current | 1e-8 | 0.0807 | 2.8e-12 | 1.2e-10 | grid_sensor_b.current, 2.8e-12 | grid_sensor_b.current, 2.8e-12 |
| GFL_FaultPSCAD__euler | 58001 / 58001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 3.7347 | 9.3e-12 | 1.3e-13 | out[8], 9.3e-12 | out[9], 3.4e-12 |
| GFM_EMTPFault__euler | 59001 / 59001 | 12 / 12 | 3 of 21 | out[10] | 1e-10 | 1.5901 | 1.7e-12 | 4.1e-13 | out[10], 1.7e-12 | out[10], 1.7e-12 |
| GFM_EMTPFull__euler | 60001 / 60001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 3.9888 | 9.2e-12 | 4.3e-14 | out[8], 9.2e-12 | out[5], 3.2e-12 |
| EMTPTransformerZeroSeq__euler | 30001 / 30001 | 12 / 12 | 0 of 11 | tr.Ad.i | 1e-10 | 1.6474 | 1e-12 | 1e-12 | tr.Ad.i, 1e-12 | tr.Ad.i, 1e-12 |
| SmoothShortFault__euler | 55001 / 55001 | 12 / 12 | 6 of 6 | ssf.A.v | 0 | 0 | 0 | 0 | ssf.A.v, 0 | ssf.A.v, 0 |
| GFL_PowerRamp__dassl | 36001 / 36001 | 12 / 12 | 3 of 21 | out[12] | 1e-10 | 0.2474 | 1e-11 | 6.8e-12 | out[12], 1e-11 | out[12], 1e-11 |

| run | outcome L / W | steps | f-evals | Jacobians | time events | state events | result points | translate L / W (s) = ratio | compile L / W (s) = ratio | simulate wall L / W (s) = ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | ok / ok | = 20909 | = 22619 | = 18648 | = 2002 | = 0 | = 4005 | 0.293 / 0.241 = 1.22 | 1.87 / 2.32 = 0.81 | 1.87 / 1.92 = 0.98 |
| SCRX9__euler | ok / ok | = 2000 | = 2000 | = 0 | = 2000 | = 0 | = 4000 | 0.257 / 0.239 = 1.08 | 2.07 / 2.3 = 0.90 | 0.212 / 0.237 = 0.89 |
| SCRX9_vs_SCRX__dassl | ok / ok | = 21506 | = 23396 | = 19125 | = 2002 | = 2 | 4009 / 4008 (+1) | 0.283 / 0.35 = 0.81 | 2.07 / 2.12 = 0.98 | 3.93 / 4.26 = 0.92 |
| SCRX__dassl | ok / ok | = 462 | = 890 | = 70 | = 2 | = 2 | 2007 / 2008 (-1) | 0.204 / 0.28 = 0.73 | 1.79 / 2.05 = 0.87 | 0.153 / 0.119 = 1.29 |
| GFL_Fault__euler | ok / ok | = 580000 | = 580000 | = 0 | = 580000 | = 0 | = 1160001 | 0.211 / 0.302 = 0.70 | 1.74 / 2.1 = 0.82 | 1.58 / 2.36 = 0.67 |
| GFL_POCFault__euler | ok / ok | = 400000 | = 400000 | = 0 | = 400000 | = 0 | = 800001 | 0.313 / 0.375 = 0.83 | 1.8 / 2.05 = 0.88 | 1.8 / 2.89 = 0.62 |
| GFL_FrequencyStep__euler | ok / ok | = 300000 | = 300000 | = 0 | = 300000 | = 0 | = 600001 | 0.281 / 0.331 = 0.85 | 1.68 / 1.91 = 0.88 | 1.03 / 1.5 = 0.69 |
| GFL_VoltageStep__euler | ok / ok | = 300000 | = 300000 | = 0 | = 300000 | = 0 | = 600001 | 0.29 / 0.32 = 0.91 | 4.04 / 2.11 = 1.92 | 0.991 / 1.37 = 0.72 |
| GFL_PowerRamp__euler | ok / ok | = 360000 | = 360000 | = 0 | = 360000 | = 0 | = 720001 | 0.271 / 0.308 = 0.88 | 1.82 / 1.9 = 0.96 | 1.42 / 1.7 = 0.83 |
| GFL_FaultPSCAD__euler | ok / ok | = 580000 | = 580000 | = 0 | = 580000 | = 0 | = 1160001 | 0.237 / 0.277 = 0.86 | 1.75 / 1.89 = 0.93 | 1.59 / 1.68 = 0.95 |
| GFM_EMTPFault__euler | ok / ok | = 590000 | = 590000 | = 0 | = 590000 | = 0 | = 1180001 | 0.246 / 0.336 = 0.73 | 1.73 / 1.88 = 0.92 | 2.37 / 2.9 = 0.82 |
| GFM_EMTPFull__euler | ok / ok | = 600000 | = 600000 | = 0 | = 600000 | = 0 | = 1200001 | 0.288 / 0.391 = 0.74 | 1.75 / 1.84 = 0.95 | 2.77 / 4.68 = 0.59 |
| EMTPTransformerZeroSeq__euler | ok / ok | = 300000 | = 300000 | = 0 | = 0 | = 0 | = 30002 | 0.229 / 0.282 = 0.81 | 1.6 / 1.83 = 0.88 | 0.196 / 0.177 = 1.11 |
| SmoothShortFault__euler | ok / ok | = 550000 | = 550000 | = 0 | = 2 | = 3 | = 55010 | 0.263 / 0.372 = 0.71 | 1.61 / 2.05 = 0.79 | 0.376 / 0.376 = 1.00 |
| GFL_PowerRamp__dassl | ok / ok | = 7477801 | = 11932197 | = 4590259 | = 360002 | = 0 | = 720004 | 0.262 / 0.322 = 0.81 | 1.65 / 2.05 = 0.80 | 16.7 / 17.4 = 0.96 |

Dymola's `compile_s` differs in meaning: on Linux Dymola reports 0.0015 s, which does not cover the gcc build, so the
Linux record measures the build from the file times; the Windows figure is Dymola's own and covers the MSVC build.

OpenModelica, the CSVs as recorded (`linux/openmodelica/`, `verification_round2/openmodelica/`):

| run | rows L / W | CSV digits L / W | signals identical | worst signal (all points) | max abs | t of max (s) | rel | RMS of it | worst rel, excl. +-Ts of disturbances | worst rel before the first disturbance |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | 10001 / 10001 | 10 / 10 | 4 of 6 | gENROU.PELEC | 1e-11 | 2.826 | 1.1e-11 | 1e-13 | gENROU.PELEC, 1.1e-11 | gENROU.w, 1e-16 |
| SCRX9__euler | 10001 / 10001 | 10 / 10 | 5 of 6 | gENROU.w | 1e-16 | 0.382 | 1e-16 | 7.3e-18 | gENROU.w, 1e-16 | gENROU.w, 1e-16 |
| SCRX9_vs_SCRX__dassl | 10001 / 10001 | 10 / 10 | 5 of 8 | native.sCRX.EFD | 1e-11 | 3.302 | 1e-12 | 1e-13 | native.sCRX.EFD, 1e-12 | dll.gENROU.w, 1e-16 |
| SCRX__dassl | 10001 / 10001 | 10 / 10 | 0 of 6 | gENROU.ETERM | 1e-10 | 6.427 | 1.4e-10 | 1.4e-12 | gENROU.ETERM, 1.4e-10 | gENROU.PELEC, 1.1e-10 |
| GFL_Fault__euler | 58001 / 58001 | 10 / 10 | 6 of 21 | out[6] | 9.6e-9 | 0.1999 | 4.5e-9 | 1.8e-10 | out[6], 4.5e-9 | out[6], 4.5e-9 |
| GFL_POCFault__euler | 40001 / 40001 | 10 / 10 | 6 of 21 | out[11] | 1e-9 | 1.0065 | 1e-10 | 1.6e-11 | out[11], 1e-10 | out[11], 1e-10 |
| GFL_FrequencyStep__euler | 30001 / 30001 | 10 / 10 | 7 of 21 | out[11] | 1e-9 | 1.0399 | 1e-10 | 1.6e-11 | out[11], 1e-10 | out[11], 1e-10 |
| GFL_VoltageStep__euler | 30001 / 30001 | 10 / 10 | 5 of 21 | out[11] | 1e-9 | 0.5244 | 1e-10 | 2.8e-11 | out[11], 1e-10 | out[11], 1e-10 |
| GFL_PowerRamp__euler | 36001 / 36001 | 10 / 10 | 5 of 21 | out[11] | 1e-9 | 0.3826 | 1e-10 | 1.1e-11 | out[11], 1e-10 | out[11], 1e-10 |
| GFL_FaultPSCAD__euler | 58001 / 58001 | 10 / 10 | 5 of 21 | grid_sensor_a.current | 0.0001 | 2.7101 | 4.7e-10 | 4.2e-7 | grid_sensor_a.current, 4.7e-10 | out[7], 9.8e-11 |
| GFM_EMTPFault__euler | 59001 / 59001 | 10 / 10 | 12 of 21 | out[8] | 1e-10 | 2.0022 | 9.9e-11 | 4.1e-13 | out[8], 9.9e-11 | out[7], 1.3e-11 |
| GFM_EMTPFull__euler | 60001 / 60001 | 10 / 10 | 4 of 21 | out[5] | 1e-9 | 0.475 | 3.2e-10 | 4.5e-12 | out[5], 3.2e-10 | out[5], 3.2e-10 |
| EMTPTransformerZeroSeq__euler | 30001 / 30001 | 10 / 10 | 9 of 11 | tr.VSecBCLL1.v | 1e-6 | 1.4658 | 5.9e-11 | 5.8e-9 | tr.VSecBCLL1.v, 5.9e-11 | tr.VSecBCLL1.v, 5.9e-11 |
| SmoothShortFault__euler | 55001 / 55001 | 10 / 10 | 6 of 6 | ssf.A.v | 0 | 0 | 0 | 0 | ssf.A.v, 0 | ssf.A.v, 0 |
| GFL_PowerRamp__dassl | 36001 / 36001 | 10 / 10 | 3 of 21 | grid_sensor_c.current | 1e-6 | 0.4127 | 3.3e-10 | 8.2e-9 | grid_sensor_c.current, 3.3e-10 | grid_sensor_c.current, 3.3e-10 |

OpenModelica, the series rebuilt from the raw results with round 2's instant rule, the two platforms at the same
precision:
both platforms rebuilt from their raw results at full precision (exact %.17g caches).
Linux from `~/cigre_verify/openmodelica/build/<run>/<run>_res.mat`,
Windows from `<temp>\cigre_verify\openmodelica\round2\<run>\<run>_res.mat`, cached exactly
in `linux/synthesis/openmodelica_rebuilt/` and `linux/synthesis/openmodelica_rebuilt_windows/`, so `--no-raw` gives this
table too. Nothing is printed, so there is no print floor: these numbers are the platforms' own difference, down to
about 1e-16 of a value. (The record of 19:24 compared the Linux series at full precision with round 2's 12-digit
Windows cache, `verification_round2/synthesis/openmodelica_rebuilt/`, and so measured that cache's rounding in 13 of
15 runs; `review/linux_fix.md`.)

| run | rows L / W | CSV digits L / W | signals identical | worst signal (all points) | max abs | t of max (s) | rel | RMS of it | worst rel, excl. +-Ts of disturbances | worst rel before the first disturbance |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | 10001 / 10001 | full / full | 0 of 6 | gENROU.PELEC | 1.8e-14 | 5.41 | 2e-14 | 3.3e-15 | gENROU.PELEC, 2e-14 | gENROU.PELEC, 7.3e-16 |
| SCRX9__euler | 10001 / 10001 | full / full | 0 of 6 | gENROU.PELEC | 1.5e-14 | 6.675 | 1.6e-14 | 4.7e-16 | gENROU.PELEC, 1.6e-14 | gENROU.PELEC, 7.7e-16 |
| SCRX9_vs_SCRX__dassl | 10001 / 10001 | full / full | 0 of 8 | native.sCRX.EFD | 2.1e-13 | 2.215 | 2.1e-14 | 2.8e-14 | native.sCRX.EFD, 2.1e-14 | dll.gENROU.ETERM, 6.2e-16 |
| SCRX__dassl | 10001 / 10001 | full / full | 0 of 6 | gENROU.PELEC | 4.2e-12 | 10 | 4.7e-12 | 1.2e-12 | gENROU.PELEC, 4.7e-12 | gENROU.PELEC, 7.9e-13 |
| GFL_Fault__euler | 58001 / 58001 | full / full | 3 of 21 | out[6] | 9.6e-9 | 0.1999 | 4.5e-9 | 1.8e-10 | out[6], 4.5e-9 | out[6], 4.5e-9 |
| GFL_POCFault__euler | 40001 / 40001 | full / full | 3 of 21 | out[6] | 6e-12 | 0.1803 | 2.5e-12 | 1e-13 | out[6], 2.5e-12 | out[6], 2.5e-12 |
| GFL_FrequencyStep__euler | 30001 / 30001 | full / full | 3 of 21 | out[6] | 1.4e-12 | 0.3479 | 5.7e-13 | 7.8e-14 | out[6], 5.7e-13 | out[6], 5.7e-13 |
| GFL_VoltageStep__euler | 30001 / 30001 | full / full | 3 of 21 | out[6] | 1.7e-12 | 0.3885 | 7.1e-13 | 1.6e-13 | out[6], 7.1e-13 | out[6], 7.1e-13 |
| GFL_PowerRamp__euler | 36001 / 36001 | full / full | 3 of 21 | out[12] | 3.7e-12 | 2.3555 | 3.7e-13 | 8.9e-13 | out[12], 3.7e-13 | out[12], 3e-13 |
| GFL_FaultPSCAD__euler | 58001 / 58001 | full / full | 3 of 21 | out[7] | 1.9e-13 | 2.8181 | 1.9e-13 | 1.5e-14 | out[7], 1.9e-13 | out[9], 6.3e-15 |
| GFM_EMTPFault__euler | 59001 / 59001 | full / full | 3 of 21 | out[9] | 2.2e-15 | 0.2636 | 7.8e-15 | 5.8e-16 | out[9], 7.8e-15 | out[9], 7.8e-15 |
| GFM_EMTPFull__euler | 60001 / 60001 | full / full | 3 of 21 | out[6] | 1.2e-11 | 0.3422 | 4.9e-12 | 2.1e-13 | out[6], 4.9e-12 | out[6], 4.9e-12 |
| EMTPTransformerZeroSeq__euler | 30001 / 30001 | full / full | 0 of 11 | tr.Bd.v | 3.6e-12 | 2.8357 | 3.7e-16 | 6.8e-13 | tr.Bd.v, 3.7e-16 | tr.Bd.v, 3.7e-16 |
| SmoothShortFault__euler | 55001 / 55001 | full / full | 0 of 6 | ssf.A.v | 2e-10 | 0.5221 | 5.4e-16 | 1.3e-11 | ssf.A.v, 5.4e-16 | ssf.A.v, 5.4e-16 |
| GFL_PowerRamp__dassl | 36001 / 36001 | full / full | 3 of 21 | grid_sensor_c.current | 3.9e-8 | 2.0166 | 1.3e-11 | 1.1e-9 | grid_sensor_c.current, 1.3e-11 | grid_sensor_b.current, 7e-12 |

| run | outcome L / W | steps | f-evals | Jacobians | time events | state events | result points | translate L / W (s) = ratio | compile L / W (s) = ratio | simulate wall L / W (s) = ratio | without LOG_STATS, median of 3, L / W = ratio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | ok / ok | = 20909 | = 22652 | = 18763 | = 2000 | = 3 | = 5777 | 0.287 / 0.427 = 0.67 | 0.396 / 3.03 = 0.13 | 2.76 / 2.46 = 1.12 | 2.72 / 2.21 = 1.23 |
| SCRX9__euler | ok / ok | - | - | = 0 | = 2002 | = 2 | = 5775 | 0.302 / 0.451 = 0.67 | 0.472 / 1.09 = 0.43 | 0.0769 / 0.147 = 0.52 | 0.0717 / 0.136 = 0.53 |
| SCRX9_vs_SCRX__dassl | ok / ok | = 21498 | = 23373 | = 19270 | = 2000 | = 4 | = 5779 | 0.73 / 0.954 = 0.77 | 0.824 / 1.52 = 0.54 | 6.09 / 4.62 = 1.32 | 5.87 / 4.98 = 1.18 |
| SCRX__dassl | ok / ok | = 463 | = 542 | = 61 | = 0 | = 4 | = 2010 | 0.303 / 0.479 = 0.63 | 0.435 / 1.51 = 0.29 | 0.0799 / 0.144 = 0.55 | 0.0785 / 0.14 = 0.56 |
| GFL_Fault__euler | ok / ok | - | - | = 0 | = 580003 | = 3 | = 1730051 | 0.151 / 0.0996 = 1.52 | 0.358 / 0.983 = 0.36 | 2.05 / 2.34 = 0.88 | 1.52 / 1.71 = 0.89 |
| GFL_POCFault__euler | ok / ok | - | - | = 0 | = 400000 | = 6 | = 1190091 | 0.396 / 0.356 = 1.11 | 0.549 / 1.24 = 0.44 | 2.86 / 3.09 = 0.93 | 2.08 / 2.27 = 0.92 |
| GFL_FrequencyStep__euler | ok / ok | - | - | = 0 | = 300000 | = 1 | = 890081 | 0.278 / 0.196 = 1.42 | 0.426 / 1.11 = 0.39 | 1.5 / 1.65 = 0.91 | 1.07 / 1.2 = 0.89 |
| GFL_VoltageStep__euler | ok / ok | - | - | = 0 | = 300000 | = 1 | = 890081 | 0.284 / 0.205 = 1.39 | 0.444 / 1.06 = 0.42 | 1.49 / 1.73 = 0.86 | 1.06 / 1.24 = 0.86 |
| GFL_PowerRamp__euler | ok / ok | - | - | = 0 | = 360000 | = 2 | = 1070086 | 0.197 / 0.204 = 0.96 | 0.428 / 1.53 = 0.28 | 1.81 / 2.07 = 0.88 | 1.32 / 1.57 = 0.84 |
| GFL_FaultPSCAD__euler | ok / ok | - | - | = 0 | = 580003 | = 3 | = 1730051 | 0.158 / 0.107 = 1.47 | 0.339 / 0.956 = 0.35 | 2.11 / 2.37 = 0.89 | 1.53 / 1.84 = 0.83 |
| GFM_EMTPFault__euler | ok / ok | - | - | = 0 | = 590006 | = 6 | = 1760068 | 0.197 / 0.248 = 0.80 | 0.403 / 1.05 = 0.38 | 4.77 / 5.16 = 0.92 | 3.88 / 4.28 = 0.91 |
| GFM_EMTPFull__euler | ok / ok | - | - | = 0 | = 600006 | = 6 | = 1790062 | 0.304 / 0.378 = 0.81 | 0.554 / 1.22 = 0.46 | 4.41 / 4.61 = 0.95 | 3.28 / 3.7 = 0.89 |
| EMTPTransformerZeroSeq__euler | ok / ok | - | - | = 0 | = 0 | = 0 | = 300002 | 0.26 / 0.176 = 1.47 | 0.382 / 1.06 = 0.36 | 0.412 / 0.528 = 0.78 | 0.258 / 0.354 = 0.73 |
| SmoothShortFault__euler | ok / ok | - | - | = 0 | = 0 | = 5 | = 550012 | 0.177 / 0.189 = 0.94 | 0.412 / 1.08 = 0.38 | 0.613 / 0.788 = 0.78 | 0.306 / 0.411 = 0.74 |
| GFL_PowerRamp__dassl | ok / ok | = 7583152 | = 9938486 | = 4568408 | = 360000 | = 2 | = 755014 | 0.212 / 0.204 = 1.04 | 0.431 / 1.58 = 0.27 | 32.6 / 29.7 = 1.10 | 24.3 / 23.8 = 1.02 |

System Modeler (`linux/systemmodeler/`, `verification_round2/systemmodeler/`):

| run | rows L / W | CSV digits L / W | signals identical | worst signal (all points) | max abs | t of max (s) | rel | RMS of it | worst rel, excl. +-Ts of disturbances | worst rel before the first disturbance |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | 10001 / 10001 | 12 / 12 | 0 of 6 | gENROU.ETERM | 1e-12 | 3.716 | 1.4e-12 | 3.7e-14 | gENROU.ETERM, 1.4e-12 | gENROU.PELEC, 1.1e-12 |
| SCRX9__euler | 10001 / 10001 | 12 / 12 | 2 of 6 | gENROU.PELEC | 1e-12 | 7.27 | 1.1e-12 | 2.2e-14 | gENROU.PELEC, 1.1e-12 | gENROU.PELEC, 1.1e-12 |
| GFL_Fault__euler | 58001 / 58001 | 12 / 12 | 6 of 21 | out[6] | 1.9e-9 | 0.1999 | 9e-10 | 3.5e-11 | out[6], 9e-10 | out[6], 9e-10 |
| GFL_POCFault__euler | 40001 / 40001 | 12 / 12 | 3 of 21 | out[12] | 1e-10 | 3.1138 | 1e-11 | 3.5e-12 | out[12], 1e-11 | out[8], 9.2e-12 |
| GFL_FrequencyStep__euler | 30001 / 30001 | 12 / 12 | 3 of 21 | out[12] | 1e-10 | 0.169 | 1e-11 | 1.8e-12 | out[12], 1e-11 | out[12], 1e-11 |
| GFL_VoltageStep__euler | 30001 / 30001 | 12 / 12 | 3 of 21 | out[6] | 2.7e-11 | 0.3885 | 1.1e-11 | 2.3e-13 | out[6], 1.1e-11 | out[6], 1.1e-11 |
| GFL_PowerRamp__euler | 36001 / 36001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 3.2515 | 1e-11 | 6e-14 | out[8], 1e-11 | grid_sensor_c.current, 3.3e-12 |
| GFL_FaultPSCAD__euler | 58001 / 58001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 2.9701 | 9.3e-12 | 7.4e-14 | out[8], 9.3e-12 | out[9], 3.4e-12 |
| GFM_EMTPFault__euler | 59001 / 59001 | 12 / 12 | 3 of 21 | out[5] | 1e-11 | 5.0807 | 4.4e-12 | 9.9e-14 | out[5], 4.4e-12 | out[6], 1.3e-12 |
| GFM_EMTPFull__euler | 60001 / 60001 | 12 / 12 | 3 of 21 | out[8] | 1e-11 | 3.2912 | 9.2e-12 | 5.8e-14 | out[8], 9.2e-12 | out[4], 4.2e-12 |
| EMTPTransformerZeroSeq__euler | 30001 / 30001 | 12 / 12 | 0 of 11 | tr.Ad.v | 1e-8 | 0.7834 | 1e-12 | 1.2e-10 | tr.Ad.v, 1e-12 | tr.Ad.v, 1e-12 |
| SmoothShortFault__euler | 55001 / 55001 | 12 / 12 | 5 of 6 | ssf.currentSensor2.i | 1e-10 | 2.971 | 1.6e-15 | 4.3e-13 | ssf.currentSensor2.i, 1.6e-15 | ssf.currentSensor2.i, 1.6e-15 |
| GFL_PowerRamp__dassl | 36001 / 36001 | 12 / 12 | 3 of 21 | out[12] | 1e-10 | 0.2528 | 1e-11 | 8.4e-12 | out[12], 1e-11 | out[12], 1e-11 |

| run | outcome L / W | steps | f-evals | Jacobians | time events | state events | result points | translate L / W (s) = ratio | compile L / W (s) = ratio | simulate wall L / W (s) = ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | ok / ok | - | = 212729 | - | = 2002 | = 0 | = 4006 | 3.36 / 9.86 = 0.34 | 1.11 / 1.71 = 0.65 | 4.27 / 5.42 = 0.79 |
| SCRX9__euler | ok / ok | - | = 26030 | - | = 2002 | = 0 | = 4006 | 3.31 / 9.7 = 0.34 | 1.16 / 1.71 = 0.68 | 0.264 / 0.435 = 0.61 |
| SCRX9_vs_SCRX__dassl | failed / failed | - | - | - | - | - | - | 3.41 / 9.55 = 0.36 | - / - | - / - |
| SCRX__dassl | failed / failed | - | - | - | - | - | - | 2.06 / 2.94 = 0.70 | - / - | - / - |
| GFL_Fault__euler | ok / ok | - | = 5220031 | - | = 580003 | = 0 | = 1160008 | 3.46 / 11.4 = 0.30 | 0.352 / 1.56 = 0.23 | 3.72 / 11 = 0.34 |
| GFL_POCFault__euler | ok / ok | - | = 5203012 | - | = 400003 | = 1443 | = 800008 | 3.91 / 12.9 = 0.30 | 0.502 / 1.86 = 0.27 | 5.52 / 12.6 = 0.44 |
| GFL_FrequencyStep__euler | ok / ok | - | = 2700013 | - | = 300001 | = 0 | = 600004 | 3.71 / 13.6 = 0.27 | 0.402 / 1.76 = 0.23 | 2.57 / 7.5 = 0.34 |
| GFL_VoltageStep__euler | ok / ok | - | = 2700013 | - | = 300001 | = 0 | = 600004 | 3.81 / 12.8 = 0.30 | 0.452 / 1.93 = 0.23 | 2.62 / 6.85 = 0.38 |
| GFL_PowerRamp__euler | ok / ok | - | = 3240022 | - | = 360002 | = 0 | = 720006 | 3.51 / 12.3 = 0.28 | 0.452 / 1.76 = 0.26 | 3.22 / 8.44 = 0.38 |
| GFL_FaultPSCAD__euler | ok / ok | - | = 5220031 | - | = 580003 | = 0 | = 1160008 | 3.31 / 11.6 = 0.28 | 0.402 / 1.66 = 0.24 | 3.92 / 10.6 = 0.37 |
| GFM_EMTPFault__euler | ok / ok | - | = 7674296 | - | = 590003 | = 2122 | = 1180008 | 3.36 / 12.1 = 0.28 | 0.452 / 1.81 = 0.25 | 5.62 / 13.5 = 0.42 |
| GFM_EMTPFull__euler | ok / ok | - | = 7804452 | - | = 600003 | = 2163 | = 1200008 | 4.02 / 12.2 = 0.33 | 0.603 / 1.71 = 0.35 | 8.93 / 16.8 = 0.53 |
| EMTPTransformerZeroSeq__euler | ok / ok | - | = 900010 | - | = 0 | = 0 | = 300003 | 2.41 / 3.33 = 0.72 | 0.352 / 1.56 = 0.23 | 1.02 / 2.83 = 0.36 |
| SmoothShortFault__euler | ok / ok | - | = 2769837 | - | = 2 | = 1980 | = 551985 | 2.26 / 2.99 = 0.76 | 0.502 / 1.66 = 0.30 | 1.77 / 5.47 = 0.32 |
| GFL_PowerRamp__dassl | ok / ok | - | 59031817 / 59032219 (-402) | - | = 360002 | = 0 | = 720006 | 4.01 / 11.5 = 0.35 | 0.503 / 1.56 = 0.32 | 22.8 / 29.2 = 0.78 |

System Modeler's diagnostic runs with the separate fix b48d49e8 (not contract runs; `diagnostics/scrx_fix_b48d49e8/` on
both platforms):

| run | rows L / W | CSV digits L / W | signals identical | worst signal (all points) | max abs | t of max (s) | rel | RMS of it | worst rel, excl. +-Ts of disturbances | worst rel before the first disturbance |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9_vs_SCRX__dassl | 10001 / 10001 | 12 / 12 | 2 of 8 | dll.gENROU.ETERM | 1e-11 | 2.541 | 1.4e-11 | 1e-13 | dll.gENROU.ETERM, 1.4e-11 | dll.gENROU.w, 7.4e-16 |
| SCRX__dassl | 10001 / 10001 | 12 / 12 | 0 of 6 | gENROU.ETERM | 6.1e-11 | 4.115 | 8.7e-11 | 4.4e-12 | gENROU.ETERM, 8.7e-11 | gENROU.PELEC, 2.2e-12 |

| run | outcome L / W | steps | f-evals | Jacobians | time events | state events | result points | translate L / W (s) = ratio | compile L / W (s) = ratio | simulate wall L / W (s) = ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| SCRX9_vs_SCRX__dassl | ok / ok | - | 238534 / 238573 (-39) | - | = 2002 | = 16 | = 4038 | 4.32 / 11.6 = 0.37 | 2.16 / 2.01 = 1.07 | 9.03 / 14.2 = 0.63 |
| SCRX__dassl | ok / ok | - | 11153 / 11108 (+45) | - | = 2 | = 16 | = 2037 | 2.46 / 3.56 = 0.69 | 1.16 / 1.76 = 0.66 | 0.214 / 0.418 = 0.51 |

### 4.3 At the stored points (source: `tool_raw_records`, read from the tool agents' records)

Each tool agent also compared every stored point of its raw result file with the Windows raw file (Dymola
`linux/dymola/self_comparison.json`, OpenModelica `linux/openmodelica/logs/self_comparison.json`, System Modeler
`linux/systemmodeler/analysis/linux_vs_windows_raw/<run>.json`).

| run | D points L / W | D time vector | D worst max abs L-W at stored points | OM points L / W | OM time vector | OM worst max abs L-W at stored points | SM points L / W | SM time vector | SM largest abs L-W / max abs value (variables above 1e-3) |
|---|---|---|---|---|---|---|---|---|---|
| SCRX9__dassl | 4005 / 4005 | equal | sCRX9.EFD 1.2e-14 | 5777 / 5777 | equal | sCRX9.EFD 5.2e-14 | 4006 / 4006 | equal | 2.2e-13 (der(gENROU.PSIkq)) |
| SCRX9__euler | 4000 / 4000 | equal | sCRX9.EFD 7.1e-15 | 5775 / 5775 | equal | gENROU.PELEC 1.5e-14 | 4006 / 4006 | equal | 1.4e-14 (pwLine1.Q12) |
| SCRX9_vs_SCRX__dassl | 4009 / 4008 | equal up to point 841 (a state event located 4e-15 s apart), then the extra stored point (Linux) at point 869 | native.sCRX.EFD 5.2e-14 | 5779 / 5779 | equal | native.sCRX.EFD 2.1e-13 | - | - | failed at the build on both |
| SCRX__dassl | 2007 / 2008 | equal up to point 419 (a state event located 1.05e-12 s apart), then the extra stored point (Windows) at point 437 | sCRX.EFD 5.2e-12 | 2010 / 2010 | equal | sCRX.EFD 1.1e-11 | - | - | failed at the build on both |
| GFL_Fault__euler | 1160001 / 1160001 | equal | grid_sensor_a.current 9.8e-7 | 1730051 / 1730051 | equal | grid_sensor_a.current 1.1e-5 | 1160008 / 1160008 | equal | 2.4e-9 (der(inductor1.i)) |
| GFL_POCFault__euler | 800001 / 800001 | equal | grid_sensor_b.current 1.3e-9 | 1190091 / 1190091 | equal | grid_sensor_b.current 1.6e-9 | 800008 / 800008 | equal | 2.2e-11 (out[6]) |
| GFL_FrequencyStep__euler | 600001 / 600001 | equal | grid_sensor_b.current 7.6e-10 | 890081 / 890081 | equal | grid_sensor_b.current 6.5e-10 | 600004 / 600004 | equal | 6e-12 (der(inductor1.i)) |
| GFL_VoltageStep__euler | 600001 / 600001 | equal | grid_sensor_c.current 5.2e-10 | 890081 / 890081 | equal | grid_sensor_c.current 1.1e-9 | 600004 / 600004 | equal | 1.1e-10 (inductor1.v) |
| GFL_PowerRamp__euler | 720001 / 720001 | equal | grid_sensor_b.current 1e-9 | 1070086 / 1070086 | equal | grid_sensor_a.current 5.8e-10 | 720006 / 720006 | equal | 1e-12 (tr.Cd.i) |
| GFL_FaultPSCAD__euler | 1160001 / 1160001 | equal | grid_sensor_b.current 1.1e-8 | 1730051 / 1730051 | equal | grid_sensor_a.current 2.3e-8 | 1160008 / 1160008 | equal | 2.6e-14 (der(c_b.v)) |
| GFM_EMTPFault__euler | 1180001 / 1180001 | equal | grid_sensor_c.voltage 5.8e-11 | 1760068 / 1760068 | equal | grid_sensor_c.voltage 2.4e-11 | 1180008 / 1180008 | equal | 9.4e-13 (inductor.v) |
| GFM_EMTPFull__euler | 1200001 / 1200001 | equal | grid_sensor_b.current 1.2e-9 | 1790062 / 1790062 | equal | grid_sensor_a.current 1.1e-8 | 1200008 / 1200008 | equal | 2.1e-11 (out[6]) |
| EMTPTransformerZeroSeq__euler | 30002 / 30002 | equal | tr.VSecABLL1.v 5.5e-12 | 300002 / 300002 | equal | tr.VSecBCLL1.v 7.3e-12 | 300003 / 300003 | equal | 1.5e-12 (der(tr.Rba.v)) |
| SmoothShortFault__euler | 55010 / 55010 | equal | ssf.B.v 1.7e-10 | 550012 / 550012 | equal | ssf.C.v 2.6e-10 | 551985 / 551985 | equal | 8.3e-15 (der(eMTPGrid.firstOrder1.y)) |
| GFL_PowerRamp__dassl | 720004 / 720004 | equal | grid_sensor_c.voltage 3.2e-8 | 755014 / 755014 | max diff 1.8e-15 s | grid_sensor_a.current 5e-8 | 720006 / 720006 | equal | 1.8e-10 (tr.phaseB.L1.v) |

- The time vectors are equal in every run except Dymola's two native-SCRX runs and OpenModelica's GFL_PowerRamp with
  DASSL (at most 1.8e-15 s apart). Dymola's first part at a located state event,
  4e-15 s apart in SCRX9_vs_SCRX (point
  842) and
  1.05e-12 s apart in SCRX (point
  420), and then at the event 1.08e-12 s after
  the clearing that one platform stores as a pre/post pair and the other once (points
  869 and
  437). With that extra point dropped, only the
  two points of the state event differ in each run (`tool_raw_records/dymola/<run>/time_vectors`, read from the two
  `dsres.mat` files), so every Dymola time event, the disturbances of D.1 included, is stored at the same instant on
  both platforms. OpenModelica's off-grid event instants are equal too, except in GFL_PowerRamp with DASSL (at most
  1.8e-15 s apart, `offgrid_event_instants_max_abs_diff`), and System Modeler's time vectors are equal in every run.
  So every off-grid disturbance acts at the same instant as on Windows (to 1.8e-15 s) in every tool: Dymola's Euler at
  the end of the step that contains it, OpenModelica and System Modeler at the located instant, DASSL at the nominal
  one.
- The tests without any DLL differ too: Dymola's native SCRX and the two network-only tests, OpenModelica's
  `SCRX__dassl` and the network tests, System Modeler's network tests. The differences come with the platform (compiler,
  C maths library, runtime), not with the shipped libraries. The Dymola agent located the first differing stored value:
  at t = 0 in the phasor tests' initialization and at the first Euler step in the sine sources of the EMT tests; the
  DLL outputs differ only after their inputs do (Dymola record, section 8.D.2).

### 4.4 Figures

- `linux/figs/scrx9_dymola_linux_vs_windows.png`, `scrx9_openmodelica_linux_vs_windows.png`,
  `scrx9_systemmodeler_linux_vs_windows.png`: SCRX9 with DASSL, EFD and GEN1.v, Linux and Windows overlaid, and the
  absolute difference on a log axis.
- `linux/figs/gfl_fault_dymola_linux_vs_windows.png`, `gfl_fault_openmodelica_linux_vs_windows.png`,
  `gfl_fault_systemmodeler_linux_vs_windows.png`: GFL_Fault, Iqref = `out[6]` (the signal of the largest difference in
  all three tools), P and Q, the same.
- A difference panel of a signal whose Linux and Windows CSV values are identical says so ("identical at all N grid
  points") instead of showing an empty log axis.

![SCRX9, Dymola, Linux against Windows](figs/scrx9_dymola_linux_vs_windows.png)

![GFL_Fault, OpenModelica, Linux against Windows](figs/gfl_fault_openmodelica_linux_vs_windows.png)

## 5. The one place where the difference grows: GFL_Fault's start-up (source: `experiment_gfl_startup`)

In all three tools the largest Linux-Windows difference sits in GFL_Fault at about 0.2 s, while the converter starts
from rest, and decays afterwards (section 4.1). To find out whether that needs a platform effect beyond round-off, the
Linux OpenModelica executable of the contract run was run again three times on Linux only
(`linux/experiments/gfl_fault_startup_sensitivity/perturb_om.py`, `run.sh`, `result.json`): unchanged (base), with the
source amplitude `gridWithFault.Vgrid` = 1 + 1e-15 (a few units in the last place), and with 1 + 1e-12. Differences at
the stored points, maximum per time window:

| comparison (OpenModelica, GFL_Fault, stored points) | signal | max abs difference | 0-0.05 s | 0.1-0.19 s | 0.19-0.21 s | 0.21-0.3 s | 0.3-1 s | 2-5.8 s |
|---|---|---|---|---|---|---|---|---|
| base rerun minus the Linux contract run | out[6] | bit-identical | 0 | 0 | 0 | 0 | 0 | 0 |
| base rerun minus the Linux contract run | out[11] | bit-identical | 0 | 0 | 0 | 0 | 0 | 0 |
| base rerun minus the Linux contract run | grid_sensor_a.current | bit-identical | 0 | 0 | 0 | 0 | 0 | 0 |
| Linux contract run minus Windows round 2 (OpenModelica) | out[6] | 9.6e-9 at 0.19989 s (8e-9 of max abs) | 6.7e-15 | 2.9e-10 | 9.6e-9 | 5.3e-9 | 9.1e-11 | 1.5e-12 |
| Linux contract run minus Windows round 2 (OpenModelica) | out[11] | 2.9e-8 at 0.20283 s (1.8e-9 of max abs) | 3.1e-14 | 2.7e-10 | 2.9e-8 | 1.9e-8 | 2.4e-10 | 1.3e-11 |
| Linux contract run minus Windows round 2 (OpenModelica) | grid_sensor_a.current | 1.1e-5 at 0.20025 s (7.2e-9 of max abs) | 3.9e-12 | 1.8e-7 | 1.1e-5 | 2.6e-6 | 1.3e-7 | 2.7e-9 |
| Vgrid 1+1e-15 minus base (Linux) | out[6] | 2.2e-10 at 0.22988 s (1.8e-10 of max abs) | 1.3e-14 | 6.7e-11 | 1.4e-10 | 2.2e-10 | 3e-12 | 4.4e-12 |
| Vgrid 1+1e-15 minus base (Linux) | out[11] | 7.7e-10 at 0.23345 s (4.7e-11 of max abs) | 9e-14 | 6.6e-11 | 3.7e-10 | 7.7e-10 | 7.1e-12 | 1.2e-11 |
| Vgrid 1+1e-15 minus base (Linux) | grid_sensor_a.current | 1.5e-7 at 0.19135 s (9.8e-11 of max abs) | 9.6e-12 | 2.5e-8 | 1.5e-7 | 1e-7 | 5.5e-9 | 2.7e-9 |
| Vgrid 1+1e-12 minus base (Linux) | out[6] | 4.2e-9 at 0.22987 s (3.5e-9 of max abs) | 2.4e-11 | 1.3e-9 | 2.8e-9 | 4.2e-9 | 6.3e-11 | 2.8e-11 |
| Vgrid 1+1e-12 minus base (Linux) | out[11] | 1.5e-8 at 0.23344 s (8.9e-10 of max abs) | 3.6e-11 | 1.3e-9 | 9.3e-9 | 1.5e-8 | 1.5e-10 | 2.6e-11 |
| Vgrid 1+1e-12 minus base (Linux) | grid_sensor_a.current | 3.2e-6 at 0.20037 s (2.1e-9 of max abs) | 4.9e-9 | 5.1e-7 | 3.2e-6 | 2e-6 | 1.2e-7 | 9.1e-9 |

What it shows:
1. The base rerun reproduces the contract run bit for bit, so the setup is the contract's.
2. A last-place change of one parameter, on one platform, grows by about four orders of magnitude between 0.1 and
   0.3 s and shrinks again after 0.3 s: the start-up transient amplifies a last-bit difference in the window where the
   Linux-Windows difference peaks.
3. The growth is not proportional (1000 times the perturbation gives about 20 times the change), so the start-up
   amplifies nonlinearly. The Linux-Windows difference, which starts in the last bit at the first steps (OpenModelica
   record: first at 1e-5 s; Dymola record: first Euler step), grows more than the 1e-15 perturbation (`out[6]`:
   1.4e6 times against
   1.6e4) and decays more slowly: in 0.3-1 s it is
   9.1e-11 against
   3e-12 in `out[6]` and
   1.3e-7 A
   against 5.5e-9 A
   in the grid current, the size of the 1e-12 perturbation
   (1.2e-7 A).
   Round-off that enters at many operations rather than in one parameter would explain that; this experiment does
   not test it.
4. After 2 s every comparison is back at 1e-12 to a few 1e-11 of the signals' largest values (column "2-5.8 s"), and the final
   values agree to 10 digits (OpenModelica record, section 7).

So the GFL_Fault number is consistent with round-off amplified by the model's own start-up: a last-place change on
one platform peaks in the same window and, at 1e-12, reaches the same size. Whether compiler and maths-library
round-off alone give the whole Linux-Windows difference is not shown (section 12, item 10). Nothing points at the
shipped library: the tests without any DLL differ too, and the DLL outputs differ only after their inputs do
(section 4.3). Figure: `linux/experiments/gfl_fault_startup_sensitivity/gfl_fault_startup_sensitivity.png`.

![GFL_Fault start-up sensitivity](experiments/gfl_fault_startup_sensitivity/gfl_fault_startup_sensitivity.png)

## 6. Cross-tool on Linux (source: `runs/<run>/cross_tool`, `runs/<run>/cross_tool_vs_windows`, `summary/cross_tool`)

Computed as `verification_round2/compare.py` does: OpenModelica's series rebuilt from its raw results, System Modeler's
diagnostic run (b48d49e8, marked *) where its contract run fails, worst relative difference over each run's key signals
(SCRX: EFD, GEN1.v, gENROU.w, ETERM, PELEC; converter tests: P, Q, f_PLL, the three grid currents, v_a; network tests:
their contract signals). Linux / Windows round 2 (`verification_round2/comparison.json`, `runs/<run>/cross_tool`):

| run | D-OM all L / W | D-OM excl L / W | D-SM all L / W | D-SM excl L / W | OM-SM all L / W | OM-SM excl L / W |
|---|---|---|---|---|---|---|
| SCRX9__dassl | 3.7e-5 / 3.7e-5 | 3.7e-5 / 3.7e-5 | 2e-10 / 2e-10 | 2e-10 / 2e-10 | 3.7e-5 / 3.7e-5 | 3.7e-5 / 3.7e-5 |
| SCRX9__euler | 0.54 / 0.54 | 0.0094 / 0.0094 | 0.54 / 0.54 | 0.0094 / 0.0094 | 1.2e-6 / 1.2e-6 | 1.2e-6 / 1.2e-6 |
| SCRX9_vs_SCRX__dassl | 0.0011 / 0.0011 | 0.0011 / 0.0011 | 1.3e-5 / 1.3e-5* | 1.3e-5 / 1.3e-5* | 0.0011 / 0.0011* | 0.0011 / 0.0011* |
| SCRX__dassl | 0.0024 / 0.0024 | 0.0024 / 0.0024 | 2.5e-5 / 2.5e-5* | 2.5e-5 / 2.5e-5* | 0.0024 / 0.0024* | 0.0024 / 0.0024* |
| GFL_Fault__euler | 0.00047 / 0.00047 | 0.00047 / 0.00047 | 0.00047 / 0.00047 | 0.00047 / 0.00047 | 5.6e-7 / 5.6e-7 | 5.6e-7 / 5.6e-7 |
| GFL_POCFault__euler | 0.069 / 0.069 | 0.069 / 0.069 | 0.19 / 0.19 | 0.19 / 0.19 | 0.26 / 0.26 | 0.26 / 0.26 |
| GFL_FrequencyStep__euler | 2.6e-5 / 2.6e-5 | 2.6e-5 / 2.6e-5 | 2.6e-5 / 2.6e-5 | 2.6e-5 / 2.6e-5 | 4e-7 / 4e-7 | 4e-7 / 4e-7 |
| GFL_VoltageStep__euler | 5.8e-5 / 5.8e-5 | 5.8e-5 / 5.8e-5 | 5.8e-5 / 5.8e-5 | 5.8e-5 / 5.8e-5 | 3.4e-8 / 3.4e-8 | 3.4e-8 / 3.4e-8 |
| GFL_PowerRamp__euler | 3.9e-5 / 3.9e-5 | 3.9e-5 / 3.9e-5 | 3.9e-5 / 3.9e-5 | 3.9e-5 / 3.9e-5 | 4.2e-7 / 4.2e-7 | 4.2e-7 / 4.2e-7 |
| GFL_FaultPSCAD__euler | 0.00027 / 0.00027 | 0.00027 / 0.00027 | 0.00027 / 0.00027 | 0.00027 / 0.00027 | 5e-7 / 5e-7 | 5e-7 / 5e-7 |
| GFM_EMTPFault__euler | 0.0021 / 0.0021 | 0.0021 / 0.0021 | 0.0032 / 0.0032 | 0.0032 / 0.0032 | 0.0033 / 0.0033 | 0.0033 / 0.0033 |
| GFM_EMTPFull__euler | 0.046 / 0.046 | 0.046 / 0.046 | 0.025 / 0.025 | 0.025 / 0.025 | 0.05 / 0.05 | 0.05 / 0.05 |
| EMTPTransformerZeroSeq__euler | 5.9e-13 / 1e-12 (floor) | 5.9e-13 / 1e-12 (floor) | 1e-12 / 1e-12 (floor) | 1e-12 / 1e-12 (floor) | 5.9e-13 / 1e-12 (floor) | 5.9e-13 / 1e-12 (floor) |
| SmoothShortFault__euler | 0.00068 / 0.00068 | 0.00068 / 0.00068 | 0.0084 / 0.0084 | 0.0084 / 0.0084 | 0.0089 / 0.0089 | 0.0089 / 0.0089 |
| GFL_PowerRamp__dassl | 4.2e-7 / 4.2e-7 | 4.2e-7 / 4.2e-7 | 7.6e-7 / 7.6e-7 | 7.6e-7 / 7.6e-7 | 7.9e-7 / 7.9e-7 | 7.9e-7 / 7.9e-7 |

"(floor)": the Linux and the Windows worst difference both lie within two units of the 12th digit of the CSVs at the
instant of their maximum (the CSV floor), so the change between them is print rounding. That is the case only in
EMTPTransformerZeroSeq, where `transformer.Ad.v` (2.3 to 2.8 kV in magnitude at those instants) differs by 5.7e-9
to 1e-8 V, one unit of the 12th digit being 1e-8 V. Round 2's block (`comparison.json`) took OpenModelica from its
12-digit cache,
this one from the raw results at full precision. Computed again with the Windows OpenModelica series rebuilt from the
Windows raw results at full precision (`runs/<run>/cross_tool_windows_recomputed`), the Linux worst relative
differences differ from the Windows ones by at most
8e-5 of themselves
(Dymola - OpenModelica,
EMTPTransformerZeroSeq__euler), and the recomputed pair without
OpenModelica equals `comparison.json` in all 15 runs
(largest relative difference 0). Above the floor
the largest change against round 2's own numbers is 8.4e-6 of
itself (OpenModelica - System Modeler,
GFL_VoltageStep__euler).

How much a cross-tool difference moved between the platforms (per key signal, the change of the maximum absolute
difference, relative to the signal's scale):

| pair | largest change of a cross-tool max abs difference, Linux against Windows, relative to the signal scale (run, signal) |
|---|---|
| dymola-openmodelica | SCRX__dassl, sCRX.EFD: 1.6e-12 |
| dymola-systemmodeler | SCRX__dassl, gENROU.PELEC: 2.2e-12 |
| openmodelica-systemmodeler | GFL_Fault__euler, out[11]: 3.5e-9 |

| run | D-OM: Linux worst max abs at t (signal); largest change against Windows, relative to the scale (signal) | D-SM: the same | OM-SM: the same |
|---|---|---|---|
| SCRX9__dassl | 3.32e-5 at 3.47 s (gENROU.PELEC); change 1.9e-13 (gENROU.ETERM) | 1.4e-10 at 2.264 s (GEN1.v); change 0 (sCRX9.EFD) | 3.32e-5 at 3.47 s (gENROU.PELEC); change 1.9e-13 (gENROU.ETERM) |
| SCRX9__euler | 0.384 at 2.004 s (GEN1.v); change 6.4e-13 (gENROU.ETERM) | 0.384 at 2.004 s (GEN1.v); change 5e-19 (gENROU.w) | 1.16e-5 at 10 s (sCRX9.EFD); change 4.1e-13 (sCRX9.EFD) |
| SCRX9_vs_SCRX__dassl | 0.0107 at 2.096 s (native.sCRX.EFD); change 6.1e-13 (native.GEN1.v) | 0.000127 at 2.972 s (native.sCRX.EFD); change 0 (native.sCRX.EFD) | 0.0107 at 2.096 s (native.sCRX.EFD); change 6.1e-13 (native.GEN1.v) |
| SCRX__dassl | 0.0237 at 2.088 s (sCRX.EFD); change 1.6e-12 (sCRX.EFD) | 2.29e-5 at 6.288 s (gENROU.PELEC); change 2.2e-12 (gENROU.PELEC) | 0.0237 at 2.088 s (sCRX.EFD); change 2.5e-12 (gENROU.PELEC) |
| GFL_Fault__euler | 1.43 at 5.1001 s (grid_sensor_c.current); change 4.8e-13 (grid_sensor_a.current) | 1.43 at 5.1001 s (grid_sensor_c.current); change 3.3e-13 (grid_sensor_a.current) | 0.00169 at 5.1001 s (grid_sensor_a.current); change 3.5e-9 (out[11]) |
| GFL_POCFault__euler | 240 at 3.1009 s (grid_sensor_c.current); change 8.3e-13 (out[10]) | 674 at 3.1009 s (grid_sensor_c.current); change 1e-12 (out[11]) | 914 at 3.1009 s (grid_sensor_c.current); change 8.4e-13 (out[11]) |
| GFL_FrequencyStep__euler | 0.00026 at 2.0033 s (out[12]); change 6.9e-13 (out[10]) | 0.00026 at 2.0033 s (out[12]); change 0 (out[12]) | 3.97e-6 at 3 s (out[12]); change 1.4e-12 (out[11]) |
| GFL_VoltageStep__euler | 0.209 at 2.0002 s (grid_sensor_b.current); change 3.9e-13 (grid_sensor_a.voltage) | 0.209 at 2.0002 s (grid_sensor_b.current); change 2e-14 (out[12]) | 3.41e-7 at 3 s (out[11]); change 7.2e-13 (out[10]) |
| GFL_PowerRamp__euler | 0.138 at 2.8002 s (grid_sensor_b.current); change 4.2e-13 (grid_sensor_a.voltage) | 0.138 at 2.8002 s (grid_sensor_b.current); change 1e-12 (out[12]) | 4.22e-6 at 3.6 s (out[12]); change 4.5e-13 (out[10]) |
| GFL_FaultPSCAD__euler | 0.301 at 5.0001 s (grid_sensor_a.voltage); change 4.5e-13 (out[11]) | 0.3 at 5.0001 s (grid_sensor_a.voltage); change 0 (out[12]) | 0.000566 at 5.1001 s (grid_sensor_a.voltage); change 6.6e-13 (out[10]) |
| GFM_EMTPFault__euler | 0.0213 at 5.0025 s (out[11]); change 1.4e-12 (grid_sensor_c.current) | 34.8 at 5.1009 s (grid_sensor_a.voltage); change 0 (out[12]) | 36.4 at 5.1009 s (grid_sensor_a.voltage); change 1.2e-12 (grid_sensor_b.current) |
| GFM_EMTPFull__euler | 161 at 5.1008 s (grid_sensor_c.current); change 1e-12 (grid_sensor_b.current) | 87 at 5.1009 s (grid_sensor_c.current); change 9.3e-14 (grid_sensor_a.voltage) | 210 at 5.1008 s (grid_sensor_b.current); change 1.3e-12 (grid_sensor_a.current) |
| EMTPTransformerZeroSeq__euler | 5.71e-9 at 2.8697 s (tr.Ad.v); change 4.4e-13 (tr.Ad.v) | 1e-8 at 0.7834 s (tr.Ad.v); change 2.7e-17 (tr.VSecABLL.v) | 5.71e-9 at 2.8697 s (tr.Ad.v); change 4.4e-13 (tr.Ad.v) |
| SmoothShortFault__euler | 254 at 5.0379 s (ssf.A.v); change 1.2e-13 (ssf.C.v) | 3.17e3 at 5.038 s (ssf.A.v); change 0 (ssf.currentSensor2.i) | 3.35e3 at 5.0379 s (ssf.A.v); change 3e-13 (ssf.B.v) |
| GFL_PowerRamp__dassl | 4.24e-6 at 3.6 s (out[12]); change 1.2e-12 (grid_sensor_a.current) | 0.00228 at 0.3298 s (grid_sensor_c.current); change 1e-12 (out[11]) | 0.00236 at 0.3298 s (grid_sensor_c.current); change 7.7e-13 (grid_sensor_a.current) |

The cross-tool picture of round 2 therefore holds on Linux unchanged: the large numbers (SCRX9 with Euler 5 ms, the
current-zero clearings of GFL_POCFault, GFM_EMTPFault, GFM_EMTPFull and SmoothShortFault) are where the tools apply an
off-grid event differently or open a phase at a different current zero, as `VERIFICATION_round2.md` sections 5 and 6
explain, and they are the same numbers on both platforms.

Settled values (the last 0.1 s of DC signals, the last 0.05 s peak of AC signals, the final values; flag above 1e-3
between two tools): none

GFL_FaultPSCAD's settled reactive power (D.3), Linux / Windows (`d3_faultpscad`). The means are over [a, b), except
the 5.3-5.8 s mean, which includes t = 5.8 s, as round 2's does (its Windows values need that window):

| tool | Q mean 1.5-2.0 s (Mvar) L / W | P mean 4.5-5.0 s (MW) L / W | Q mean 4.5-5.0 s (Mvar) L / W | Q mean 5.3-5.8 s, both ends included (Mvar) L / W | P at 5.8 s (MW) L / W | Q at 5.8 s (Mvar) L / W |
|---|---|---|---|---|---|---|
| Dymola | -53.22724704 / -53.22724704 | 40.00001291 / 40.00001291 | -71.58891582 / -71.58891582 | -71.45101574 / -71.45101574 | 40.15479425 / 40.15479425 | -71.70213542 / -71.70213542 |
| OpenModelica | -53.22724703 / -53.22724703 | 40.00001299 / 40.00001299 | -71.58891587 / -71.58891587 | -71.4510156 / -71.4510156 | 40.15479424 / 40.15479424 | -71.7021354 / -71.7021354 |
| System Modeler | -53.22724704 / -53.22724704 | 40.00001291 / 40.00001291 | -71.58891582 / -71.58891582 | -71.45101555 / -71.45101555 | 40.15479417 / 40.15479417 | -71.70213535 / -71.70213535 |

![Cross-tool, SCRX9 EFD, Linux](figs/crosstool_linux_scrx9_efd.png)

![Cross-tool, GFL_Fault P and Q, Linux](figs/crosstool_linux_gfl_fault_pq.png)

## 7. SCRX9 DLL against master's native SCRX, per tool on Linux (source: `runs/<run>/steady_start`, `runs/SCRX9_vs_SCRX__dassl/dll_vs_native`, `scrx9_test_vs_native_test`)

Steady start before the fault (EFD(0), the drift of EFD, the speed and the bus voltage before 2 s), Linux / Windows:

| run | tool (part) | EFD(0) L / W (pu) | max abs(EFD - EFD(0)), t < 2 s, L / W (pu) | max abs(w), t < 2 s, L / W (pu) | GEN1.v range, t < 2 s, L / W (pu) |
|---|---|---|---|---|---|
| SCRX9__dassl | Dymola | 1.43510692 / 1.43510692 | 7.164818e-5 / 7.164818e-5 | 1.079907e-6 / 1.079907e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9__dassl | OpenModelica | 1.43510692 / 1.43510692 | 7.164857e-5 / 7.164857e-5 | 1.079908e-6 / 1.079908e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9__dassl | System Modeler | 1.43510692 / 1.43510692 | 7.164842e-5 / 7.164842e-5 | 1.079905e-6 / 1.079905e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9__euler | Dymola | 1.43510692 / 1.43510692 | 7.405925e-5 / 7.405925e-5 | 1.104271e-6 / 1.104271e-6 | 3.8579e-6 / 3.8579e-6 |
| SCRX9__euler | OpenModelica | 1.43510692 / 1.43510692 | 7.405926e-5 / 7.405925e-5 | 1.104271e-6 / 1.104271e-6 | 3.8579e-6 / 3.8579e-6 |
| SCRX9__euler | System Modeler | 1.43510692 / 1.43510692 | 7.40595e-5 / 7.40595e-5 | 1.104269e-6 / 1.104269e-6 | 3.8579e-6 / 3.8579e-6 |
| SCRX__dassl | Dymola | 1.43510692 / 1.43510692 | 7.770115e-5 / 7.770115e-5 | 1.083041e-6 / 1.083041e-6 | 3.6546e-6 / 3.6546e-6 |
| SCRX__dassl | OpenModelica | 1.43510692 / 1.43510692 | 7.565819e-5 / 7.565819e-5 | 1.083042e-6 / 1.083042e-6 | 3.6953e-6 / 3.6953e-6 |
| SCRX__dassl | System Modeler (with b48d49e8) | 1.43510692 / 1.43510692 | 7.114928e-5 / 7.114928e-5 | 1.079746e-6 / 1.079746e-6 | 3.6163e-6 / 3.6163e-6 |
| SCRX9_vs_SCRX__dassl | Dymola dll | 1.43510692 / 1.43510692 | 7.164818e-5 / 7.164818e-5 | 1.079907e-6 / 1.079907e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9_vs_SCRX__dassl | Dymola native | 1.43510692 / 1.43510692 | 7.149608e-5 / 7.149608e-5 | 1.079855e-6 / 1.079855e-6 | 3.6566e-6 / 3.6566e-6 |
| SCRX9_vs_SCRX__dassl | OpenModelica dll | 1.43510692 / 1.43510692 | 7.164857e-5 / 7.164857e-5 | 1.079908e-6 / 1.079908e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9_vs_SCRX__dassl | OpenModelica native | 1.43510692 / 1.43510692 | 7.149636e-5 / 7.149635e-5 | 1.079856e-6 / 1.079856e-6 | 3.6566e-6 / 3.6566e-6 |
| SCRX9_vs_SCRX__dassl | System Modeler (with b48d49e8) dll | 1.43510692 / 1.43510692 | 7.16484e-5 / 7.16484e-5 | 1.079905e-6 / 1.079905e-6 | 3.6759e-6 / 3.6759e-6 |
| SCRX9_vs_SCRX__dassl | System Modeler (with b48d49e8) native | 1.43510692 / 1.43510692 | 7.149606e-5 / 7.149606e-5 | 1.079855e-6 / 1.079855e-6 | 3.6566e-6 / 3.6566e-6 |

Same SMIB, both T_E 0.01 s and r_cr_fd 10, both faulted 2.0025-2.1525 s (`SCRX9_vs_SCRX`), DLL minus native, Linux /
Windows:

| tool | signal (DLL minus native) | max abs before 2.0025 s L / W | max abs after L / W | after, at the 5 ms samples L / W | t >= 2.3 s, at the samples L / W | at 10 s L / W |
|---|---|---|---|---|---|---|
| Dymola | EFD | 1.028e-6 / 1.028e-6 | 3.289 / 3.289 | 0.03994 / 0.03994 | 0.03994 / 0.03994 | 7.798e-5 / 7.798e-5 |
| Dymola | GEN1.v | 1.43e-8 / 1.43e-8 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | -1.148e-6 / -1.148e-6 |
| Dymola | gENROU.w | 8.587e-10 / 8.587e-10 | 6.283e-5 / 6.283e-5 | 6.283e-5 / 6.283e-5 | 6.283e-5 / 6.283e-5 | -4.852e-7 / -4.852e-7 |
| Dymola | gENROU.ETERM | 1.43e-8 / 1.43e-8 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | -1.148e-6 / -1.148e-6 |
| OpenModelica | EFD | 1.028e-6 / 1.028e-6 | 3.289 / 3.289 | 0.03991 / 0.03991 | 0.03991 / 0.03991 | 7.472e-5 / 7.472e-5 |
| OpenModelica | GEN1.v | 1.429e-8 / 1.43e-8 | 0.001576 / 0.001576 | 0.001576 / 0.001576 | 0.001576 / 0.001576 | -1.145e-6 / -1.145e-6 |
| OpenModelica | gENROU.w | 8.588e-10 / 8.588e-10 | 6.28e-5 / 6.28e-5 | 6.28e-5 / 6.28e-5 | 6.28e-5 / 6.28e-5 | -4.856e-7 / -4.856e-7 |
| OpenModelica | gENROU.ETERM | 1.429e-8 / 1.43e-8 | 0.001576 / 0.001576 | 0.001576 / 0.001576 | 0.001576 / 0.001576 | -1.145e-6 / -1.145e-6 |
| System Modeler (with b48d49e8) | EFD | 1.028e-6 / 1.028e-6 | 3.289 / 3.289 | 0.03994 / 0.03994 | 0.03994 / 0.03994 | 7.798e-5 / 7.798e-5 |
| System Modeler (with b48d49e8) | GEN1.v | 1.435e-8 / 1.435e-8 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | -1.148e-6 / -1.148e-6 |
| System Modeler (with b48d49e8) | gENROU.w | 8.589e-10 / 8.589e-10 | 6.283e-5 / 6.283e-5 | 6.283e-5 / 6.283e-5 | 6.283e-5 / 6.283e-5 | -4.852e-7 / -4.852e-7 |
| System Modeler (with b48d49e8) | gENROU.ETERM | 1.435e-8 / 1.435e-8 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | 0.001577 / 0.001577 | -1.148e-6 / -1.148e-6 |

The SCRX9 test against master's native SCRX test (separate runs; T_E and r_cr_fd differ by design), before 2 s:

| tool | EFD: SCRX9 test minus native test, max abs, t < 2 s, L / W (pu) | GEN1.v L / W (pu) | gENROU.w L / W (pu) |
|---|---|---|---|
| Dymola | 6.709e-6 / 6.709e-6 | 3.5e-7 / 3.5e-7 | 1.789e-7 / 1.789e-7 |
| OpenModelica | 4.635e-6 / 4.635e-6 | 3.035e-7 / 3.035e-7 | 1.452e-7 / 1.452e-7 |
| System Modeler (with b48d49e8) | 2.548e-6 / 2.548e-6 | 4.357e-8 / 4.357e-8 | 2.674e-9 / 2.674e-9 |

Every number equals its Windows value to the digits shown. (Round 2's OpenModelica numbers in these tables and in D.3
come from its 12-digit cache, the Linux ones from the raw results at full precision; that difference lies below the
digits shown.) The DLL exciter and the native one relate on Linux exactly
as on Windows: about 1e-6 pu in EFD before the fault, 0.04 pu at the DLL's 5 ms samples after it, and up to 3.3 pu
between the samples, where the DLL holds its output and a continuous exciter does not (`VERIFICATION_round2.md`
section 7.2 reads these numbers).

## 8. Performance, Linux against Windows (source: `performance`, the metrics files)

| run | Dymola simulate wall L / W (s) = ratio | OpenModelica without LOG_STATS, median of 3, L / W (s) = ratio | System Modeler simulate wall L / W (s) = ratio |
|---|---|---|---|
| SCRX9__dassl | 1.87 / 1.92 = 0.98 | 2.72 / 2.21 = 1.23 | 4.27 / 5.42 = 0.79 |
| SCRX9__euler | 0.212 / 0.237 = 0.89 | 0.0717 / 0.136 = 0.53 | 0.264 / 0.435 = 0.61 |
| SCRX9_vs_SCRX__dassl | 3.93 / 4.26 = 0.92 | 5.87 / 4.98 = 1.18 | failed / failed |
| SCRX__dassl | 0.153 / 0.119 = 1.29 | 0.0785 / 0.14 = 0.56 | failed / failed |
| GFL_Fault__euler | 1.58 / 2.36 = 0.67 | 1.52 / 1.71 = 0.89 | 3.72 / 11 = 0.34 |
| GFL_POCFault__euler | 1.8 / 2.89 = 0.62 | 2.08 / 2.27 = 0.92 | 5.52 / 12.6 = 0.44 |
| GFL_FrequencyStep__euler | 1.03 / 1.5 = 0.69 | 1.07 / 1.2 = 0.89 | 2.57 / 7.5 = 0.34 |
| GFL_VoltageStep__euler | 0.991 / 1.37 = 0.72 | 1.06 / 1.24 = 0.86 | 2.62 / 6.85 = 0.38 |
| GFL_PowerRamp__euler | 1.42 / 1.7 = 0.83 | 1.32 / 1.57 = 0.84 | 3.22 / 8.44 = 0.38 |
| GFL_FaultPSCAD__euler | 1.59 / 1.68 = 0.95 | 1.53 / 1.84 = 0.83 | 3.92 / 10.6 = 0.37 |
| GFM_EMTPFault__euler | 2.37 / 2.9 = 0.82 | 3.88 / 4.28 = 0.91 | 5.62 / 13.5 = 0.42 |
| GFM_EMTPFull__euler | 2.77 / 4.68 = 0.59 | 3.28 / 3.7 = 0.89 | 8.93 / 16.8 = 0.53 |
| EMTPTransformerZeroSeq__euler | 0.196 / 0.177 = 1.11 | 0.258 / 0.354 = 0.73 | 1.02 / 2.83 = 0.36 |
| SmoothShortFault__euler | 0.376 / 0.376 = 1.00 | 0.306 / 0.411 = 0.74 | 1.77 / 5.47 = 0.32 |
| GFL_PowerRamp__dassl | 16.7 / 17.4 = 0.96 | 24.3 / 23.8 = 1.02 | 22.8 / 29.2 = 0.78 |

| tool | simulate L/W, all runs ok on both | Euler runs | DASSL runs | translate L/W | compile L/W |
|---|---|---|---|---|---|
| Dymola | 0.59-1.29 (median 0.89, 15 runs) | 0.59-1.11 (11) | 0.92-1.29 (4) | 0.70-1.22 (median 0.81, 15 runs) | 0.79-1.92 (median 0.88, 15 runs) |
| OpenModelica | 0.53-1.23 (median 0.89, 15 runs) | 0.53-0.92 (11) | 0.56-1.23 (4) | 0.63-1.52 (median 0.96, 15 runs) | 0.13-0.54 (median 0.38, 15 runs) |
| System Modeler | 0.32-0.79 (median 0.38, 13 runs) | 0.32-0.61 (11) | 0.78-0.79 (2) | 0.27-0.76 (median 0.33, 15 runs) | 0.23-0.68 (median 0.26, 13 runs) |

- OpenModelica uses the median of three runs without LOG_STATS (`nostats_simulate_wall_s`), the other two
  `simulate_wall_s`.
- Dymola: the Euler runs take 0.59-1.11
  of the Windows time, the DASSL runs 0.92-1.29.
  Its "CPU-time for integration" is not reliable inside WSL2 (it exceeded the wall time in two runs; Dymola record,
  section 10).
- OpenModelica: the Euler runs take 0.53-0.92
  of the Windows time; the three DASSL runs with a DLL 1.02-1.23,
  mostly in the Jacobian timer (Linux links reference LAPACK/BLAS, Windows OpenBLAS; not tested further, OpenModelica
  record section 7.1); compilation takes 0.13-0.54
  of the Windows time.
- System Modeler: the simulations take 0.32-0.79
  of the Windows time, translation 0.33 and compilation
  0.26 (medians); the Windows round-2 runs had the other
  Windows agents' load.
- Every timing on both platforms was taken with the other tool agents running at the same time: compare by order of
  magnitude.

![Performance](figs/performance_linux_vs_windows.png)

## 9. Static checks (source: `static_checks`)

| check | Linux | Windows round 2 | Linux source |
|---|---|---|---|
| Dymola checkModel, normal | 50 classes, 0 failed, 0 with warnings | 50/50 ok, 0 warnings, 0 errors (round2_changes.md section 6) | linux/dymola/logs/checks/dymola_checks_summary.json |
| Dymola checkModel, pedantic | 50 classes, 0 failed, 0 with warnings | 50 classes, 50 ok, 0 warnings, 0 errors | linux/dymola/logs/checks/dymola_checks_summary.json |
| OpenModelica checkModel | 50 of 50 ok, 0 with messages | 50 of 50 ok, 0 with messages | linux/openmodelica/logs/checks_summary.json |
| OpenModelica checkModel with --unitChecking | 50 of 50 ok, 0 with messages | 50 of 50 ok, 0 with messages | linux/openmodelica/logs/checks_summary.json |
| OpenModelica translateModel (the 12 tests and master's native SCRX) | 13 of 13 true, 11 with a warning | 12 of 12 tests true, 10 with a warning (round2_changes.md section 6; master's SCRX not counted there) | linux/openmodelica/logs/translate_all/summary.json |
| System Modeler validation (Linux: kernel checkModelTest, unit severity warning; Windows: WSMValidate) | 45 of 52 OpenIPSL classes valid, 0 unit warnings; with the 5 diagnostic classes 49 of 57 valid, the same verdict as Windows for 57 of 57 | 45 of 52 valid, 0 unit warnings | linux/systemmodeler/validation_table.md (and validation.json) |

All verdicts are Windows'. System Modeler's standalone kernel has no `checkModel`/`validateModel`; its `checkModelTest`
was run once per class with `+unit-violation-severity=warning`, because the kernel's default is `silent` (System Modeler
record, section 7). OpenModelica's translateModel count includes master's native SCRX test; its warning ("alias variables
with redundant start ...") is the one it prints on Windows.

## 10. Tool messages (sources: the tool READMEs, section named in each item)

1. Dymola: one Linux-only message in every run, GNU ld's "warning: the use of 'tmpnam' is dangerous, better use
   'mkstemp'" in Dymola's own `ModelicaInternal_temporaryFileName` (also in the native SCRX test; not OpenIPSL code).
   Windows-only and gone on Linux: "Some 32-bit libraries are missing ... switching to 64-bit mode" and the MSVC warnings
   C4267/C4018. All other messages are Windows' (Dymola record, section 7).
2. OpenModelica: no message on one platform only; the translation messages are identical to the Windows metrics files
   in all 15 runs (OpenModelica record, section 6).
3. System Modeler: no message on one platform only, once the executable's stdout and stderr go to two files; Windows
   tags the MSL files `writable`, Linux `readonly` (System Modeler record, section 8). Without the kit's `g++-nopie`
   wrapper every DLL model prints two failed links of the kernel's evaluator (section 11, item 4).
4. No message from the shipped libraries on any platform (the adapter writes to stderr only on an error).

## 11. Everything that differs from Windows

1. Compilers. Model code: Dymola gcc 13.3.0 `-O1` PIE (Windows MSVC); OpenModelica clang 18.1.3 `-Os` (Windows clang
   22.1.4 of MSYS2 ucrt64); System Modeler g++ 13.3.0 without `-O`, through `g++-nopie` (Windows MSVC cl 19.44 `/MT`).
   Shipped library: gcc 15.2.0 `.so` (Windows MSVC 19.51 DLL). C maths library: glibc 2.39 `libm` (Windows UCRT).
2. glibc. The shipped `.so` files were built on glibc 2.43 (Ubuntu 26.04.1) and need only `GLIBC_2.2.5`, `GLIBC_2.3.4`
   and `GLIBC_2.4` (the last from `__stack_chk_fail`); they loaded and ran on glibc 2.39 in all three tools. Their C tests
   pass on 2.39 too (`linux/smoke/10_shipped_libs.txt`: 6 of 6, two libraries in one process in both orders included).
3. Library binding (section 2): Dymola DT_RUNPATH, OpenModelica DT_RPATH (with `--disable-new-dtags`, seven folders),
   System Modeler none, so `LD_LIBRARY_PATH`. Windows: the DLL path compiled in (Dymola) or the folder on PATH.
4. System Modeler's PIE trap. System Modeler 15.0 links its translation-time evaluator against `lib/linux64/libserializer.a`,
   which is not position-independent (52 32-bit absolute relocations: 45 `R_X86_64_32` and 7 `R_X86_64_32S`, by
   `readelf -rW`); Ubuntu's g++ links PIE by default, so the link fails twice per DLL model, once for `sampleTime` and
   once for `count` ("relocation R_X86_64_32 ... can not be used when making a PIE object"). The kernel goes on: `Ts`
   becomes `PARAM` instead of `EVAL_PARAM`, and SCRX9 DASSL and GFL_Fault are bit-identical in every model variable
   with and without the wrapper: 596 of 597 and 540 of 541 stored variables, the one left being
   `$SimulationLog.realTime`, the wall-clock log (System Modeler record, section 6). The kit's
   `/opt/openipsl-kit/bin/g++-nopie`, named by `setCompilerPath`, removes the failures. Wolfram tests with GCC 8.5,
   which does not default to PIE.
5. No WSMLink on Linux. System Modeler for Linux ships no Wolfram Language kernel and no `wolframscript`: only the
   standalone kernel exists. The contract runs used it on both platforms; the Windows WSMLink cross-check and
   `WSMValidate` have no Linux counterpart (validation by `checkModelTest`).
6. stdout and stderr. A System Modeler executable whose stdout and stderr share one file on Linux loses the stderr text
   (stdout overwrites it); the adapter writes its messages to stderr. The runner keeps them apart, and so does the
   kit's smoke test `tests/smoke/40_systemmodeler.sh` since the fix after this record (`run.out`, `run.err`).
7. Dymola's `Evaluate`. Windows round 2 ran with `Evaluate = true` from a persistent flag of Luigi's Windows
   `setup.dymx`; Dymola's default is `false`. The Linux record sets `true` explicitly and gets Windows' statistics in all
   15 runs; with `false`, GFM_EMTPFull gets a linear system of size 24 and dynamic state selection, the transformer tests
   take 2.5-3.3 times as long and GFL_PowerRamp DASSL 6.44 M steps and 111 s instead of 7.48 M and 17 s (Dymola record,
   section 9; that set is kept in `linux/dymola/evaluate_false/`).
8. Dymola for Linux: MSL 4.1.0 is its only MSL, as on Windows; "Compilation time" does not cover the gcc build;
   "CPU-time for integration" unreliable in WSL2; about 9 system calls per time event in its runtime (Dymola record,
   section 10).
9. OpenModelica on Linux: MSL from `~/.openmodelica/libraries/Modelica 4.0.0+maint.om`, installed from the `omlibrary`
   cache on the user's first omc run; LAPACK/BLAS reference 3.12.0 against OpenBLAS.
10. Numbers: not bit-identical; equal events and counts except the three items of section 4.1; differences of round-off size, up
    to the GFL_Fault start-up maximum of section 5.

## 12. What is NOT verified

1. Other distributions: Ubuntu 22.04 and 26.04, Debian, RHEL 8/9 (Dymola's reference platform is RHEL 8.6 with gcc
   11.2.1). The glibc symbol versions predict that the files load on all of them (RHEL 8 has glibc 2.28); not run.
2. Native Linux outside WSL2. All runs were in a WSL2 VM on Windows 11 (kernel 6.18.33.2-microsoft-standard-WSL2);
   timings in particular are WSL2 timings.
3. The tools' GUIs: Dymola's, OMEdit, System Modeler's Model Center and Simulation Center (and whether Simulation Center
   sets `LD_LIBRARY_PATH` for the executable).
4. A package moved after the build, a `dymosim` or OpenModelica executable copied to another machine, a stale
   `lib<Name>.so` in an earlier RPATH folder: described from the measured binding, not run.
5. Both libraries in one Modelica model (covered only by the C tests of `10_shipped_libs.sh`).
6. aarch64 or any other architecture; only `linux64` (x86-64) is shipped.
7. How System Modeler's kernel passes the library path to its evaluator (not traced), and timings on a quiet machine.
8. Rebuilding the libraries from their sources on Ubuntu 24.04 (gcc 13.3, the CMake / `build_linux64.sh` route): only
   the shipped `.so` files, built with gcc 15.2 on Ubuntu 26.04, were used.
9. System Modeler through WSMLink, and Model Center's validation (`WSMValidate`): System Modeler for Linux has no
   Wolfram Language kernel (section 11, item 5); validation was by the standalone kernel's `checkModelTest`.
10. Whether compiler and maths-library round-off alone give the whole GFL_Fault start-up difference (section 5): it
    would take the Linux GFL_Fault executable rebuilt with another optimization level or compiler (its makefile with
    `-O0`, or `CC=gcc`) and compared with the `-Os` contract run on the same platform; not run.
11. Rerunning the stored-point comparisons of section 4.3 and the experiment of section 5: they read the Windows round-2
    raw results in `<temp>\cigre_verify\{dymola,openmodelica,systemmodeler}\round2\`
    (8.7, 1.9 and 12 GB of result files), which are in no record. Once that Temp folder is cleaned they cannot be
    rerun, and the tool agents' records stand as written. Section 4.2's rebuilt OpenModelica table and Dymola's time
    vectors of 4.3 do not depend on it any more: their Windows inputs are cached exactly in `linux/synthesis/`.

## 13. Open items and decisions

A. Open items
  A.1 The Windows round-2 Dymola record got `Evaluate = true` from Luigi's Windows `setup.dymx`; its README does not
      say so and its `dymola_run.py` would not reproduce it on another machine. One line in either is needed.
  A.2 The kit's smoke test `linux-env/tests/smoke/40_systemmodeler.sh` writes the executable's stdout and stderr to one
      file and so loses stderr on Linux; the lead's folder, not edited here. FIXED after this record by the lead:
      the smoke test now writes `run.out` and `run.err` separately.
  A.3 `verification_round2/dymola/event_instants.json` has no entry for the end of GFL_PowerRamp's ramps (2.800005 s);
      this synthesis uses the instants of `compare.py`, as round 2 did.
  A.4 Build trees in the distro's ext4 that can go once Luigi says so: `/home/<user>/cigre_verify/dymola/` (33 GB:
      `runs` 8.7 GB, `evaluate_false` 12 GB, `first_pass_evaluate_false` 12 GB, bit-identical to the second pass),
      `/home/<user>/cigre_verify/openmodelica/build/` (5.1 GB), `/home/<user>/cigre_verify/systemmodeler/` (about 14 GB),
      `/home/<user>/cigre_verify/synthesis/` (1.3 GB: this synthesis's stage, the experiment and the test stages of the
      review fix in `review_fix/`).
  A.5 System Modeler's non-PIC `libserializer.a` could be reported to Wolfram (stock Ubuntu users see two failed
      evaluator links per DLL model, with correct results).
D. Decisions for Luigi
  D.1 Which Dymola `Evaluate` setting is the recipe of record: (i) `true`, what Windows round 2 ran and this record
      uses (recommended: same translation on both platforms, faster); (ii) `false`, Dymola's default.
  D.2 Whether the README classes of the package get Linux sentences: (i) System Modeler users who run a built executable
      outside the tool put `Resources/Library/linux64` on `LD_LIBRARY_PATH` (with the error text of section 2);
      (ii) a moved or deleted package, or a `dymosim` copied to a machine without the package at that path, needs the
      same; (iii) a stale `lib<Name>.so` in one of the five folders that OpenModelica's RPATH puts before `linux64`
      would be loaded instead of the shipped one. Recommended: (i), one sentence; (ii) and (iii) optional.
  D.3 Whether to keep the Windows round-2 raw results that sections 4.3 and 5 read (section 12, item 11): (i) copy
      the result files (about 23 GB) to a kept folder outside Temp, for example the distro's ext4
      `/home/<user>/cigre_verify/windows_round2_raw/`, and point `WINDOWS_RUNS`, `WIN_BUILD`, the third argument of
      `run_analysis.sh`, the experiment's `--windows` and `compare_linux.py --om-win-raw`/`--dymola-win-raw` at it;
      (ii) let them go with the Temp folder; the record keeps its numbers, and section 4.2 and Dymola's time vectors
      rerun from the caches. Recommended: (i) while Linux runs of this package may be repeated before the merge,
      otherwise (ii).
  D.4 Whether to run the one-platform test of section 12, item 10 (about 1e-8 in `out[6]` near 0.2 s between `-O0`
      and `-Os` would show that compiler-level round-off alone gives the platform difference): (i) not now, the verdict
      does not depend on it (recommended); (ii) run it.
Decisions taken by Luigi, 2026-10-25 ~21:00 (after this record was written)
  - D.1: (i) `Evaluate = true` is the recipe of record. The Linux runner already sets it; the Windows round-2 script
    `verification_round2/dymola/scripts/dymola_run.py` now sets and restores it too, and its README says why (the
    round-2 results are unchanged by that edit).
  - D.3: (i), kept in Dropbox: the Windows round-2 raw results (27.2 GB, 11025 files, robocopy 0 failed) are now in
    `<records>\z-raw-results\windows_round2\<tool>\` (the former
    `...\Temp\cigre_verify\<tool>\round2\`). `compare_linux.py`, `run_compare_linux.sh` and the experiment's scripts
    point there; the kit's runners read it from `WINDOWS_RAW_ROOT` in `site.env`. Section 12, item 11 no longer
    applies.
  - A.4: build trees deleted except the SCRX9 and GFL_Fault runs of each tool (53 GB to 5.3 GB in the distro).
  - A.2: fixed (see A.2). D.2 and D.4: not yet decided; the recommendations stand.
  - The kit is also the private repository https://github.com/ALSETLab/openipsl-linux-testenv (renamed ALSETLab/openipsl-testenv on 2026-10-31; first commit
    `68dd8cd`, branch `main`, machine-specific defaults moved into `site.env`, BSD 3-Clause), to be made public
    later. The copy in `<records>\linux-env\` keeps `site.env` and `logs\`.

## 14. Files of this record

Folder `<records>\report\linux\`:
- `LINUX_VERIFICATION.md` (this file), rendered from `synthesis/LINUX_VERIFICATION.src.md`.
- `compare_linux.py` (the synthesis, numpy and matplotlib only, `python3 -I`), `run_compare_linux.sh` (runs it in the
  distro, stages in ext4, renders, copies), `comparison_linux.json` (every number), `comparison_linux_tables.md` (every
  table), `synthesis/openmodelica_rebuilt/<run>.csv.gz` and `synthesis/openmodelica_rebuilt_windows/<run>.csv.gz` (the
  rebuilt Linux and Windows OpenModelica series, `%.17g`, exact, each with a `<run>.meta.json` naming its raw file),
  `synthesis/dymola_time_vectors.json` (where Dymola's stored time vectors part), so that `--no-raw` gives the same
  numbers without the build trees and the Windows Temp folder.
- `review/linux_check.md` (the reviewer's findings) with its checks in `check/`, and `review/linux_fix.md` (how each
  finding was applied).
- `figs/`: `scrx9_<tool>_linux_vs_windows.png`, `gfl_fault_<tool>_linux_vs_windows.png` (3 tools each),
  `crosstool_linux_scrx9_efd.png`, `crosstool_linux_gfl_fault_pq.png`, `performance_linux_vs_windows.png`.
- `experiments/gfl_fault_startup_sensitivity/`: `perturb_om.py`, `run.sh`, `result.json`,
  `gfl_fault_startup_sensitivity.png`, `console.txt` (section 5).
- `dymola/`, `openmodelica/`, `systemmodeler/`: the tool records (CSV, metrics JSON and raw-points file per run, logs,
  README), unchanged by this synthesis except for text corrections of the reviewer's findings A.4 and A.8 in
  `dymola/README.md` and `systemmodeler/README.md` (listed in `review/linux_fix.md`).
- `smoke/`: the kit's smoke-test outputs; `requirements/`: the requirement research of the kit.
- Runners: `<records>\linux-env\tests\{dymola,openmodelica,systemmodeler}\` (each
  with a README); the kit itself: `<records>\linux-env\`.
