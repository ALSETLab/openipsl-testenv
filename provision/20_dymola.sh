#!/usr/bin/env bash
# Step 20 (root): Dymola for Linux from the vendor zip.
# - the shared libraries the Dymola RPM declares that a minimal Ubuntu lacks (Qt 6 xcb platform, NSS, GL, ...),
#   from the RPM's own requirement list; Dymola's installation guide says the libxcb libraries are no longer bundled;
# - the main RPM converted to .deb with alien, which the installation guide names for Debian/Ubuntu; the
#   converted package keeps the RPM's post-install script (start scripts in /usr/local/bin);
# - the FlexNet licence file in $DYMOLA_DIR/insert, where Dymola looks without DYMOLAPATH;
# - a Python virtual environment with the Dymola Python interface wheel shipped in the installation.
. "$(dirname "$0")/lib.sh"
need_root
header
need_var DYMOLA_ZIP DYMOLA_RPM DYMOLA_DIR DYMOLA_LICENSE_HOST DYMOLA_LICENSE_PORT

log "apt: alien, rpm, and the libraries the Dymola RPM requires"
apt-get update
apt_install alien rpm cpio fakeroot \
  libxcb1 libxcb-cursor0 libxcb-dri3-0 libxcb-glx0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-randr0 libxcb-render0 libxcb-render-util0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-util1 \
  libxcb-xfixes0 libxcb-xkb1 libx11-6 libx11-xcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxi6 \
  libxrandr2 libxrender1 libxtst6 libxkbcommon0 libxkbcommon-x11-0 libxkbfile1 libsm6 libice6 \
  libegl1 libgl1 libgles2 libglu1-mesa libopengl0 libglx0 \
  libnss3 libnspr4 libdbus-1-3 libfontconfig1 libfreetype6 libglib2.0-0t64 \
  libwebp7 libwebpmux3 libvorbis0a libvorbisenc2 libbz2-1.0 liblzma5 libzstd1 zlib1g libexpat1 libatomic1

if [ -x "$DYMOLA_DIR/bin64/dymola" ]; then
  log "Dymola is already installed in $DYMOLA_DIR"
else
  [ -f "$DYMOLA_ZIP" ] || die "DYMOLA_ZIP not found: $DYMOLA_ZIP"
  w="$WORK_DIR/dymola"
  mkdir -p "$w"
  cd "$w"
  if ! ls "$w"/dymola_*_amd64.deb >/dev/null 2>&1; then
    log "extract $DYMOLA_RPM from $DYMOLA_ZIP"
    unzip -o -j "$DYMOLA_ZIP" "*/linux_x86_64/$DYMOLA_RPM" -d "$w"
    log "convert with alien (several minutes for the 0.5 GB RPM)"
    alien --to-deb --scripts --keep-version "$DYMOLA_RPM"
    rm -f "$w/$DYMOLA_RPM"
  fi
  deb="$(ls -1 "$w"/dymola_*_amd64.deb | head -n1)"
  log "install $deb"
  dpkg -i "$deb"
fi
[ -x "$DYMOLA_DIR/bin64/dymola" ] || die "no $DYMOLA_DIR/bin64/dymola after the install"

lic="$DYMOLA_DIR/insert/dymola.lic"
log "licence file $lic: FlexNet server $DYMOLA_LICENSE_HOST port $DYMOLA_LICENSE_PORT"
printf 'SERVER %s ANY %s\nVENDOR dynasim\nUSE_SERVER\n' "$DYMOLA_LICENSE_HOST" "$DYMOLA_LICENSE_PORT" > "$lic"
chmod 0644 "$lic"

venv=/opt/openipsl-kit/venv-dymola
whl="$(ls -1 "$DYMOLA_DIR"/Modelica/Library/python_interface/dymola-*.whl 2>/dev/null | head -n1 || true)"
if [ -n "$whl" ]; then
  if [ ! -x "$venv/bin/python" ]; then
    log "Python environment $venv (system numpy/scipy visible) with $(basename "$whl")"
    mkdir -p /opt/openipsl-kit
    python3 -m venv --system-site-packages "$venv"
  fi
  "$venv/bin/pip" install --no-index --no-deps --force-reinstall "$whl"
else
  log "WARNING: no dymola-*.whl under $DYMOLA_DIR/Modelica/Library/python_interface; Python interface not installed"
fi

log "installed: $(dpkg-query -W -f='${Package} ${Version}' dymola 2>/dev/null || echo 'dymola (not in dpkg)')"
snapshot_packages 20
stamp 20_dymola
log "done"
