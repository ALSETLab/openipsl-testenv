#!/bin/bash
# make_sysroot.sh: unpack an armhf sysroot and lld 19 into <dir> without sudo (nothing is installed system-wide).
# Usage: bash make_sysroot.sh <dir>   (2026-11-01 used ~/arm-verify/build/armhf_sysroot; the toolchain files and
# run_armhf.sh next to this script carry that absolute path, so edit them for another <dir>)
set -euo pipefail
D=$(realpath -m "$1")
mkdir -p "$D/debs" "$D/root/usr/include/arm-linux-gnueabihf"
cd "$D/debs"
apt-get download libc6:armhf libc6-dev:armhf libgcc-14-dev:armhf libgcc-s1:armhf lld-19
for f in libc6_*.deb libc6-dev_*.deb libgcc-14-dev_*.deb libgcc-s1_*.deb; do dpkg-deb -x "$f" "$D/root"; done
dpkg-deb -x lld-19_*.deb "$D/lld"
ln -sfn usr/lib "$D/root/lib"
cp -a /usr/include/arm-linux-gnueabihf/asm "$D/root/usr/include/arm-linux-gnueabihf/"
cp -a /usr/include/linux /usr/include/asm-generic "$D/root/usr/include/"
