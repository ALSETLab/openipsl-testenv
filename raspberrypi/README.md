# raspberrypi/: native Linux aarch64 verification of the OpenIPSL IEEE/CIGRE DLL package (Raspberry Pi 400)

This folder is the Raspberry Pi twin of `macos/`. It holds the scripts, patches and environment record used on
2026-11-01 for the OpenModelica-only verification of OpenIPSL pull request #433 (branch `feature/ieee-cigre-dll`,
head `b05fa04440809291d61f13045f8586d186613f66`) on a Raspberry Pi 400 running Raspberry Pi OS 64-bit (Debian 13
trixie). Wolfram ships no System Modeler for Linux arm64, so this machine has no System Modeler column. The record
is `ARM_LINUX_AARCH64_VERIFICATION.md`; on the Pi it is at `~/arm-verify/`. Start with `SETUP.md` if the Pi is not yet imaged
and provisioned.

## Contents

| Path | What it is |
|---|---|
| `SETUP.md` | How to image a card with 64-bit Raspberry Pi OS, reach the Pi by SSH key from a desktop and run `provision_pi.sh`: the steps before anything below, written for a reader who starts from an empty card |
| `scripts/provision_pi.sh` | Provisioning of a fresh 64-bit Raspberry Pi OS image (needs sudo once): build tools, OpenModelica 1.27.2 from `build.openmodelica.org/apt trixie stable` (packages `omc omlibrary`), first MSL load |
| `scripts/make_pkg.sh` | Package under test: a `git archive` of the checkout's HEAD, plus the installed `Resources/Library/aarch64-linux`, plus a `COMMIT` file |
| `scripts/probe_folders.sh`, `scripts/folder_probe.c`, `scripts/FolderProbe/package.mo` | Which `Resources/Library/<folder>` omc links and loads. Eight layouts; each copy of `libFolderProbe.so` returns its own folder number |
| `scripts/omc_verify_pi.py`, `scripts/run_all_om_pi.sh` | The 15 contract runs plus checks, extras, timing, binding and self-comparison (port of the macOS `omc_verify_macos.py` / `run_all_om_macos.sh`; same run list, `.mos` text, signals, grids and metrics fields) |
| `scripts/armhf/` | 32-bit ARM cross build without sudo: `make_sysroot.sh` (unpacks the armhf libc/libgcc `.deb` files and `lld-19`), `toolchain_armhf.cmake` (processor `armv7l`), `toolchain_armhf_on_aarch64_kernel.cmake` (processor `aarch64`, as a 32-bit userland on a 64-bit kernel reports), `run_armhf.sh` (ctest emulator through the unpacked loader) |
| `scripts/UnitProbe.mo` | Negative controls for `--unitChecking` |
| `scripts/runs.json` | The contract run list (reference copy; `omc_verify_pi.py` carries the same list in code) |
| `scripts/fma_diff.py` | Worst difference per signal between two CSV records of the same runs (the FMA control against the record) |
| `scripts/compare_arm.py` | Comparison against Windows round 2, Linux x86_64 and (with `--macos` / `--macos-json`) the macOS arm64 record. It imports `report/linux/compare_linux.py` from `<root>/records/report/linux/` |
| `patches/0001..0003` | The three CMake commits of the ARM work (platform folders; `-ffp-contract=off`; macOS install names). As pushed to #433 (`3da33828`, `34985981`, `053f0a75` on `b05fa044`, 2026-11-01); since then `git clone --branch feature/ieee-cigre-dll` already contains them, and `git am` is only needed on an older checkout |
| `env/ENVIRONMENT_2026-11-01.txt` | Machine, OS, toolchain and package versions of the record run |
| `ARM_LINUX_AARCH64_VERIFICATION.md` | The record (a copy of `~/arm-verify/ARM_LINUX_AARCH64_VERIFICATION.md`) |

## How to reproduce (as the Pi login user, from `~/arm-verify/`, with this folder copied to `~/arm-verify/kit-raspberrypi/`)

```
git clone --branch feature/ieee-cigre-dll https://github.com/OpenIPSL/OpenIPSL.git OpenIPSL
git -C OpenIPSL checkout -b arm-platform-folders b05fa044
git -C OpenIPSL am ../kit-raspberrypi/patches/000{1,2,3}-*.patch
cmake -S OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE -B build/ieee_cigre -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/ieee_cigre && ctest --test-dir build/ieee_cigre --output-on-failure && cmake --install build/ieee_cigre
bash scripts/make_pkg.sh OpenIPSL pkg/record
bash scripts/probe_folders.sh raw/openmodelica/lookup
WIN_RECORD=$PWD/records/report/verification_round2/openmodelica nohup bash scripts/run_all_om_pi.sh pkg/record/OpenIPSL raw/openmodelica/record build/om_runs > raw/openmodelica/run_all_nohup.log 2>&1 &
python3 -I scripts/compare_arm.py --om raw/openmodelica/record --om-raw build/om_runs --win records/report/verification_round2 --linux records/report/linux --macos records/iterations/2026-10-31_I9-arm-verification/macos/raw --macos-json records/iterations/2026-10-31_I9-arm-verification/macos/comparison_final/comparison_arm.json --arm-label "OpenModelica 1.27.2 (arm64 apt, trixie)" --out comparison_final --no-figs
```

FMA control (after the record; `build/fma_variants/so_gnu11/` holds the two libraries compiled with `-std=gnu11`):

```
mkdir -p pkg/fma_gnu11 && cp -a pkg/record/OpenIPSL pkg/fma_gnu11/ && cp build/fma_variants/so_gnu11/*.so pkg/fma_gnu11/OpenIPSL/Resources/Library/aarch64-linux/
STEPS=run KEYS="GFL_Fault__euler GFL_VoltageStep__euler SCRX9__dassl" bash scripts/run_all_om_pi.sh pkg/fma_gnu11/OpenIPSL raw/openmodelica/record_fma_gnu11 build/om_runs_fma > raw/openmodelica/run_fma_nohup.log 2>&1
python3 -I scripts/fma_diff.py raw/openmodelica/record raw/openmodelica/record_fma_gnu11 GFL_Fault__euler GFL_VoltageStep__euler SCRX9__dassl
```

To wait for the background driver, poll its PID (`while kill -0 <pid>; do sleep 30; done`), not `pgrep -f
run_all_om_pi.sh`: the waiting shell's own command line contains that name, so the loop never ends.

`records/` is the copy of the x64 records (`report/verification_round2/`, `report/linux/`) and of the macOS record
folder, as for the Mac.

## Traps

1. **The CMake source path has two `OpenIPSL` levels.** The source is `OpenIPSL/OpenIPSL/Resources/C-Sources/IEEE_CIGRE`
   (repository folder, then library folder), not `OpenIPSL/Resources/...`.
2. **No passwordless sudo.** The trixie image gives the Imager-created user no `NOPASSWD` rule. Only
   `provision_pi.sh` needs sudo; everything else runs as the user.
3. **`omlibrary` is a zip cache.** `/usr/share/omlibrary/cache` holds zips; the first `loadModel(Modelica)` unpacks
   them into `~/.openmodelica/libraries/`. There is nothing under `/usr/lib/omlibrary`. omc ignores `MODELICAPATH`.
4. **Folder lookup on aarch64 Linux.** omc 1.27.2 links and loads from `Resources/Library/`, then
   `Resources/Library/aarch64-linux` (listed twice in its search list), then the base folder again. It never looks
   in `linux64`, so the x86-64 `linux64` libraries in the repository are never tried, and an unpatched CMake
   install (which writes into `linux64`) fails with `cannot find -l<Name>`. A library in the base folder shadows the
   one in `aarch64-linux`.
5. **The executable needs no `LD_LIBRARY_PATH`.** omc writes a DT_RPATH (`--disable-new-dtags`) with its own
   library folders, `~/.openmodelica/binaries/<Library>` and the package folders, as on x86-64 Linux.
6. **Fused multiply-add.** gcc 14 in `-std=c11` mode (what the CMake project passes) does not contract, with or
   without `-ffp-contract=off` (0 `fmadd`/`fmsub`; identical `.text`). `-std=gnu11` or `-ffp-contract=fast`
   produces 76 fused instructions in `GFM_GFL_IBR.o` and 3 in `SCRX9.o`. Patch 0002 keeps that from happening when
   someone builds outside the CMake flags.
7. **RAM is 3.7 GiB.** Run one omc process at a time (`run_all_om_pi.sh` is serial) and never build omc on the Pi.
8. **No matplotlib.** Python 3.13 with numpy only (Debian's PEP 668 blocks `pip install --user`). Run
   `compare_arm.py` with `--no-figs`, or make the figures on another machine.
9. **`claude` is on PATH only in login shells** (`~/.local/bin`, added by Debian's `.profile`).
10. **No System Modeler for Linux arm64.** `wolfram-engine` 15.0.1 (Mathematica kernel) is installed, but it has no
    `WSMKernel` and cannot replace System Modeler.
11. **32-bit ARM.** A 32-bit Raspberry Pi OS on a Pi 4/400 runs a 64-bit kernel and CMake reports `aarch64`; patch
    0001 tests `CMAKE_SIZEOF_VOID_P` so such builds go to `linux32`, not `aarch64-linux`. omc for armhf (1.27.2)
    searches `arm-linuxeabihf`, which the CMake project does not produce: OpenModelica on 32-bit ARM is not supported.
12. **clang contracts by default** on Linux aarch64 too (77 fused instructions in GFM, 5 in SCRX9, also at `-O0`);
    gcc does not in `-std=c11` mode. Patch 0002 covers both.
