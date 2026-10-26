# Dymola for Linux runs (kit `tests/dymola/`)

Verification runs of the OpenIPSL IEEE/CIGRE DLL package in Dymola 2026x Refresh 1 for Linux, with the shipped
`Resources/Library/linux64/lib<Name>.so`. The recipe is the Windows round-2 Dymola recipe
(`report/verification_round2/dymola/scripts/`), ported to Linux: the same 15 runs with the same arguments, the
same CSV signals, grids and metric fields, plus the Linux facts (compiler, link line, run-time library search).
First used on 2026-10-25 for commit 1244ae93; record in `report/linux/dymola/`.

## Files

| File | What it does |
|---|---|
| `run_all.sh` | The driver: static checks, the 15 runs (one fresh hidden Dymola each), build diagnostics, the self-comparison against the Windows record, the tables, and the copy of the record to the output folder |
| `dymola_run.py` | One run: `DymolaInterface(dymolapath=.../bin64/dymola.sh, showwindow=False)`; `RequestOption("Standard")` recorded; `Advanced.UI.SkipMessageDialogs = true`, `Advanced.Translation.Log.Timing = true`, `Advanced.Simulation.MaxRunTime = 1800`, `Evaluate = true` (each read before, written back and read again after); `experimentSetupOutput(doublePrecision=true)` (put back with `experimentSetupOutput()`); `openModel(<pkg>/package.mo, changeDirectory=false)`; `cd` to the run folder; `translateModel`; `simulateExtendedModel(..., method="Euler", fixedstepsize=<step>)` or `method="Dassl"`; the statistics of `dslog.txt`; the build facts of the generated `dymosim` (compiler, `readelf -d`, `ldd`, `dllLibraryPath[]` of `dsmodel.c`, build time from the file times). `--translate-only` for diagnostics, `--evaluate true\|false\|keep` |
| `post.py` | A run folder into the contract files `<Test>__<solver>_metrics.json`, `.csv`, `_raw_points.txt`, logs to `logs/<run>/` |
| `dsres.py` | Reader of Dymola's MAT v4 result (unchanged from Windows round 2) |
| `dymola_checks.py` | `checkModel`, normal and pedantic, of every class of `Electrical.Controls.IEEE_CIGRE` and `Tests.Controls.IEEE_CIGRE` (50 classes), one session |
| `diag_build.sh` | Build diagnostics: translate-only sessions under `strace -f -e trace=execve` (the exact `dsbuild.sh` call and the `cc`/`collect2` link line), `readelf`/`ldd`, `LD_DEBUG=libs` (how the loader finds `lib<Name>.so`), `LD_DEBUG=files` over one simulation |
| `compare_windows.py` | Self-comparison against the Windows round-2 Dymola record: CSV max \|difference\| per signal, solver statistics, and the stored doubles of the two `dsres.mat` files; also compares two Linux records (`--title`, `--name`) |
| `raw_summary.py` | The stored-point part of a comparison as a Markdown table |
| `headline_values.py` | The values the Windows round-2 README quotes, recomputed from both CSV sets |
| `codediff.sh` | `dsmodel.c` of Linux against Windows for every run (are the two translations the same equations?) |
| `first_difference.py` | Diagnostic: the first stored point where a Linux and a Windows result differ, and in which variables |
| `diag_timing.sh` | Diagnostic: a `dymosim` run again outside Dymola under `/usr/bin/time`, pinned to single vCPUs, and under `strace -c` (no licence needed) |
| `table.py`, `messages.py` | The table of runs and the unique tool messages (Markdown) |

## How to run

Prerequisites: the kit's distro with Dymola provisioned (`provision/20_dymola.sh`), the licence server reachable
(VPN), and the package exported with `tests/export_package.sh <commit>`. One Dymola session at a time: the
driver starts them one after the other.

From Windows (PowerShell or Git Bash; in Git Bash prefix `MSYS_NO_PATHCONV=1`):

```
wsl.exe -d openipsl-verify-24.04 -e bash <kit>/tests/dymola/run_all.sh /home/<user>/cigre_verify/pkg/<commit>/OpenIPSL <records>/dymola
```

Inside the distro (normal user):

```
bash <kit>/tests/dymola/run_all.sh ~/cigre_verify/pkg/<commit>/OpenIPSL <output dir> [run names...]
```

Arguments: the exported package folder (`.../OpenIPSL`) and the output folder of the record. Optional run names
(e.g. `SCRX9__dassl GFL_Fault__euler`) restrict the runs. Environment variables (put them in a small wrapper
script that exports them and calls `run_all.sh`; `wsl.exe -e` does not pass Windows variables):

| Variable | Default | Meaning |
|---|---|---|
| `BUILD` | `~/cigre_verify/dymola` | build tree and raw results (ext4) |
| `DYMOLA_SH` | `/opt/dymola-2026xRefresh1-x86_64/bin64/dymola.sh` | Dymola start script |
| `CAP` | 1800 | `Advanced.Simulation.MaxRunTime` in s |
| `EVALUATE` | `true` | Dymola's flag `Evaluate` (see below) |
| `STEPS` | `checks runs diag compare copy` (with run names: `runs compare copy`) | steps to do |
| `WINDOWS_REC` | `$WINDOWS_RECORD_ROOT/dymola` (kit `site.env`) | Windows round-2 record (CSV, metrics); unset = the self-comparison is skipped |
| `WINDOWS_RUNS` | `$WINDOWS_RAW_ROOT/dymola/runs` (kit `site.env`) | Windows round-2 build tree (`dsres.mat`, `dsmodel.c`), read only; unset = the stored-point comparison and `codediff.sh` are skipped |
| `KIT_SITE` | `<kit>/site.env` | the site settings file the two defaults above come from (optional) |

The build tree and the raw results (`$BUILD/runs/<run>/dsres.mat`, 8.7 GB for the 15 runs) stay in the distro's
ext4. The record is assembled in `$BUILD/record` and copied with `cp -r` to the output folder at the end, so
nothing is written into a synced folder (Dropbox, OneDrive) while Dymola runs. The full set takes about 4 minutes (15 fresh Dymola sessions of
about 7 s, plus 24 s for GFL_PowerRamp with DASSL).

The `Evaluate=false` experiment of the record (Dymola's default setting), in its own build tree, inside the distro:

```
EVALUATE=false BUILD=~/cigre_verify/dymola/evaluate_false STEPS="checks runs compare" bash run_all.sh <pkg> ~/cigre_verify/dymola/evaluate_false/record
```

or from Windows (`env` sets the variables, since `wsl.exe -e` passes no Windows variables):

```
wsl.exe -d openipsl-verify-24.04 -e env EVALUATE=false BUILD=/home/<user>/cigre_verify/dymola/evaluate_false "STEPS=checks runs compare" bash <kit>/tests/dymola/run_all.sh /home/<user>/cigre_verify/pkg/<commit>/OpenIPSL /home/<user>/cigre_verify/dymola/evaluate_false/record
```

The record of that set, without its CSVs, is `report/linux/dymola/evaluate_false/`.

Single steps, with `/opt/openipsl-kit/venv-dymola/bin/python -I -B`: `dymola_run.py --help`; `post.py --run <run
folder> --name <run> --out <record> --grid <dt> --stop <s>`; `dymola_checks.py --lib <pkg> --work <dir> --out <dir>`;
`bash diag_build.sh <pkg> <build> <record>`; `bash diag_timing.sh <run folder> <output file> 3 0 6 12 18 23`;
`first_difference.py --linux <dsres.mat> --windows <dsres.mat>`.

## What differs from the Windows recipe

- `Evaluate = true` is set explicitly. The Windows round-2 record ran with it although its scripts do not set it:
  it is a persistent flag of the Windows `setup.dymx` (`<global-flag name="Evaluate" value="true"/>`), and each of
  its 15 translation logs prints `Settings | Evaluate = true`. Dymola's default, and this distro's setup, is
  `false`, which translates other equations (GFM_EMTPFull: a linear system of size 24 and dynamic state selection
  instead of none) and needs 2.5-3.3 times the simulation wall time in the six tests with the EMTP transformer;
  GFL_PowerRamp with DASSL takes
  6,438,627 instead of 7,477,801 steps and 111 s instead of 17 s. With `Evaluate = true` the generated `dsmodel.c`
  holds the same equations as on Windows and the solver statistics are identical.
- Dymola is started from its Linux start script (`bin64/dymola.sh`, which sets `DYMOLA` and `LD_LIBRARY_PATH`
  for Dymola itself); the Python interface is the wheel in `/opt/openipsl-kit/venv-dymola`.
- `python -I -B`: `-B` so that no `__pycache__` is written into the kit folder.
- `compile_s` is the C build time measured from the files (`dymosim` mtime minus `dsmodel.c` mtime): Dymola for
  Linux writes "Compilation time: 0.0014 s" in the translation log, which is not the gcc build (1.6-2.6 s,
  confirmed by the start and exit of the `dsbuild.sh` process under strace). Dymola's figure is kept as
  `extra.dymola_reported_compilation_time_s`.
- The metrics carry `platform` and `compiler`; the message parser also reads gcc and GNU ld messages.
- Dymola's settings file on Linux is `~/.dassaultsystemes/dymola/2026x Refresh 1/setup.dymx` (lower-case
  `dymola`); the driver diffs it before and after a run set (`logs/setup_dymx_diff.txt`).
