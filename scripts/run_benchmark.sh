#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
./scripts/extract_sample_corpus.sh
exec .venv/bin/scidoc benchmark benchmark/datasets/source-documents/input
