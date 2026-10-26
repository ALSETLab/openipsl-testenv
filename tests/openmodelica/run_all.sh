#!/usr/bin/env bash
# OpenModelica verification of the IEEE_CIGRE tests on Linux (normal user, inside the distro).
# Runs every step of omc_verify.py in order, writes the build tree and the record into the distro's ext4,
# then copies the record (not the raw .mat files) to <record dest> with cp.
#
# Usage: bash run_all.sh <package dir .../OpenIPSL> <record dest> [<work dir>]
#   <package dir>  the exported package, e.g. ~/cigre_verify/pkg/<commit>/OpenIPSL (tests/export_package.sh)
#   <record dest>  where the record goes, e.g. /mnt/c/records/linux/openmodelica ("-" = do not copy)
#   <work dir>     build tree and staged record (default ~/cigre_verify/openmodelica); never a /mnt/ path
# Environment: STEPS (default "env checks extras run timing binding compare table"), OMC_TIMING_REPS (default 3),
#              WIN_RECORD / WIN_BUILD (the Windows round-2 record and build tree for "compare", read only; default
#              $WINDOWS_RECORD_ROOT/openmodelica and $WINDOWS_RAW_ROOT/openmodelica from the kit's site.env, or
#              KIT_SITE=<file>; without them "compare" is skipped).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
KIT_SITE="${KIT_SITE:-$HERE/../../site.env}"
# shellcheck source=/dev/null
[ -f "$KIT_SITE" ] && . "$KIT_SITE"
WIN_RECORD="${WIN_RECORD:-${WINDOWS_RECORD_ROOT:+$WINDOWS_RECORD_ROOT/openmodelica}}"
WIN_BUILD="${WIN_BUILD:-${WINDOWS_RAW_ROOT:+$WINDOWS_RAW_ROOT/openmodelica}}"
PKG="$(cd "${1:?usage: run_all.sh <package dir> <record dest> [<work dir>]}" && pwd)"
DEST="${2:?usage: run_all.sh <package dir> <record dest> [<work dir>]}"
WORK="${3:-$HOME/cigre_verify/openmodelica}"
case "$WORK" in /mnt/*) echo "work dir must be on the distro's ext4, not $WORK" >&2; exit 2 ;; esac
if [ -z "${STEPS:-}" ]; then
  STEPS="env checks extras run timing binding compare table"
  # a full run starts from an empty staged record, so the record holds this run only (the build tree is reused)
  rm -rf "$WORK/record"
fi
PY=/usr/bin/python3
ARGS=(--pkg "$PKG" --build "$WORK/build" --out "$WORK/record" --reps "${OMC_TIMING_REPS:-3}")
[ -n "${WIN_RECORD:-}" ] && ARGS+=(--win-record "$WIN_RECORD")
[ -n "${WIN_BUILD:-}" ] && ARGS+=(--win-build "$WIN_BUILD")
mkdir -p "$WORK/record/logs"
LOG="$WORK/record/logs/run_all.log"
echo "== run_all.sh $(date -Is) pkg=$PKG work=$WORK dest=$DEST steps=[$STEPS]" | tee -a "$LOG"
rc=0
for s in $STEPS; do
  case "$s" in
    run|timing) set -- "$s" all ;;
    *) set -- "$s" ;;
  esac
  echo "== step $s $(date -Is)" | tee -a "$LOG"
  "$PY" -I "$HERE/omc_verify.py" "${ARGS[@]}" "$@" 2>&1 | tee -a "$LOG"
  st=${PIPESTATUS[0]}
  echo "== step $s exit $st $(date -Is)" | tee -a "$LOG"
  [ "$st" -ne 0 ] && rc=1
done
if [ "$DEST" != "-" ]; then
  mkdir -p "$DEST"
  # the record only: CSV, metrics JSON, raw-points files, logs/ (run.mos and log.txt of every run); no .mat
  cp -r "$WORK/record/." "$DEST/"
  echo "== copied $WORK/record to $DEST ($(du -sh "$WORK/record" | cut -f1))" | tee -a "$LOG"
  cp "$LOG" "$DEST/logs/run_all.log"
fi
exit $rc
