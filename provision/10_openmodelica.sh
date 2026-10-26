#!/usr/bin/env bash
# Step 10 (root): OpenModelica OM_VERSION from the archived release repository of build.openmodelica.org.
# That repository holds exactly one release, so the version stays fixed when the main /apt channel moves on.
# omc is the command-line compiler (no graphical clients); omlibrary carries cached Modelica Standard Library versions.
. "$(dirname "$0")/lib.sh"
need_root
header
need_var OM_VERSION

codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
key=/usr/share/keyrings/openmodelica-keyring.gpg
list=/etc/apt/sources.list.d/openmodelica.list
line="deb [arch=amd64 signed-by=$key] https://build.openmodelica.org/omc/builds/linux/releases/${OM_VERSION}/ $codename release"

if [ ! -s "$key" ]; then
  log "fetch the OpenModelica signing key"
  curl -fsSL https://build.openmodelica.org/apt/openmodelica.asc | gpg --dearmor -o "$key"
fi
log "repository: $line"
echo "$line" > "$list"
apt-get update
apt_install omc omlibrary

got="$(dpkg-query -W -f='${Version}' omc)"
log "omc package $got; omc --version: $(omc --version)"
case "$got" in
  "$OM_VERSION"-*) ;;
  *) die "omc $got is installed, OM_VERSION is $OM_VERSION" ;;
esac
snapshot_packages 10
stamp 10_openmodelica
log "done"
