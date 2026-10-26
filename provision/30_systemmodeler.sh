#!/usr/bin/env bash
# Step 30 (root): Wolfram System Modeler for Linux from the vendor .sh installer, run unattended.
# The installer is a Makeself archive: options before "--" go to Makeself (--nox11: never open an xterm),
# options after it go to Wolfram's installer (-silent: no prompts, log in /tmp/InstallerLog-<n>).
# Makeself unpacks about 0.4 GB into the current folder, so it runs from $WORK_DIR, not from the Windows drive.
# System Modeler compiles models with the system g++ (build-essential, step 00).
. "$(dirname "$0")/lib.sh"
need_root
header
need_var WSM_INSTALLER WSM_TARGET

log "apt: libraries System Modeler needs (libatomic per Wolfram's requirements; Kerberos for the kernel; NSS, ALSA, xcb for the GUI)"
apt-get update
apt_install build-essential libatomic1 libgssapi-krb5-2 libnss3 libasound2t64 libxkbfile1 \
  libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 \
  libxcb-util1 libxcb-xkb1 libxkbcommon-x11-0 libegl1 libgl1 libopengl0 libfontconfig1

# The installer registers desktop menu entries with xdg-desktop-menu, which fails with "No writable system
# menu directory found" on the minimal WSL image. These folders let it succeed, and WSLg then lists Model Center
# and Simulation Center in the Windows Start menu.
mkdir -p /etc/xdg/menus /usr/share/applications /usr/share/desktop-directories

if [ -x "$WSM_TARGET/bin/WSMKernelX" ] && [ "${WSM_REINSTALL:-0}" != 1 ]; then
  log "System Modeler is already installed in $WSM_TARGET (set WSM_REINSTALL=1 to install again)"
else
  [ -f "$WSM_INSTALLER" ] || die "WSM_INSTALLER not found: $WSM_INSTALLER"
  w="$WORK_DIR/wsm"
  mkdir -p "$w"
  cd "$w"
  log "check the installer archive"
  bash "$WSM_INSTALLER" --check
  log "install into $WSM_TARGET (links in /usr/local/bin)"
  bash "$WSM_INSTALLER" --nox11 -- -silent -targetdir="$WSM_TARGET" -execdir=/usr/local/bin
fi
[ -x "$WSM_TARGET/bin/WSMKernelX" ] || die "no $WSM_TARGET/bin/WSMKernelX after the install (see $WSM_TARGET/InstallerLog)"
[ -f "$WSM_TARGET/InstallerLog" ] && tail -n 6 "$WSM_TARGET/InstallerLog"
if [ -s "$WSM_TARGET/InstallErrors" ]; then
  log "installer reported:"
  cat "$WSM_TARGET/InstallErrors"
  if grep -qv '^xdg-desktop-menu' "$WSM_TARGET/InstallErrors"; then
    die "System Modeler installer errors other than desktop menu integration (above)"
  fi
  log "only desktop menu integration failed; the kernel and the GUI are installed"
fi

# System Modeler 15.0's lib/linux64/libserializer.a is not position-independent (R_X86_64_32 relocations),
# and Ubuntu's g++ links position-independent executables by default. The kernel's external-function
# evaluator (it runs Library functions such as sampleTime() at translation) links against that archive and
# fails with "relocation R_X86_64_32 ... can not be used when making a PIE object" (measured 2026-10-25).
# This wrapper links executables with -no-pie; use it with setCompilerPath("/opt/openipsl-kit/bin/g++-nopie")
# in a kernel .mos, or as the compiler path in Model Center's options.
mkdir -p /opt/openipsl-kit/bin
cat > /opt/openipsl-kit/bin/g++-nopie <<'EOF'
#!/bin/sh
# g++ that links executables without PIE (OpenIPSL Linux verification kit, provision/30_systemmodeler.sh).
# Compile-only (-c, -S, -E) and shared-library (-shared) calls are passed through unchanged.
for a in "$@"; do
  case "$a" in -c|-S|-E|-shared) exec /usr/bin/g++ "$@" ;; esac
done
exec /usr/bin/g++ "$@" -no-pie
EOF
chmod 0755 /opt/openipsl-kit/bin/g++-nopie
log "installed /opt/openipsl-kit/bin/g++-nopie (non-PIE link wrapper for System Modeler)"

snapshot_packages 30
stamp 30_systemmodeler
log "done"
