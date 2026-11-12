# OpenIPSL verification kits

Scripted environments in which the Modelica tools build and simulate OpenIPSL models with the prebuilt
`Resources/Library` binaries of the IEEE/CIGRE DLL package (OpenIPSL branch `feature/ieee-cigre-dll`, pull request
OpenIPSL/OpenIPSL#433), so that each verification record of that pull request can be repeated. There is one kit per
platform: Linux x86-64 (in WSL2 on Windows), macOS on Apple Silicon, and Linux on 64-bit ARM (a Raspberry Pi). Since
`43f6efd7` the pull request ships the libraries for all of them, and the kits run the tools against the files as
shipped.

No vendor software is included: you bring your own Dymola and System Modeler installers and licences; OpenModelica
is installed from its repositories or built from source. License: BSD 3-Clause (`LICENSE`). Kit version: `VERSION`.
Repository: https://github.com/ALSETLab/openipsl-testenv (public since 2026-11-01; until 2026-10-31 named
`openipsl-linux-testenv`, which GitHub redirects).

## The kits

| Platform | Kit | Tools | First used | Record |
|---|---|---|---|---|
| Linux x86-64 (Ubuntu 24.04 in WSL2) | this folder: `windows/`, `provision/`, `tests/`; guide [below](#linux-x86-64-kit-ubuntu-2404-in-wsl2) | Dymola, OpenModelica, System Modeler | 2026-10-25 | [`linux_record/LINUX_VERIFICATION.md`](linux_record/LINUX_VERIFICATION.md) |
| macOS on Apple Silicon (arm64) | [`macos/`](macos/README.md) | System Modeler, OpenModelica built from source | 2026-10-31 | [`macos/ARM_MACOS_VERIFICATION.md`](macos/ARM_MACOS_VERIFICATION.md); release `arm-macos-2026-10-31` holds the MSL for omc and the raw OpenModelica results |
| Linux aarch64 (Raspberry Pi 400, Raspberry Pi OS trixie) | [`raspberrypi/`](raspberrypi/README.md), machine setup in [`raspberrypi/SETUP.md`](raspberrypi/SETUP.md) | OpenModelica from its arm64 apt repository, gcc and clang builds, a 32-bit `armhf` cross build | 2026-11-01 | [`raspberrypi/ARM_LINUX_AARCH64_VERIFICATION.md`](raspberrypi/ARM_LINUX_AARCH64_VERIFICATION.md) |

The records are copies of the project's records, with machine paths replaced by placeholders. The Windows x64
verification, which every kit compares with, is the record attached to the comment of 2026-10-25 on
OpenIPSL/OpenIPSL#433 (`verification_record_1244ae93.zip`). Paths such as `report/verification_round2/` and
`report/linux/` in the kits' READMEs are folders of the project's records: the first is that Windows record, the
second is described by `linux_record/` (its CSV files on request). Dymola is not available for macOS or for Linux on
ARM, and System Modeler is not available for Linux on ARM.

All kits share the run list (the 15 runs of the 13 IEEE/CIGRE tests), the CSV contract and the metrics fields, so
the records compare run by run. Results in brief:

- Linux x86-64: Dymola 15 of 15, OpenModelica 15 of 15, System Modeler 13 of 15, each within 4.5e-9 relative of its
  Windows result.
- macOS arm64: System Modeler 13 of 15, OpenModelica (built from source) 15 of 15, within 4.6e-9 of Windows.
- Linux aarch64: OpenModelica 15 of 15, within 9.2e-10 of Linux x86-64 and 4.5e-9 of Windows.

The two System Modeler failures are master's native SCRX test, alone and inside `SCRX9_vs_SCRX`, fixed by
OpenIPSL/OpenIPSL#432; they fail on Windows too.

## Where each tool finds the libraries

| Platform | Folder below `Resources/Library` | Files | Searched by |
|---|---|---|---|
| Windows x64 | `win64` | `<Name>.dll` + `<Name>.lib` | Dymola, OpenModelica, System Modeler |
| Linux x86-64 | `linux64` | `lib<Name>.so` | Dymola, OpenModelica, System Modeler |
| Linux aarch64 | `aarch64-linux` | `lib<Name>.so` | OpenModelica (never `linux64` on ARM) |
| macOS arm64 | `aarch64-darwin` and `arm64-darwin` (identical copies) | `lib<Name>.a`, static archives | System Modeler (`aarch64-darwin`), OpenModelica (`arm64-darwin`) |

On macOS the archives are linked into the simulation executable, which then needs no library at run time: neither
tool's executable has an rpath to the package, and OpenModelica starts it through `/bin/sh`, which drops
`DYLD_LIBRARY_PATH`. Each kit's README has the measured details; the Linux x86-64 ones are
[below](#how-each-tool-finds-the-shipped-libraries-measured-with-the-scrx9-test).

## Where to start

- Linux x86-64: the [Steps](#steps) of the guide below.
- macOS: [`macos/README.md`](macos/README.md), "What it needs" and "Steps".
- Raspberry Pi: [`raspberrypi/SETUP.md`](raspberrypi/SETUP.md) for a Pi that is not yet imaged and provisioned, then
  [`raspberrypi/README.md`](raspberrypi/README.md), "With the shipped libraries".

## Layout

```
README.md, LICENSE, VERSION    this file, the licence, the kit version
windows/New-VerifyDistro.ps1   Linux x86-64: creates the WSL2 distro and runs the provisioning steps
provision/                     Linux x86-64: NN_name.sh run as root, NN_name.user.sh as the normal user; lib.sh helpers
tests/export_package.sh        Linux x86-64: one OpenIPSL commit, exported read only with git archive
tests/smoke/                   Linux x86-64: distro, shipped libraries, one smoke test per tool
tests/dymola/, tests/openmodelica/, tests/systemmodeler/
                               Linux x86-64: the full IEEE/CIGRE test set per tool (each folder has its README)
site.env.example               Linux x86-64: the site settings template (copy to site.env, which git ignores)
linux_record/                  the Linux x86-64 verification record with its figures
macos/                         the macOS kit: README, scripts, the patches of its first run, environment, record
raspberrypi/                   the Raspberry Pi kit: SETUP.md, README, scripts (with armhf/), the patches of its
                               first run, environment, record
```

## Linux x86-64 kit (Ubuntu 24.04 in WSL2)

A scripted Linux environment, inside WSL2 on Windows, in which Dymola, OpenModelica and System Modeler build and
simulate OpenIPSL models with the shipped `Resources/Library/linux64` libraries. It was written for the IEEE/CIGRE
DLL package and can be reused for any OpenIPSL model that needs Linux runs. Status: first used on 2026-10-25.

Commands below use these placeholders: `<kit>` is this folder as seen from WSL (for example
`/mnt/c/git/openipsl-testenv`), `<commit>` an OpenIPSL commit, `<records>` the folder that receives the
verification record, `<windows records>` and `<windows raw>` the optional Windows record to compare with
(`WINDOWS_RECORD_ROOT`, `WINDOWS_RAW_ROOT` in `site.env`).

### What it sets up

| Layer | Script | Result |
|---|---|---|
| Distro | `windows/New-VerifyDistro.ps1` | A named WSL2 distro from the official Ubuntu 24.04 LTS image, `/etc/wsl.conf` with systemd, the default user, `metadata` file permissions on `/mnt`, and the Windows PATH kept out |
| Base | `provision/00_base.sh` (root) | The normal user (no password, no sudo), gcc/g++, cmake, ninja, git, Python 3 with numpy, scipy and matplotlib |
| OpenModelica | `provision/10_openmodelica.sh` (root) | `omc` and `omlibrary` of `OM_VERSION`, from the archived release repository of build.openmodelica.org |
| Dymola | `provision/20_dymola.sh` (root) | The Dymola RPM converted with `alien`, the shared libraries its RPM requires, the FlexNet licence file, a Python environment with the Dymola Python interface |
| System Modeler | `provision/30_systemmodeler.sh` (root) | The vendor installer run unattended into `WSM_TARGET`, the libraries the kernel and GUI need |
| Licences | `provision/40_licences.user.sh` (user) | `~/.systemmodeler/mathpass` naming the MathLM server |
| Package | `tests/export_package.sh` (user) | One OpenIPSL commit exported read-only with `git archive` |
| Smoke tests | `tests/smoke/` (user) | `00_distro.sh`: user, systemd, WSLg, PATH, licence servers. `10_shipped_libs.sh`: the package's C tests against the shipped `.so` files. `20_openmodelica.sh`, `30_dymola.py`, `40_systemmodeler.sh`: each tool builds and simulates the SCRX9 DLL test and shows how its executable finds `libSCRX9.so` |
| Tool runs | `tests/<tool>/` (user) | The full test set per tool, with the metrics and CSV files of the verification record (see each folder's README) |

### Why Ubuntu 24.04 LTS

It is the one release that all three vendors list (checked 2026-10-25):

- Dymola 2026x Refresh 1 names "Red Hat Enterprise Linux (RHEL) version 8.6, 64-bit, with gcc version 11.2.1, and
  compatible systems" and defers to the Qt 6.10 supported-platforms list, which has Ubuntu 22.04 and 24.04.
- System Modeler 15.0 lists Ubuntu 22.04, 24.04 and 26.04 (wolfram.com, System Modeler system requirements).
- OpenModelica 1.27.1 has release packages for Ubuntu 22.04, 24.04 and 26.04.

The OpenIPSL linux64 libraries need only glibc symbol versions 2.2.5, 2.3.4 and 2.4, so they load on any of these.

### Requirements

- Windows 11 with WSL2 (tested with WSL 2.7.14, WSLg 1.0.73). WSLg is needed only for the tools' GUIs.
- The vendor installers: Dymola for Linux (the zip with `dymola-<version>.x86_64.rpm`) and System Modeler for Linux
  (`SystemModeler_<version>_LIN.sh`), and network licences for both. OpenModelica is downloaded by apt.
- Network access to the licence servers from WSL. The default NAT networking was enough over a Cisco AnyConnect VPN.
  If it is not, try `networkingMode=mirrored` in `%UserProfile%\.wslconfig`.
- About 10 GB of disk for the distro.

### Steps

1. Copy `site.env.example` to `site.env` and fill in the installer paths, the licence servers, the user name and
   the OpenIPSL repository path. `site.env` is never shared.
2. From a Windows terminal in the kit folder:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1
   ```

   This creates the distro and runs every provisioning step. Logs go to `logs\<distro>\`. Re-running is safe;
   `-Steps 20` re-runs one step and `-SkipCreate` skips the distro creation.
3. Smoke tests, from Windows:

   ```
   wsl -d openipsl-verify-24.04 -- bash <kit as /mnt/...>/tests/smoke/00_distro.sh
   wsl -d openipsl-verify-24.04 -- bash <kit>/tests/export_package.sh <commit>
   wsl -d openipsl-verify-24.04 -- bash <kit>/tests/smoke/10_shipped_libs.sh ~/cigre_verify/pkg/<commit>/OpenIPSL
   ```

   Then one smoke test per tool:

   ```
   wsl -d openipsl-verify-24.04 -e bash <kit>/tests/smoke/20_openmodelica.sh ~/cigre_verify/pkg/<commit>/OpenIPSL
   wsl -d openipsl-verify-24.04 -e /opt/openipsl-kit/venv-dymola/bin/python -I <kit>/tests/smoke/30_dymola.py ~/cigre_verify/pkg/<commit>/OpenIPSL <kit>/site.env
   wsl -d openipsl-verify-24.04 -e env WSM_CXX=/opt/openipsl-kit/bin/g++-nopie bash <kit>/tests/smoke/40_systemmodeler.sh ~/cigre_verify/pkg/<commit>/OpenIPSL
   ```

4. The tool runs: see `tests/<tool>/README.md`.

From PowerShell, run scripts with `wsl -d <distro> -e bash <script>`. Do not pass a one-liner through
`wsl -- bash -c '...'`: wsl.exe parses the line again and `$variables` are lost.

### How each tool finds the shipped libraries (measured with the SCRX9 test)

| Tool | At build time | At run time |
|---|---|---|
| OpenModelica 1.27.1 | `-L<pkg>/Resources/Library/linux64 -lSCRX9` | `DT_RPATH` with `Resources/Library/linux64` (and other candidates), so the executable runs by hand |
| Dymola 2026x Refresh 1 | the absolute path of `linux64/libSCRX9.so` in `dllLibraryPath[]` of `dsmodel.c` | `DT_RUNPATH` with `Resources/Library/linux64` and Dymola's `bin/lib64` |
| System Modeler 15.0 | `-L<pkg>/Resources/Library/linux64 -lSCRX9` | no RUNPATH: the `.sim` lists the folder under `<ExternalLibraries>`, and `LD_LIBRARY_PATH` must name it when the executable runs outside the tool |

### Known trap: System Modeler and Ubuntu's PIE default

System Modeler 15.0 links its external-function evaluator against `lib/linux64/libserializer.a`, which is not
position-independent. Ubuntu's g++ links PIE executables by default, so that link fails with
"relocation R_X86_64_32 ... can not be used when making a PIE object" whenever a model calls a `Library`
function at translation time. Step 30 installs `/opt/openipsl-kit/bin/g++-nopie`, a g++ wrapper that links
executables with `-no-pie`. Name it with `setCompilerPath("/opt/openipsl-kit/bin/g++-nopie")` in a kernel `.mos`,
or as the compiler in Model Center's options. Wolfram tests System Modeler with GCC 8.5, which does not default to PIE.

Reported to Wolfram on 2026-10-26; on 2026-10-27 Wolfram confirmed it and announced a position-independent
`libserializer` for the next System Modeler version, calling the `-no-pie` wrapper a sensible workaround until then.

**To do on the first System Modeler release after 15.0:** rerun `tests/systemmodeler/` with the default g++ (no
`setCompilerPath`) and check that the evaluator links without the relocation error and that every model variable
matches the wrapper's run. If it does, drop the wrapper from `provision/30_systemmodeler.sh` and the
`setCompilerPath` lines, and rewrite this section and trap 1 of `tests/systemmodeler/README.md` as history.

### A nightly distro beside the verification one

The verification environment pins one OpenModelica release (`OM_VERSION`) and is not touched afterwards. To try a
development build of OpenModelica against the same models, for example when a change announced for the next release
(a new error, a changed default) has to be confirmed first hand before the release exists, create a second,
throwaway distro from the apt `nightly` channel instead of changing the first one:

1. Copy `site.env` to `site.nightly.env` (git ignores `site.*.env`), give the distro another `DISTRO_NAME`
   (for example `openipsl-nightly-24.04`) and set `OM_CHANNEL=nightly`. `OM_VERSION` is then ignored.
2. Create it with the base and OpenModelica steps only; it needs no vendor installers and no licences:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File windows\New-VerifyDistro.ps1 -SiteEnv site.nightly.env -Steps 00,10
   ```

   Step 10 then adds `deb [...] https://build.openmodelica.org/apt noble nightly`, installs the newest `omc` and
   `omlibrary` (versions like `1.28.0~dev-NNNN-g<commit>-1`, NNNN the build number) and appends the version
   installed to `/var/lib/openipsl-kit/omc_version` in the distro, since nothing pins it.
3. To move to a newer build later, as root in that distro:
   `apt-get update && apt-get install --only-upgrade omc omlibrary`, then read `omc --version`. Which
   OpenModelica commit a build holds is in its version string (`g<commit>`); compare it with the commit you are
   waiting for on GitHub (`repos/OpenModelica/OpenModelica/compare/<build commit>...<commit>`: status `behind` or
   `identical` means the build includes it).

The nightly distro is not the verification environment: its omc changes with every upgrade, so results from it are
dated with the build number and never enter a verification record in place of a release's. Remove it with
`wsl --unregister <its name>` when done. First used on 2026-11-11 for the Real-equality error of OpenModelica
1.28.0 (OpenIPSL/OpenIPSL#455), with the `omc` package `1.28.0~dev-1860-ge89ef0a-1`.

### Reusing the distro

To reuse the environment on another computer of your own, `wsl --export openipsl-verify-24.04 <file>.tar` and
`wsl --import` it there. The exported image contains the licensed tools, so it is for your own use only; anyone
else follows the steps above with their own installers and licences.

### Removing it

`wsl --unregister openipsl-verify-24.04` deletes the distro and everything installed in it. Nothing outside the
distro is changed, except the kit's own `logs\` folder.
