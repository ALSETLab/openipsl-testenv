#!/bin/sh
# Runs a 32-bit ARM program through the unpacked armhf loader (no system armhf libc is installed).
exec /home/<pi-user>/arm-verify/build/armhf_sysroot/root/usr/lib/ld-linux-armhf.so.3 --library-path "${ARMHF_EXTRA_LIBPATH:+$ARMHF_EXTRA_LIBPATH:}/home/<pi-user>/arm-verify/build/armhf_sysroot/root/usr/lib/arm-linux-gnueabihf" "$@"
