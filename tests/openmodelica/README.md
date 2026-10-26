# OpenModelica runs on Linux (kit step tests/openmodelica)

Verifies the IEEE/CIGRE DLL package of OpenIPSL with OpenModelica on Linux, using the shipped
`Resources/Library/linux64/lib<Name>.so` files. It is the Linux port of the Windows round-2 driver
(`report/verification_round2/openmodelica/scripts/omc_verify.py`): the same 15 runs, the same `.mos` text, the same
signals, grids and metrics fields, so the results can be compared with the Windows record line by line.

## Files

| File | What it does |
|---|---|
| `omc_verify.py` | The driver. Commands `env`, `checks`, `parsechecks`, `extras`, `run <key>\|all`, `timing <key>\|all`, `binding`, `compare`, `table` (see below). Needs `/usr/bin/python3` with numpy (the kit's base step installs it). |
| `run_all.sh` | Runs every command in order, then copies the record to a destination folder. |
| `UnitProbe.mo` | Three small models, two of them with a unit error on purpose, to show that the unit check can fail (`extras`). |

## Running it

Requirements: the distro of the kit (`windows/New-VerifyDistro.ps1`, steps 00 and 10), and the package exported
with `tests/export_package.sh <commit>`, which puts it in `~/cigre_verify/pkg/<commit>/OpenIPSL`.

From Windows (PowerShell or cmd; in Git Bash put `MSYS_NO_PATHCONV=1` in front). Write the paths in full: `wsl.exe -e`
passes the arguments without a shell, so `~` is not expanded:

```
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/openmodelica/run_all.sh /home/<user>/cigre_verify/pkg/<commit>/OpenIPSL <records>/openmodelica
```

Inside the distro (as the normal user):

```
bash <kit>/tests/openmodelica/run_all.sh ~/cigre_verify/pkg/<commit>/OpenIPSL <records>/openmodelica
```

Arguments of `run_all.sh`: the package folder (the one that holds `package.mo`), the record destination (`-` = do
not copy), and optionally the work folder (default `~/cigre_verify/openmodelica`; it must be on the distro's ext4,
never under `/mnt/`). Environment: `STEPS` (default `env checks extras run timing binding compare table`),
`OMC_TIMING_REPS` (default 3), `WIN_RECORD` and `WIN_BUILD` (the Windows round-2 record and build tree that
`compare` reads; defaults `$WINDOWS_RECORD_ROOT/openmodelica` and `$WINDOWS_RAW_ROOT/openmodelica` from the kit's
`site.env`, or the file `KIT_SITE` names; without a Windows record `compare` is skipped).

One step at a time:

```
/usr/bin/python3 -I omc_verify.py --pkg ~/cigre_verify/pkg/<commit>/OpenIPSL run GFL_Fault__euler
/usr/bin/python3 -I omc_verify.py --pkg ~/cigre_verify/pkg/<commit>/OpenIPSL timing all
```

Options (before the command): `--pkg`, `--build` (default `~/cigre_verify/openmodelica/build`), `--out` (record,
default `~/cigre_verify/openmodelica/record`), `--win-record`, `--win-build`, `--reps`, `--cap` (s per omc
process, default 1800).

## What each command does

- `env`: versions (OS, glibc, omc, clang, gcc, Python), SHA-256, `readelf -d`, `ldd` and the exported adapter
  symbols of the shipped `.so` files, and what omc itself reports (`getCompiler()`, `getCFlags()`, `getLinker()`, the
  MSL file it loaded, `getLoadedLibraries()`). Output `logs/env.txt`.
- `checks`: `checkModel` of every package and class listed in the `package.order` files of
  `Electrical/Controls/IEEE_CIGRE` and `Tests/Controls/IEEE_CIGRE` (50 classes at 1244ae93), then again after
  `setCommandLineOptions("--unitChecking")`. Output `logs/checks_*`, `logs/checks_summary.json`.
- `extras`: the unit probe (`UnitProbe.mo`), `translateModel` with `-d=initialization,aliasConflicts` of the tests
  that print initialization or alias warnings, and `translateModel` of all 12 tests. Output `logs/unitprobe`,
  `logs/init_diag`, `logs/translate_all`.
- `run`: the contract runs. Each in its own folder `<build>/<Test>__<solver>/`, omc started there with `run.mos`:
  `loadModel(Modelica, {"4.0.0"}, requireExactVersion=true)`, `loadFile(<pkg>/package.mo)`, `cd(<run folder>)`,
  `simulate(..., numberOfIntervals=<N>, tolerance=1e-06, method=..., outputFormat="mat", variableFilter=...,
  simflags="-lv=LOG_STATS")`. Euler: N = StopTime/step. A run over the cap is killed with its process group and
  counts as `failed`. Writes `<Test>__<solver>.csv` (contract grid, linear interpolation, the value after an event at
  a stored event instant), `_metrics.json`, `_raw_points.txt`, `logs/<key>/{run.mos,log.txt}`; the raw `.mat` stays
  in the build tree.
- `timing`: the same call without LOG_STATS (`simflags="-s=<method>"`), repeated `--reps` times; adds the
  `nostats_*` fields (median) to the metrics file and checks that the result is bitwise the contract run's.
- `binding`: a short SCRX9 and GFL_Fault `simulate()` with `LD_DEBUG=libs` (written to files in the run folder), to
  show the search path the dynamic loader used for `lib<Name>.so` in the simulation process that omc starts; then the
  same executable relinked with its generated makefile and `MODELICAUSERCFLAGS=-Wl,--verbose`, which lists every
  path `ld` tried for `-l<Name>` at link time. Output `logs/binding.json`.
- `compare`: the self-comparison against the Windows round-2 record of OpenModelica: per run and signal the largest
  difference on the CSV grid, before and after the first disturbance, and, when the Windows build tree is
  readable, the raw stored points (same time vector, first instant that differs, event instants). Output
  `logs/self_comparison.json`.
- `table`: the runs table, `logs/runs_table.md`.

## Linux facts this step relies on (measured 2026-10-25, OpenModelica 1.27.1-1, Ubuntu 24.04.5)

- omc compiles the simulation code with `clang` (`CC=clang` in the generated makefile, Ubuntu clang 18.1.3, `-Os`).
- The makefile links `-L<pkg>/Resources/Library/linux64 -l<Name>` with an `-L` and an `-Wl,-rpath` for each of seven
  folders, in this order: OpenModelica's own `/usr/bin/../lib/x86_64-linux-gnu/omc` and `/usr/bin/../lib/`, then
  `~/.openmodelica/binaries/OpenIPSL`, `Resources/Library/`, `Resources/Library/x86_64-linux`,
  `Resources/Library/linux64`, `Resources/Library`; with `--disable-new-dtags` the executable carries DT_RPATH (those
  seven plus `/usr/bin/../lib`, searched before `LD_LIBRARY_PATH`), not DT_RUNPATH. No environment variable is needed.
  Five folders come before `linux64`, and the loader tries their 15 candidate files first (`binding`, `LD_DEBUG=libs`),
  so a stale `lib<Name>.so` in any of them would be loaded instead of the shipped one.
- `compare` reads the Windows raw results from `WIN_BUILD` (default `$WINDOWS_RAW_ROOT/openmodelica`); without
  them the stored-point part of the comparison is skipped and the CSV part still runs.
- `loadModel(Modelica, {"4.0.0"}, ...)` loads `~/.openmodelica/libraries/Modelica 4.0.0+maint.om`, installed from the
  `omlibrary` cache on the first omc run of the user.
