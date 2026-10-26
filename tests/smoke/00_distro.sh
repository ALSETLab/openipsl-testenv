#!/usr/bin/env bash
# Smoke test 00 (normal user): the distro itself - user, systemd, WSLg display, Windows PATH kept out,
# DNS and TCP reachability of the licence servers named in site.env.
set -uo pipefail
KIT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=/dev/null
. "${1:-$KIT_DIR/site.env}"
ok=0; bad=0
check() { if eval "$2" >/dev/null 2>&1; then echo "PASS  $1"; ok=$((ok+1)); else echo "FAIL  $1"; bad=$((bad+1)); fi; }
tcp() { timeout 5 bash -c "</dev/tcp/$1/$2"; }
echo "user $(id -un) uid $(id -u); $(. /etc/os-release && echo "$PRETTY_NAME"); glibc $(ldd --version | head -n1 | awk '{print $NF}')"
check "not root" '[ "$(id -u)" -ne 0 ]'
check "user is LINUX_USER ($LINUX_USER)" '[ "$(id -un)" = "$LINUX_USER" ]'
check "systemd is PID 1" '[ "$(ps -p 1 -o comm=)" = systemd ]'
check "WSLg display (DISPLAY=${DISPLAY:-unset}, WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-unset})" '[ -n "${DISPLAY:-}" ] && [ -S /tmp/.X11-unix/X${DISPLAY#:} ]'
check "no Windows folders on PATH" '! echo "$PATH" | grep -q "/mnt/c/"'
check "OpenIPSL repository readable ($OPENIPSL_REPO)" '[ -d "$OPENIPSL_REPO/.git" ]'
check "Dymola licence server $DYMOLA_LICENSE_HOST:$DYMOLA_LICENSE_PORT" "tcp $DYMOLA_LICENSE_HOST $DYMOLA_LICENSE_PORT"
check "System Modeler licence server $WSM_LICENSE_SERVER:16286" "tcp $WSM_LICENSE_SERVER 16286"
echo "passed $ok, failed $bad"
[ "$bad" -eq 0 ]
