#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

app_url="${SCIDOC_APP_URL:-http://localhost:3000}"
voiceover_starter="/System/Library/CoreServices/VoiceOver.app/Contents/MacOS/VoiceOverStarter"
mode="${1:-document}"

if [[ "$(uname -s)" != "Darwin" ]] || [[ ! -x "$voiceover_starter" ]]; then
  echo "This command requires macOS VoiceOver."
  exit 1
fi

if ! curl --silent --fail --max-time 3 "$app_url/api/documents" >/dev/null; then
  echo "The application is not running. Start it with 'make share', then run 'make voiceover' in another Terminal window."
  exit 1
fi

selection="$(
  SCIDOC_VOICEOVER_URL="$app_url" SCIDOC_VOICEOVER_MODE="$mode" .venv/bin/python <<'PY'
import json
import os
import urllib.request

base_url = os.environ["SCIDOC_VOICEOVER_URL"].rstrip("/")
mode = os.environ["SCIDOC_VOICEOVER_MODE"]
with urllib.request.urlopen(f"{base_url}/api/documents", timeout=5) as response:
    documents = json.load(response)

for document in documents:
    if document["status"] != "completed":
        continue
    if mode != "math":
        print(document["id"])
        break
    try:
        with urllib.request.urlopen(
            f"{base_url}/api/documents/{document['id']}/sdr", timeout=5
        ) as response:
            sdr = json.load(response)
    except (OSError, ValueError):
        continue
    for page in sdr["pages"]:
        for element in page["elements"]:
            content = element["content"]
            has_math = element["type"] in {"equation", "chemical_equation"}
            has_speech = any(
                content.get(field)
                for field in ("mathml", "alt_text", "unicode", "normalized_latex", "latex", "text")
            )
            if has_math and has_speech:
                print(f"{document['id']}\t{element['id']}")
                raise SystemExit
else:
    print("")
PY
)"

IFS=$'\t' read -r document_id equation_id <<< "$selection"

if [[ -z "${document_id:-}" ]]; then
  if [[ "$mode" == "math" ]]; then
    echo "No converted equation with readable content is available. Process a mathematical PDF first, then try again."
  else
    echo "No completed document is available. Process a PDF first, then run this command again."
  fi
  exit 1
fi

accessible_url="$app_url/api/documents/$document_id/exports/html"
if [[ -n "${equation_id:-}" ]]; then
  accessible_url="$accessible_url#$equation_id"
  echo "Opening a converted equation in the accessible HTML export…"
else
  echo "Opening the accessible HTML export in Safari…"
fi
open -a Safari "$accessible_url"
sleep 3

if ! pgrep -x VoiceOver >/dev/null; then
  echo "Starting VoiceOver…"
  "$voiceover_starter"
  sleep 4
fi

osascript \
  -e 'tell application "Safari" to activate' \
  -e 'delay 1' \
  -e 'tell application "System Events" to keystroke "a" using {control down, option down}'

if [[ "$mode" == "math" ]]; then
  echo "VoiceOver is reading from the converted equation. Press Control to pause, or Command-F5 to turn VoiceOver off."
else
  echo "VoiceOver is reading the document. Press Control to pause, or Command-F5 to turn VoiceOver off."
fi
