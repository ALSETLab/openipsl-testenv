#!/usr/bin/env bash
# make_pkg.sh: the package under test, a git archive of the checkout's HEAD, with the commit in <dest>/COMMIT, as the
# x64 and macOS records used.
# - HEAD tracks Resources/Library/aarch64-linux (OpenIPSL #433 from 43f6efd7 on): the archive holds the shipped
#   libraries; the script stops if the working tree's copies differ from them (a rebuild that is not bit-identical),
#   so that the runs never test rebuilt libraries in place of the shipped ones.
# - HEAD does not (the record run on b05fa044 with the kit's patches): the installed, untracked folder is copied in.
#   bash make_pkg.sh <checkout> <dest dir>      e.g. bash make_pkg.sh ~/arm-verify/OpenIPSL ~/arm-verify/pkg/record
set -euo pipefail
SRC="$(cd "${1:?usage}" && pwd)"; DEST="${2:?usage}"
LIB=OpenIPSL/Resources/Library/aarch64-linux
if [ -n "$(git -C "$SRC" ls-tree --name-only HEAD "$LIB/")" ]; then
  if ! git -C "$SRC" diff --quiet HEAD -- "$LIB"; then
    git -C "$SRC" diff --stat HEAD -- "$LIB" >&2
    echo "make_pkg.sh: $LIB in the working tree differs from the shipped libraries of HEAD; stopping." >&2
    echo "Restore them (git -C $SRC checkout -- $LIB) to test the shipped files." >&2
    exit 1
  fi
  SOURCE="shipped in HEAD"
else
  SOURCE="installed, untracked"
fi
rm -rf "$DEST"; mkdir -p "$DEST"
git -C "$SRC" archive --format=tar HEAD OpenIPSL | tar -x -C "$DEST"
[ "$SOURCE" = "shipped in HEAD" ] || cp -a "$SRC/$LIB" "$DEST/OpenIPSL/Resources/Library/"
BRANCH=$(git -C "$SRC" symbolic-ref --short -q HEAD || echo "none, detached")
git -C "$SRC" log -1 --format="%H (%s; branch $BRANCH; aarch64-linux libraries $SOURCE)" > "$DEST/COMMIT"
cat "$DEST/COMMIT"; ls -la "$DEST/OpenIPSL/Resources/Library" "$DEST/$LIB"
