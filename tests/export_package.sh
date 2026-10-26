#!/usr/bin/env bash
# Export one commit of the OpenIPSL repository into ~/cigre_verify/pkg/<commit>/OpenIPSL (normal user).
# The repository is only read (git archive); the package under test is this exported tree, with the
# shipped Resources/Library/linux64/*.so exactly as committed.
# Usage: bash tests/export_package.sh <commit> [<site.env>]
set -euo pipefail
KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
commit="${1:?usage: export_package.sh <commit> [<site.env>]}"
# shellcheck source=/dev/null
. "${2:-$KIT_DIR/site.env}"
git_ro() { git -c safe.directory="$OPENIPSL_REPO" -C "$OPENIPSL_REPO" "$@"; }

full="$(git_ro rev-parse --verify "$commit^{commit}")"
short="${full:0:8}"
dest="$HOME/cigre_verify/pkg/$short"
if [ -f "$dest/OpenIPSL/package.mo" ] && [ "$(cat "$dest/COMMIT" 2>/dev/null)" = "$full" ]; then
  echo "already exported: $dest/OpenIPSL"
else
  rm -rf "$dest"
  mkdir -p "$dest"
  git_ro archive --format=tar "$full" OpenIPSL | tar -x -C "$dest"
  echo "$full" > "$dest/COMMIT"
  echo "exported $full to $dest/OpenIPSL"
fi
( cd "$dest/OpenIPSL/Resources/Library/linux64" && sha256sum lib*.so ) | tee "$dest/linux64.sha256"
echo "$dest/OpenIPSL"
