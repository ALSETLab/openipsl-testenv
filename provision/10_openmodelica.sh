#!/usr/bin/env bash
# Step 10 (root): OpenModelica from build.openmodelica.org, by OM_CHANNEL:
#   release (default): OM_VERSION from the archived release repository. That repository holds exactly one
#                      release, so the version stays fixed when the main /apt channel moves on.
#   nightly:           the newest development build of the main /apt repository, component "nightly"
#                      (1.28.0~dev-NNNN-g<commit>). No version is pinned; the one installed is logged and
#                      written to /var/lib/openipsl-kit/omc_version. For a throwaway distro, not for the
#                      verification environment.
# omc is the command-line compiler (no graphical clients); omlibrary carries cached Modelica Standard Library versions.
. "$(dirname "$0")/lib.sh"
need_root
header

codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
key=/usr/share/keyrings/openmodelica-keyring.gpg
list=/etc/apt/sources.list.d/openmodelica.list
channel="${OM_CHANNEL:-release}"
case "$channel" in
  release)
    need_var OM_VERSION
    line="deb [arch=amd64 signed-by=$key] https://build.openmodelica.org/omc/builds/linux/releases/${OM_VERSION}/ $codename release" ;;
  nightly)
    line="deb [arch=amd64 signed-by=$key] https://build.openmodelica.org/apt $codename nightly" ;;
  *) die "OM_CHANNEL is '$channel'; it must be release or nightly" ;;
esac

if [ ! -s "$key" ]; then
  log "fetch the OpenModelica signing key"
  curl -fsSL https://build.openmodelica.org/apt/openmodelica.asc | gpg --dearmor -o "$key"
fi
log "channel $channel, repository: $line"
echo "$line" > "$list"
apt-get update
apt_install omc omlibrary

got="$(dpkg-query -W -f='${Version}' omc)"
log "omc package $got; omlibrary package $(dpkg-query -W -f='${Version}' omlibrary); omc --version: $(omc --version)"
case "$channel" in
  release)
    case "$got" in
      "$OM_VERSION"-*) ;;
      *) die "omc $got is installed, OM_VERSION is $OM_VERSION" ;;
    esac ;;
  nightly)
    mkdir -p "$STATE_DIR"
    printf '%s %s\n' "$got" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$STATE_DIR/omc_version"
    log "nightly build recorded in $STATE_DIR/omc_version; upgrade later with: apt-get update && apt-get install --only-upgrade omc omlibrary" ;;
esac
snapshot_packages 10
stamp 10_openmodelica
log "done"
