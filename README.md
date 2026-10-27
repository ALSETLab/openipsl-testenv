# OpenIPSL Linux verification kit

A scripted Linux environment, inside WSL2 on Windows, in which three Modelica tools build and simulate OpenIPSL
models with the shipped `Resources/Library/linux64` libraries. It was written to verify the IEEE/CIGRE DLL
package (OpenIPSL branch `feature/ieee-cigre-dll`, replacing pull request #362), and it can be reused for any
OpenIPSL model that needs Linux runs.

Kit version: see `VERSION`. Status: draft 0.1.0, first used on 2026-10-25 for the Linux verification of the
IEEE/CIGRE DLL package. Repository: https://github.com/ALSETLab/openipsl-linux-testenv (private for now).
License: BSD 3-Clause (`LICENSE`). No vendor software is included: you bring your own installers and licences.

Commands below use these placeholders: `<kit>` is this folder as seen from WSL (for example
`/mnt/c/git/openipsl-linux-testenv`), `<commit>` an OpenIPSL commit, `<records>` the folder that receives the
verification record, `<windows records>` and `<windows raw>` the optional Windows record to compare with
(`WINDOWS_RECORD_ROOT`, `WINDOWS_RAW_ROOT` in `site.env`).

## What it sets up

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

## Why Ubuntu 24.04 LTS

It is the one release that all three vendors list (checked 2026-10-25):

- Dymola 2026x Refresh 1 names "Red Hat Enterprise Linux (RHEL) version 8.6, 64-bit, with gcc version 11.2.1, and
  compatible systems" and defers to the Qt 6.10 supported-platforms list, which has Ubuntu 22.04 and 24.04.
- System Modeler 15.0 lists Ubuntu 22.04, 24.04 and 26.04 (wolfram.com, System Modeler system requirements).
- OpenModelica 1.27.1 has release packages for Ubuntu 22.04, 24.04 and 26.04.

The OpenIPSL linux64 libraries need only glibc symbol versions 2.2.5, 2.3.4 and 2.4, so they load on any of these.

## Requirements

- Windows 11 with WSL2 (tested with WSL 2.7.14, WSLg 1.0.73). WSLg is needed only for the tools' GUIs.
- The vendor installers: Dymola for Linux (the zip with `dymola-<version>.x86_64.rpm`) and System Modeler for Linux
  (`SystemModeler_<version>_LIN.sh`), and network licences for both. OpenModelica is downloaded by apt.
- Network access to the licence servers from WSL. The default NAT networking was enough at RPI over the Cisco
  AnyConnect VPN. If it is not, try `networkingMode=mirrored` in `%UserProfile%\.wslconfig`.
- About 10 GB of disk for the distro.

## Steps

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

## How each tool finds the shipped libraries (measured with the SCRX9 test)

| Tool | At build time | At run time |
|---|---|---|
| OpenModelica 1.27.1 | `-L<pkg>/Resources/Library/linux64 -lSCRX9` | `DT_RPATH` with `Resources/Library/linux64` (and other candidates), so the executable runs by hand |
| Dymola 2026x Refresh 1 | the absolute path of `linux64/libSCRX9.so` in `dllLibraryPath[]` of `dsmodel.c` | `DT_RUNPATH` with `Resources/Library/linux64` and Dymola's `bin/lib64` |
| System Modeler 15.0 | `-L<pkg>/Resources/Library/linux64 -lSCRX9` | no RUNPATH: the `.sim` lists the folder under `<ExternalLibraries>`, and `LD_LIBRARY_PATH` must name it when the executable runs outside the tool |

## Known trap: System Modeler and Ubuntu's PIE default

System Modeler 15.0 links its external-function evaluator against `lib/linux64/libserializer.a`, which is not
position-independent. Ubuntu's g++ links PIE executables by default, so that link fails with
"relocation R_X86_64_32 ... can not be used when making a PIE object" whenever a model calls a `Library`
function at translation time. Step 30 installs `/opt/openipsl-kit/bin/g++-nopie`, a g++ wrapper that links
executables with `-no-pie`. Name it with `setCompilerPath("/opt/openipsl-kit/bin/g++-nopie")` in a kernel `.mos`,
or as the compiler in Model Center's options. Wolfram tests System Modeler with GCC 8.5, which does not default to PIE.

Reported to Wolfram on 2026-10-26; on 2026-10-27 Wolfram confirmed it and announced a position-independent
`libserializer` for the next System Modeler version, calling the `-no-pie` wrapper a sensible workaround until then (record:
`ALSETLab/openipsl-tool-reports`, `system-modeler/2026-10-26_evaluator-pie/`).

**To do on the first System Modeler release after 15.0:** rerun `tests/systemmodeler/` with the default g++ (no
`setCompilerPath`) and check that the evaluator links without the relocation error and that every model variable
matches the wrapper's run. If it does, drop the wrapper from `provision/30_systemmodeler.sh` and the
`setCompilerPath` lines, and rewrite this section and trap 1 of `tests/systemmodeler/README.md` as history.

To reuse the environment on another computer of your own, `wsl --export openipsl-verify-24.04 <file>.tar` and
`wsl --import` it there. The exported image contains the licensed tools, so it is for your own use only; anyone
else follows the steps above with their own installers and licences.

## Layout

```
windows/New-VerifyDistro.ps1   creates the distro and runs the provisioning steps
provision/                     NN_name.sh run as root, NN_name.user.sh as the normal user; lib.sh shared helpers
tests/export_package.sh        one OpenIPSL commit, exported read only with git archive
tests/smoke/                   distro, shipped libraries, one smoke test per tool
tests/dymola/, tests/openmodelica/, tests/systemmodeler/
                               the full IEEE/CIGRE test set per tool (each folder has its README)
site.env.example               the site settings template (copy to site.env, which git ignores)
```

## Removing it

`wsl --unregister openipsl-verify-24.04` deletes the distro and everything installed in it. Nothing outside the
distro is changed, except the kit's own `logs\` folder.
