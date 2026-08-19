#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e '.[dev,ocr]'
npm install
./scripts/extract_sample_corpus.sh
echo "Setup complete. Copy .env.example to .env before running infrastructure-backed services."
