#!/usr/bin/env bash
# 2026-11-01: provisioning of Luigi's Raspberry Pi 400 (Raspberry Pi OS 64-bit, Debian 13 trixie, imaged 2026-11-01
# from 2026-10-06-raspios-trixie-arm64.img.xz) for the native aarch64-linux verification of the IEEE/CIGRE DLL
# package (OpenIPSL #433). Run as the Pi login user; sudo asks for the password once (kept alive below).
# Every step is idempotent. Run 2026-11-01 01:0x: steps 0-3 in one pass, 4-6 in a second pass (the first pass stopped on a
# wrong path check after installing omc; corrected below). Changes from the 2026-10-31 draft: the trixie arm64 index of build.openmodelica.org
# has no omlib-modelica-4.0.0, the libraries come as the single package "omlibrary" (1.27.2-1); sudo keepalive.
set -euo pipefail

echo "== 0. sudo ticket (type the password once)"
sudo -v
( while kill -0 "$$" 2>/dev/null; do sudo -n true 2>/dev/null; sleep 50; done ) &
KEEPALIVE=$!
trap 'kill $KEEPALIVE 2>/dev/null || true' EXIT

echo "== 1. architecture and OS"
uname -m; uname -r                      # must print aarch64
. /etc/os-release; echo "$PRETTY_NAME ($VERSION_CODENAME)"
[ "$(uname -m)" = aarch64 ] || { echo "not a 64-bit OS: reimage first"; exit 1; }
tr -d '\0' < /proc/device-tree/model; echo

echo "== 2. build tools"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git cmake ninja-build build-essential python3 python3-numpy curl ca-certificates gnupg
gcc --version | head -n 1; cmake --version | head -n 1; ninja --version; python3 --version

echo "== 3. OpenModelica (official arm64 apt repository, stable channel)"
# https://openmodelica.org/download/download-linux ; trixie/stable/binary-arm64 checked 2026-11-01 (omc 1.27.2-1)
sudo install -d /usr/share/keyrings
curl -fsSL https://build.openmodelica.org/apt/openmodelica.asc | sudo gpg --dearmor --yes -o /usr/share/keyrings/openmodelica-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/openmodelica-keyring.gpg] https://build.openmodelica.org/apt $VERSION_CODENAME stable" \
  | sudo tee /etc/apt/sources.list.d/openmodelica.list
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y omc omlibrary
omc --version                           # expected 1.27.2
dpkg-query -W -f='${Package} ${Version}\n' omc omc-common libomc libomcsimulation omlibrary
# omlibrary ships only a zip cache in /usr/share/omlibrary/cache; omc unpacks it into ~/.openmodelica/libraries
# (Modelica 3.2.3 / 4.0.0 / 4.1.0 +maint.om, Complex, ModelicaServices, ModelicaReference, ObsoleteModelica4)
# the first time a library is loaded. Trigger that now and prove the MSL loads:
ls -la /usr/share/omlibrary/cache/
printf 'getModelicaPath();
loadModel(Modelica);
getErrorString();
' > /tmp/loadmsl.mos && omc /tmp/loadmsl.mos | tail -n 3
ls ~/.openmodelica/libraries

echo "== 4. Claude Code (native installer, linux-arm64)"
curl -fsSL https://claude.ai/install.sh | bash
~/.local/bin/claude --version
grep -q '.local/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

echo "== 5. Wolfram on the Pi (optional; NOT installed by this script)"
# sudo apt-get install -y wolfram-engine   # only on Luigi's word; not needed for the DLL verification
command -v wolframscript && wolframscript --version || echo "no wolframscript on this image"
command -v wolfram && wolfram --version || echo "no wolfram kernel on this image"
apt-cache policy wolfram-engine | head -n 3 || true

echo "== 6. memory and storage (the Pi 400 has 4 GB RAM; run the cases serially)"
free -h; df -h / /boot/firmware
echo "== provisioning finished $(date -Is)"
