#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
model_kind="${1:-ocr}"
mkdir -p "$repo_root/data/models/cache"
export XDG_CACHE_HOME="$repo_root/data/models/cache"

case "$model_kind" in
  ocr)
    "$repo_root/.venv/bin/pip" install -e "$repo_root[ocr]"
    echo "RapidOCR runtime installed. Its ONNX assets are cached under data/models/cache when supported."
    ;;
  paddle)
    "$repo_root/.venv/bin/pip" install -e "$repo_root[paddle]"
    echo "PaddleOCR installed; model weights download on first use into the configured cache."
    ;;
  formula)
    "$repo_root/.venv/bin/pip" install -e "$repo_root[math]"
    echo "pix2tex installed; model weights download on first use into data/models/cache."
    ;;
  *)
    echo "Usage: $0 [ocr|paddle|formula]" >&2
    exit 2
    ;;
esac
