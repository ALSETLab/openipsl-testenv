# Setting up a Raspberry Pi for the aarch64 Linux verification

How to put 64-bit Raspberry Pi OS on a card, reach the Pi over SSH from a desktop without a password, and provision
it with the build tools and OpenModelica that `README.md` assumes. Written from the 2026-11-01 setup of the
Raspberry Pi 400 used for the first record; the versions in section 8 are what that day's repositories served.
Nothing here is specific to the Pi 400: any Raspberry Pi 4, 400 or 5 with at least 4 GB of RAM will do.

Conventions: `<pi-user>` is the login user you create in Imager; the desktop is the computer you work from (the
commands are shown for PowerShell on Windows and are the same on macOS or Linux except where noted); the Pi is
reached as `raspberrypi.local` (mDNS) and, once `~/.ssh/config` is written, as `pi400`.

## 1. What you need

| Item | Note |
|---|---|
| Raspberry Pi 4, 400 or 5, 4 GB RAM or more | The record machine: Pi 400 Rev 1.0, 4 GB. The Pi 400 has no power button: power-cycle by unplugging USB-C |
| microSD card, 32 GB or more | 64 GB used; after provisioning plus `wolfram-engine` 16 GB are in use |
| USB-C power supply (5 V, 3 A) | |
| Card reader on the desktop | |
| Raspberry Pi Imager 2.x on the desktop | Windows: `winget install RaspberryPiFoundation.RaspberryPiImager`. macOS/Linux: https://www.raspberrypi.com/software/ |
| Wi-Fi or Ethernet on the same LAN as the desktop | mDNS (`raspberrypi.local`) must cross between them; on a guest or campus network use the IP address instead |
| Optional: HDMI monitor and keyboard, or a KVM-over-IP | Only for watching the first boot; everything else is done over SSH |

## 2. One SSH key on the desktop

Create a key for the ARM machines if you do not have one (no passphrase is fine for a lab machine; use one if the
desktop is shared):

```
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_arm -C "<desktop-user>@<desktop> arm-boxes"
```

Keep `~/.ssh/id_ed25519_arm.pub` at hand: Imager asks for its content in step 3.

## 3. Image the card with Raspberry Pi Imager

Imager v2 (Qt 6) ignores synthetic input from automation tools; do these steps by hand.

1. Put the card in the reader. Start Imager.
2. **Device**: Raspberry Pi 4 (this family covers the Pi 400) or Raspberry Pi 5.
3. **Operating system**: Raspberry Pi OS (64-bit). Take the desktop edition unless you know you want Lite; the
   desktop one is what the record used (`2026-10-06-raspios-trixie-arm64.img.xz`, Debian 13 trixie, 1.36 GB download,
   6.7 GB extracted). Check it says **64-bit**: OpenModelica and Claude Code have no 32-bit arm builds.
4. **Storage**: the card. Check the size matches your card (not an internal disk). Imager erases it.
5. **Next**, then **Edit settings** (OS customisation):
   - General: hostname `raspberrypi`; user `<pi-user>` with a password you type yourself; Wi-Fi SSID, passphrase,
     country; locale (time zone and keyboard).
   - Services: **Enable SSH**, **Allow public-key authentication only**, and paste the content of
     `~/.ssh/id_ed25519_arm.pub` into the authorized keys box (one line, starts with `ssh-ed25519`). Password login
     over SSH stays off.
   - Raspberry Pi Connect: off (not needed; SSH is enough).
   - Save.
6. **Yes** to apply the customisation, **Yes** to erase the card. Writing took about 4 minutes at 27 MB/s on USB 3;
   let the verification pass run (it reads the whole card back).
7. Eject the card.

Imager keeps the customisation in its settings (Windows: registry key
`HKCU\Software\Raspberry Pi\Raspberry Pi Imager\imagecustomization`). It contains the Wi-Fi passphrase and the
password hash: never export or commit it.

## 4. First boot

1. Power the Pi **off** (unplug USB-C), swap the card, plug the power back in. A card swapped while the Pi is
   running does not reboot it: the old system keeps running from RAM with a dead root file system (`EXT4-fs error`
   messages, SSH connections reset with `kex_exchange_identification: Connection reset by peer`), and nothing works
   until you power-cycle.
2. First boot takes one to two minutes: the file system is resized, SSH host keys are regenerated
   (`regenerate_ssh_host_keys.service`), the user is created, Wi-Fi joins. On a monitor you see the Raspberry Pi
   splash and then the desktop.
3. From the desktop, wait until it answers:

```
ssh -o ConnectTimeout=5 -i ~/.ssh/id_ed25519_arm <pi-user>@raspberrypi.local uname -m
```

`Connection refused` means the Pi is up but sshd not yet; retry every 20 s. The first success asks you to accept the
host key; the answer must be `aarch64`.

If `raspberrypi.local` does not resolve, find the address on your router's DHCP table (the Pi's hostname is
`raspberrypi`), or on the Pi's desktop with `hostname -I`, and use the IP instead of the name below.

## 5. SSH alias and known hosts on the desktop

If this card replaces an earlier Raspberry Pi OS under the same name, drop the old host key first (the new image
has new keys; otherwise ssh refuses with `REMOTE HOST IDENTIFICATION HAS CHANGED`):

```
ssh-keygen -R raspberrypi.local
```

Add to `~/.ssh/config` (create the file if missing; on Windows it is `C:\Users\<you>\.ssh\config`):

```
Host pi400
  HostName raspberrypi.local
  User <pi-user>
  IdentityFile ~/.ssh/id_ed25519_arm
  IdentitiesOnly yes
```

Done when this prints `aarch64` without asking for anything:

```
ssh pi400 uname -m
```

## 6. Provision

Copy the script and run it in a terminal you can watch (it asks for the user's password once, for sudo; the
trixie image gives the Imager-created user no passwordless sudo):

```
scp scripts/provision_pi.sh pi400:~/
ssh -t pi400 "bash ~/provision_pi.sh 2>&1 | tee ~/provision.log"
```

What it does, in order:

| Step | What | Where it comes from |
|---|---|---|
| 0 | `sudo -v` once, then a background keepalive so apt never stalls on a password prompt | |
| 1 | Checks `uname -m` is `aarch64` and prints the OS and board model; stops otherwise | |
| 2 | git, cmake, ninja-build, build-essential, python3, python3-numpy, curl, ca-certificates, gnupg | Raspberry Pi OS (Debian trixie) |
| 3 | OpenModelica `omc` and `omlibrary`, then one `loadModel(Modelica)` to unpack the MSL cache into `~/.openmodelica/libraries/` | `https://build.openmodelica.org/apt trixie stable`, signed by `openmodelica.asc` |
| 4 | Claude Code (native installer) into `~/.local/bin`, added to PATH in `.bashrc` | `https://claude.ai/install.sh` |
| 5 | Reports whether `wolframscript` / `wolfram` exist and what `apt-cache policy wolfram-engine` offers. **Installs nothing** | |
| 6 | `free -h`, `df -h` | |

About 10 minutes on Wi-Fi. Step 3 pulls clang and LAPACK as omc dependencies (about 1 GB). After it, check:

```
ssh pi400 'omc --version; cmake --version | head -1; gcc --version | head -1; ls ~/.openmodelica/libraries'
```

Expected: `OpenModelica 1.27.2`, cmake 3.31, gcc 14.2, and a `libraries` folder with `Modelica 4.0.0`, `Modelica 4.1.0`,
`Complex`, `ModelicaServices` and friends.

Optional, only if you need the Mathematica kernel on the Pi (System Modeler does not exist for Linux arm64, so this
is not part of the verification):

```
ssh -t pi400 'sudo apt-get install -y wolfram-engine'
```

2.2 GB download, 5.4 GB on disk, EULA pre-accepted by the Pi OS image; gives `wolframscript` and `wolfram`
(Mathematica 15.0.1 kernel), under `/opt/Wolfram/WolframEngine/`.

### If your record must match another machine's OpenModelica version

The trixie `stable` channel serves one version (1.27.2 on 2026-11-01). Older arm64 builds stay in the pool,
`https://build.openmodelica.org/apt/pool/contrib-trixie/`: download the five packages `omc`, `omc-common`,
`libomc`, `libomcsimulation`, `omlibrary` of the wanted version, then

```
sudo apt-get install --allow-downgrades ./omc_<ver>_arm64.deb ./omc-common_<ver>_all.deb ./libomc_<ver>_arm64.deb ./libomcsimulation_<ver>_arm64.deb ./omlibrary_<ver>_all.deb
sudo apt-mark hold omc omc-common libomc libomcsimulation omlibrary
```

The first record kept 1.27.2 and labelled its column accordingly (see `ARM_LINUX_AARCH64_VERIFICATION.md`).

## 7. Optional: Claude Code and the Claude desktop app

- Log in once: `ssh -t pi400 "/home/<pi-user>/.local/bin/claude"` and follow the browser login. Give the full path:
  a non-interactive `ssh -t pi400 claude` does not read `.bashrc`, and PowerShell expands `~` on the desktop, not on
  the Pi.
- To run a Claude Code session on the Pi from the desktop app: New session, **Add SSH connection**, name `pi400`,
  host `<pi-user>@raspberrypi.local`, port empty (22), key `~/.ssh/id_ed25519_arm`, worktree folder empty. The app's
  sessions start a login shell, where Debian's `.profile` puts `~/.local/bin` on PATH, so `claude` is found.

## 8. Versions on 2026-11-01

| Component | Version |
|---|---|
| Raspberry Pi Imager | 2.0.12 |
| Image | Raspberry Pi OS (64-bit) with desktop, 2026-10-06, Debian 13 trixie, kernel 6.18.50+rpt-rpi-v8 |
| gcc / cmake / ninja / python3 / git | 14.2.0 / 3.31.6 / 1.12 / 3.13.5 (+numpy) / 2.47.3 |
| OpenModelica (`omc`, `omlibrary`) | 1.27.2-1 (the only version in `trixie stable` arm64) |
| Claude Code | 2.1.316 |
| wolfram-engine (optional) | 15.0.1+202608182322, from `archive.raspberrypi.com trixie/main` |
| Disk after everything | 16 GB used of 58 GB; 7.5 GB without wolfram-engine |

## 9. Traps

1. **Power-cycle after a card swap** (section 4). The symptoms look like a network or sshd problem; they are not.
2. **`omlibrary` is a zip cache**, `/usr/share/omlibrary/cache`, not a library tree. The MSL appears under
   `~/.openmodelica/libraries/` only after the first `loadModel(Modelica)` of each user. There is nothing under
   `/usr/lib/omlibrary`, and omc ignores `MODELICAPATH`.
3. **No passwordless sudo** for the Imager-created user on trixie. The script keeps one sudo ticket alive; run
   anything else that needs root in a terminal where you can type the password.
4. **4 GB of RAM.** Never build omc on the Pi; run one omc process at a time.
5. **No matplotlib**: Debian's PEP 668 blocks `pip install --user`. Use `python3-numpy` from apt and make figures
   elsewhere, or create a venv.
6. **`claude` is on PATH only in login shells** (`~/.local/bin`).
7. **KVM-over-IP** (if you watch the boot through one): the on-screen menu offers few key combos; others are typed
   with the real keyboard focus in the video area. A paste button that types the clipboard is handy for long
   commands.
8. **Imager and automation**: Imager 2.x ignores synthetic clicks and keystrokes. Drive it by hand.
