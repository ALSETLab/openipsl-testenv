#!/usr/bin/env bash
# make_pkg.sh: the package under test, a git archive of the checkout's HEAD plus the installed aarch64-linux libraries
# (the installed folder is untracked), with the commit in <dest>/COMMIT, as the x64 and macOS records used.
#   bash make_pkg.sh <checkout> <dest dir>      e.g. bash make_pkg.sh ~/arm-verify/OpenIPSL ~/arm-verify/pkg/record
set -euo pipefail
SRC="$(cd "${1:?usage}" && pwd)"; DEST="${2:?usage}"
rm -rf "$DEST"; mkdir -p "$DEST"
git -C "$SRC" archive --format=tar HEAD OpenIPSL | tar -x -C "$DEST"
cp -a "$SRC/OpenIPSL/Resources/Library/aarch64-linux" "$DEST/OpenIPSL/Resources/Library/"
git -C "$SRC" log -1 --format='%H (%s; branch arm-platform-folders on b05fa04440809291d61f13045f8586d186613f66)' > "$DEST/COMMIT"
cat "$DEST/COMMIT"; ls -la "$DEST/OpenIPSL/Resources/Library" "$DEST/OpenIPSL/Resources/Library/aarch64-linux"
