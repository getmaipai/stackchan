#!/usr/bin/env bash
# Intent: run a long command (firmware build, flash, soak, gate) with its full output in a log file and
# print only a short verdict, so no session ever pastes a build log into its context.
# Usage: run-bg.sh NAME -- command args...
# Writes: .runs/NAME.log (full output), .runs/NAME.status (running|ok|fail + seconds). Prints 3 lines max.
# Start it with the Bash tool's run_in_background so the session is notified and keeps working meanwhile.
set -u
NAME="$1"; shift; [ "${1:-}" = "--" ] && shift
mkdir -p .runs
LOG=".runs/$NAME.log"; ST=".runs/$NAME.status"
echo "running $(date +%s)" > "$ST"
start=$(date +%s)
"$@" > "$LOG" 2>&1; rc=$?
secs=$(( $(date +%s) - start ))
if [ $rc -eq 0 ]; then echo "ok ${secs}s" > "$ST"; else echo "fail rc=$rc ${secs}s" > "$ST"; fi
echo "$NAME: $(cat "$ST")  (log: $LOG, $(wc -l < "$LOG" | tr -d ' ') lines)"
if [ $rc -ne 0 ]; then echo "last errors:"; grep -i -E 'error|fail|undefined|fatal' "$LOG" | tail -5 | cut -c1-200; fi
exit $rc
