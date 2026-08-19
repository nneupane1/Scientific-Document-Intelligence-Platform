#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
model_dir="${SCIDOC_NARRATION_MODEL_DIR:-${project_root}/data/models/narration}"
model_path="${model_dir}/kokoro-v1.0.onnx"
voices_path="${model_dir}/voices-v1.0.bin"
release_base="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

mkdir -p "${model_dir}"

download() {
  local url="$1"
  local destination="$2"
  local temporary="${destination}.part"
  if [[ -s "${destination}" ]]; then
    echo "Already installed: ${destination}"
    return
  fi
  rm -f "${temporary}"
  curl --fail --location --retry 3 --progress-bar --output "${temporary}" "${url}"
  mv "${temporary}" "${destination}"
}

download "${release_base}/kokoro-v1.0.onnx" "${model_path}"
download "${release_base}/voices-v1.0.bin" "${voices_path}"

echo "Offline Kokoro narration is ready in ${model_dir}"
