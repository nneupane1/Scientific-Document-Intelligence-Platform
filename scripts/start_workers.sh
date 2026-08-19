#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
exec .venv/bin/dramatiq scidoc_jobs.tasks --processes 1 --threads "${SCIDOC_WORKER_THREADS:-4}"
