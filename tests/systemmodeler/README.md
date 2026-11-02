# System Modeler runs of the IEEE/CIGRE DLL verification (Linux)

Part of the OpenIPSL Linux verification kit (`linux-env`, see `../../README.md`). These scripts build and simulate the
contract runs of the IEEE/CIGRE DLL package in Wolfram System Modeler 15.0 for Linux, with the shipped
`Resources/Library/linux64/lib<Name>.so`, and write a record in the data contract of the Windows rounds
(`report/verification_round2/systemmodeler/`), so that the two platforms can be compared run by run.

**Route: the standalone kernel only.** System Modeler for Linux ships no Wolfram Language kernel and no
`wolframscript`, so the WSMLink route of the Windows rounds (`WSMValidate`, `SystemModelSimulate`) does not exist
here. Everything goes through `bin/WSMKernelX` with a `.mos` script and the simulation executable it builds.

## Files

| File | Role |
|---|---|
| `wsm_run_linux.py` | One contract run: build with the kernel, rewrite the `.sim`, run `<Short>.exe` (timed, 30 min cap), count the events in a second untimed run, write `<Test>__<solver>.csv`, `_metrics.json`, `_raw_points.txt`, `logs/<tag>/`. Port of the kernel route of the Windows `scripts/wsm_run.py` (same `.sim` rewrite, same resampling, same field meanings); the platform parts are listed in its docstring |
| `runs.json` | The 15 contract runs of the Windows round 2 (model, solver, step or interval, stop time, tolerance, CSV grid, signals), plus `first_disturbance` for the comparison |
| `run_all.sh` | Every run of `runs.json` (or the ids given), one after the other; `--compiler default` repeats runs without `setCompilerPath` |
| `validate_classes.py`, `run_validation.sh`, `list_classes.py`, `experiments/WSMExperimentsRound2.mo` | Validation of the 52 classes of the Windows round 2 plus its five diagnostic classes with the kernel's `checkModelTest`, one kernel session per class, unit violations as warnings; two controls (the kernel's default unit severity on the negative control; all classes with the kernel's default compiler). `WSMExperimentsRound2.mo` is the Windows round-2 file, copied unchanged |
| `run_diag_scrxfix.sh`, `runs_diag_scrxfix.json` | Diagnostic, not contract: the two native-SCRX runs on a copy of the package whose `PSSE/ES/SCRX.mo` is the file of OpenIPSL commit `b48d49e8` (the separate fix), as the Windows round 2 did |
| `probes.sh` | Diagnostic probes behind statements of the record (the executable without `LD_LIBRARY_PATH`, the initial nonlinear system's residual, the kernel's validation entry points, the evaluator's compile and link lines, stdout and stderr in one file) |
| `run_analysis.sh` | Every comparison below in one go (no kernel, no licence), written to `~/cigre_verify/systemmodeler/analysis` and copied to `<record>/analysis` |
| `compare_windows.py` | The Linux CSVs against the Windows round-2 CSVs: max abs difference per signal, before and after the first disturbance, last 0.5 s; the counters side by side |
| `compare_mat.py` | Two `.mat` results compared bit for bit, every shared variable at every stored point (wrapper against default compiler; Linux against Windows) |
| `key_values.py`, `summarize.py`, `collect_messages.py` | The documented numbers of the Windows README side by side; the runs table with the library lookup of each executable; every tool message, Linux beside Windows |

## Requirements

The distro built by the kit (`provision/00`, `30`, `40`): System Modeler in `WSM_TARGET`
(`/usr/local/Wolfram/SystemModeler/15.0`), its licence in `~/.systemmodeler/mathpass`, the non-PIE link wrapper
`/opt/openipsl-kit/bin/g++-nopie` (installed by `provision/30_systemmodeler.sh`), `/usr/bin/python3` with numpy, and the
package exported by `tests/export_package.sh` (`~/cigre_verify/pkg/<commit>/OpenIPSL`, with a `COMMIT` file beside
it). No extra package.

## How to run

From Windows (Git Bash: prefix `MSYS_NO_PATHCONV=1`; PowerShell: as written). Never pass a one-liner through
`wsl.exe -- bash -c '...'`: `wsl.exe` re-parses it and `$variables` vanish. Run the script files:

```
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/run_all.sh /home/<user>/cigre_verify/pkg/<commit>/OpenIPSL <records>/systemmodeler
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/run_all.sh <pkg> <record>/default_gpp --compiler default --work /home/<user>/cigre_verify/systemmodeler/runs_default_gpp --stage /home/<user>/cigre_verify/systemmodeler/record_default_gpp SCRX9__dassl GFL_Fault__euler
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/run_validation.sh <pkg> <record> <Windows round-2 record>/logs/wsm_validate.json
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/run_diag_scrxfix.sh <pkg> <SCRX.mo of b48d49e8> <record>/diagnostics/scrx_fix_b48d49e8
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/probes.sh <pkg> <record>
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/systemmodeler/run_analysis.sh <record> <Windows round-2 record> <windows raw>/systemmodeler/runs
```

`run_all.sh` alone makes only the 15 contract runs. The record in `report/linux/systemmodeler/` also needs the other
five lines, in this order: the default-g++ control runs, the validation, the b48d49e8 diagnostics, the probes and the
analysis (the synthesis, `report/linux/compare_linux.py`, reads the diagnostics for the two native-SCRX runs).
(`<kit>` = the kit folder as seen from WSL, for example `/mnt/c/git/openipsl-testenv`; `<pkg>` =
`/home/<user>/cigre_verify/pkg/<commit>/OpenIPSL` from `tests/export_package.sh`; `<record>` = the record folder of
this tool, for example `<records>/systemmodeler`; the Windows round-2 record = `<windows records>/systemmodeler`
(`WINDOWS_RECORD_ROOT` in `site.env`); `<windows raw>` = `WINDOWS_RAW_ROOT` in `site.env`. The last argument of
`run_analysis.sh` is optional: the Windows raw results, for the bit-for-bit comparison; without it that comparison
is skipped.)

Inside the distro (`wsl -d openipsl-verify-24.04`, as the normal user), the same commands without the `wsl.exe ... -e`
prefix, e.g. `bash ~/..../run_all.sh ~/cigre_verify/pkg/<commit>/OpenIPSL <records>/systemmodeler`.
To follow a run from Windows: `wsl.exe -d openipsl-verify-24.04 -e tail -f /home/<user>/cigre_verify/systemmodeler/runs/run_all_console.txt`.

The fixed SCRX file of the diagnostic, read-only from a clone:
`git -C <OpenIPSL clone> show b48d49e8:OpenIPSL/Electrical/Controls/PSSE/ES/SCRX.mo > SCRX_b48d49e8.mo`
(SHA-256 `8a7c618928ca1348a8c5981d328c1f274874345c5d26dc0950d124a315d6a16c`).

The analysis scripts, inside the distro (all `/usr/bin/python3 -I`; `<W>` = the Windows round-2 record):

```
compare_windows.py --spec runs.json --linux <record> --windows <W> --out <dir>
compare_mat.py <runs>/<tag>/<Short>_res.mat <runs_default_gpp>/<tag>/<Short>_res.mat --label-a g++-nopie --label-b default_g++ --json <file>
compare_mat.py <runs>/<tag>/<Short>_res.mat <windows raw>/systemmodeler/runs/<tag>/<Short>_res.mat --label-a linux --label-b windows --json <file>
key_values.py --record <record> --record <W> --labels "Linux,Windows round 2" --out <file.md>
summarize.py --spec runs.json --linux <record> --windows <W> --out <file.md>
collect_messages.py --spec runs.json --linux <record> --windows <W> --out <file.md>
```

## Where things go

- Build trees and raw `.mat` results: the distro's ext4, `~/cigre_verify/systemmodeler/{runs, runs_default_gpp,
  validation, diag, probes}` (never a synced folder such as Dropbox: random file-lock failures). About 12 GB for the
  15 runs.
- The record is staged in `~/cigre_verify/systemmodeler/record` (and `record_default_gpp`, `diag/record`) and copied
  with `cp -r` into the record folder given on the command line when a script ends.
- One System Modeler kernel or simulation at a time (the licence pool is shared): every script runs its builds,
  validations and simulations one after the other; do not start two scripts at once.

## Traps measured here (2026-10-25)

1. **The kernel's default compiler cannot link the external-function evaluator.** Ubuntu's g++ links PIE by default
   and `lib/linux64/libserializer.a` has 52 32-bit absolute relocations (45 `R_X86_64_32`, 7 `R_X86_64_32S`):
   "relocation R_X86_64_32 against `.rodata.str1.1' can not be used when making a PIE object", twice per DLL model
   (the evaluators of `sampleTime` and `count`). The build still succeeds, but the wrappers' `Ts` is then a parameter
   computed at initialisation instead of a value evaluated at translation. `setCompilerPath("/opt/openipsl-kit/bin/g++-nopie")`
   in every `.mos` (runs and validation) removes it; every model variable is bit-identical either way, only
   `$SimulationLog.realTime` (the wall-clock log) differs (record README).
2. **The executable does not find `lib<Name>.so` by itself**: no RUNPATH/RPATH, `-L<...>/linux64 -lSCRX9` only. The
   runner puts the `.sim`'s `<ExternalLibraries>` path on `LD_LIBRARY_PATH` (Windows: the same folder on `PATH`).
3. **stdout and stderr must go to two files.** When both go to one file (`> f 2>&1`, or Python's `stderr=STDOUT` on a
   file), what the executable writes to stderr is overwritten by its stdout: the init warning of SCRX9 and any DLL
   message (the adapter writes its messages to stderr) are lost. Through a pipe they survive. `probes.sh` P5.
4. **One kernel session per validated class.** The `*Test` functions attach every message raised earlier in the
   session to the test they run.
5. **Unit violations are silent by default** in the standalone kernel (`mce_getUnitViolationSeverity()` = `silent`);
   `WSMKernelX +unit-violation-severity=warning` makes them warnings, as WSMLink's `WSMValidate` reports them.
6. The kernel's script language has no `checkModel` or `validateModel` ("Class checkModel not found in scope");
   `checkModelTest` (writes `<mos>.out.json`), `instantiateModelTest` and `mce_checkModel` (returns the validation
   report as a string) exist.
