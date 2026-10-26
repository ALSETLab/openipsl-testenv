#!/usr/bin/env bash
# Step 00 (root): WSL settings, the normal user, base packages for building and for the test scripts.
. "$(dirname "$0")/lib.sh"
need_root
header
need_var LINUX_USER

log "write /etc/wsl.conf (systemd, default user, file permissions on /mnt, no Windows PATH)"
cat > /etc/wsl.conf <<EOF
# Written by the OpenIPSL Linux verification kit (provision/00_base.sh).
[boot]
systemd=true

[user]
default=$LINUX_USER

[automount]
options = "metadata"

[interop]
appendWindowsPath = false
EOF

if id "$LINUX_USER" >/dev/null 2>&1; then
  log "user $LINUX_USER exists (uid $(id -u "$LINUX_USER"))"
else
  log "create user $LINUX_USER: no password and no sudo; root work goes through wsl -u root"
  useradd --create-home --shell /bin/bash --user-group "$LINUX_USER"
fi

log "apt: base packages"
apt-get update
apt_install ca-certificates curl gnupg git \
  build-essential cmake ninja-build pkg-config file binutils strace \
  python3 python3-venv python3-pip python3-numpy python3-scipy python3-matplotlib \
  zip unzip xz-utils less

snapshot_packages 00
stamp 00_base
log "done: restart the distro (wsl --terminate <distro>) so /etc/wsl.conf takes effect; New-VerifyDistro.ps1 does it"
