#!/usr/bin/env bash
# Timing diagnostics for Dymola-for-Linux runs (normal user; Dymola itself is not started, so no licence is used):
# runs a generated dymosim again, outside Dymola, in a copy of its run folder, and compares dymosim's own
# "CPU-time for integration" (dslog.txt) with the process times of /usr/bin/time (elapsed, user, system) and the
# number of threads of the process; then repeats the run pinned to single CPUs with taskset, to show how much
# the time of the same executable varies on this machine (WSL2 VM on a hybrid CPU: vCPUs are scheduled by the
# Windows host on performance or efficient cores).
# Usage: bash diag_timing.sh <run folder> <output file> [repeats] [cpus...]
#   e.g. bash diag_timing.sh ~/cigre_verify/dymola/runs/GFM_EMTPFull__euler ~/cigre_verify/dymola/record/logs/timing_GFM_EMTPFull.txt 3 0 8 16 23
set -uo pipefail
RUN="${1:?usage: diag_timing.sh <run folder> <output file> [repeats] [cpus...]}"
OUTF="${2:?output file}"
N="${3:-3}"
shift 3 2>/dev/null || shift $#
CPUS="${*:-}"
T="$(mktemp -d "${TMPDIR:-/tmp}/dymosim_timing.XXXXXX")"
cp "$RUN/dymosim" "$RUN/dsin.txt" "$T/"
{
  echo "# timing of $RUN/dymosim outside Dymola, $(date -Is)"
  echo "# $(lscpu | grep 'Model name' | sed 's/  */ /g'); $(nproc) vCPUs; load: $(cut -d' ' -f1-3 /proc/loadavg)"
  echo "# dymosim reads dsin.txt and writes dsres.mat in $T (deleted afterwards)"
  one() {
    local label="$1"; shift
    ( cd "$T" && rm -f dsres.mat dslog.txt
      "$@" /usr/bin/time -f 'elapsed %e s, user %U s, system %S s, max RSS %M kB, voluntary cs %w, involuntary cs %c' \
        -o time.txt ./dymosim > dymosim.out 2>&1 &
      pid=$!; sleep 0.5
      thr=$(for p in $(pgrep -P "$pid" 2>/dev/null; pgrep -f "$T/dymosim|\./dymosim" 2>/dev/null); do
              awk '/^Threads/ {print $2}' "/proc/$p/status" 2>/dev/null; done | sort -n | tail -n1)
      wait "$pid"
      cpu=$(grep -E 'CPU-time for integration' dslog.txt | sed 's/.*: *//')
      echo "$label | $(cat time.txt) | dslog CPU-time for integration: $cpu | threads seen: ${thr:-?}" )
  }
  for i in $(seq 1 "$N"); do one "unpinned run $i"; done
  for c in $CPUS; do one "taskset -c $c" taskset -c "$c"; done
  echo "# system calls of one more run (strace -c -f): where the system time goes"
  ( cd "$T" && rm -f dsres.mat dslog.txt && strace -c -f -o syscalls.txt ./dymosim > dymosim.out 2>&1
    head -n 14 syscalls.txt
    ls -l dsres.mat | awk '{print "# dsres.mat " $5 " bytes"}' )
} | tee "$OUTF"
rm -rf "$T"
