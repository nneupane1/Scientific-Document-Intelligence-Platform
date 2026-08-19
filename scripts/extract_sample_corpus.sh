#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
archive="$repo_root/source-documents.zip"
destination="$repo_root/benchmark/datasets/source-documents"

if [[ ! -f "$archive" ]]; then
  echo "Missing canonical corpus archive: $archive" >&2
  exit 1
fi

mkdir -p "$destination"
unzip -o -q "$archive" -d "$destination"
echo "Extracted canonical sample corpus to $destination"
