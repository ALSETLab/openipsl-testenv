#!/usr/bin/env bash
# Common helpers of the provisioning steps. Every step sources this file; it is not run on its own.
# A step is called as:  bash <kit>/provision/NN_name.sh [<path of site.env>]
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[1]}")/.." && pwd)"
SITE_ENV="${1:-$KIT_DIR/site.env}"
if [ ! -f "$SITE_ENV" ]; then
  echo "site.env not found: $SITE_ENV (copy site.env.example to site.env and edit it)" >&2
  exit 2
fi
# shellcheck source=/dev/null
. "$SITE_ENV"
KIT_VERSION="$(tr -d '[:space:]' < "$KIT_DIR/VERSION" 2>/dev/null || echo unknown)"

STATE_DIR=/var/lib/openipsl-kit   # stamps of finished steps and package snapshots
WORK_DIR=/var/tmp/openipsl-kit    # unpacked installers (ext4, not the Windows drive)

log()  { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die()  { log "ERROR: $*"; exit 1; }
need_root() { [ "$(id -u)" -eq 0 ] || die "run this step as root: wsl -d <distro> -u root -- bash $0 <site.env>"; }
need_user() { [ "$(id -u)" -ne 0 ] || die "run this step as the normal user (${LINUX_USER:-?}), not as root"; }
need_var() { local v; for v in "$@"; do [ -n "${!v:-}" ] || die "$v is not set in $SITE_ENV"; done; }
apt_install() { DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"; }
stamp() { mkdir -p "$STATE_DIR"; printf '%s %s\n' "$KIT_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_DIR/$1.done"; }
snapshot_packages() { mkdir -p "$STATE_DIR"; dpkg-query -W -f='${Package}\t${Version}\n' > "$STATE_DIR/packages_after_$1.tsv"; }
header() {
  local os; os="$(. /etc/os-release && echo "$PRETTY_NAME")"
  log "OpenIPSL Linux verification kit $KIT_VERSION, step $(basename "${BASH_SOURCE[1]}"), user $(id -un)"
  log "system: $os, kernel $(uname -r), glibc $(ldd --version | head -n1 | awk '{print $NF}')"
}
