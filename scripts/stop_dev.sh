#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pid_file="$repo_root/data/temp/scidoc-dev.pid"

if [[ ! -f "$pid_file" ]]; then
  echo "No managed Scientific Document Intelligence session is running."
  exit 0
fi

managed_pid="$(sed -n '1p' "$pid_file")"
if [[ ! "$managed_pid" =~ ^[0-9]+$ ]]; then
  echo "Ignoring an invalid runtime PID file."
  rm -f "$pid_file"
  exit 1
fi

if ! kill -0 "$managed_pid" 2>/dev/null; then
  echo "Removing stale runtime state; the application is already stopped."
  rm -f "$repo_root/data/temp/scidoc-dev.pid" "$repo_root/data/temp/scidoc-dev.mode" "$repo_root/data/temp/scidoc-dev.url"
  exit 0
fi

managed_command="$(ps -p "$managed_pid" -o command= 2>/dev/null || true)"
if [[ "$managed_command" != *"scripts/start_dev.sh"* ]]; then
  echo "The recorded PID no longer belongs to this application; refusing to stop it."
  exit 1
fi

echo "Stopping Scientific Document Intelligence…"
kill -TERM "$managed_pid"
for _ in $(seq 1 40); do
  if ! kill -0 "$managed_pid" 2>/dev/null; then
    echo "Stopped."
    exit 0
  fi
  sleep 0.25
done

echo "The application did not stop within 10 seconds."
exit 1
