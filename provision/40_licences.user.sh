#!/usr/bin/env bash
# Step 40 (normal user): per-user licence settings.
# System Modeler reads its licence from ~/.systemmodeler/mathpass; a line "!<host>" names a MathLM network
# licence server (Wolfram support articles 12542 and "Global Aspects of Wolfram System Sessions").
# Dymola's licence file is system-wide ($DYMOLA_DIR/insert/dymola.lic, step 20), so nothing per user here.
. "$(dirname "$0")/lib.sh"
need_user
header
need_var WSM_LICENSE_SERVER

mkdir -p "$HOME/.systemmodeler"
mp="$HOME/.systemmodeler/mathpass"
if [ -f "$mp" ] && grep -qx "!$WSM_LICENSE_SERVER" "$mp"; then
  log "$mp already names $WSM_LICENSE_SERVER"
else
  [ -f "$mp" ] && cp "$mp" "$mp.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  printf '!%s\n' "$WSM_LICENSE_SERVER" > "$mp"
  log "wrote $mp: !$WSM_LICENSE_SERVER"
fi
log "done"
