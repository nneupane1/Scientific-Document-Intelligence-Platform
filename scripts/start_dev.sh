#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

runtime_dir="$repo_root/data/temp"
pid_file="$runtime_dir/scidoc-dev.pid"
mode_file="$runtime_dir/scidoc-dev.mode"
url_file="$runtime_dir/scidoc-dev.url"

if [[ ! -x .venv/bin/uvicorn ]] || [[ ! -d node_modules ]]; then
  echo "Dependencies are missing. Run 'make setup' once, then run 'make launch'."
  exit 1
fi

port_is_listening() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
  elif command -v nc >/dev/null 2>&1; then
    nc -z 127.0.0.1 "$port" >/dev/null 2>&1
  else
    return 1
  fi
}

detect_lan_address() {
  local detected_interface=""
  local detected_address=""

  if command -v ipconfig >/dev/null 2>&1; then
    detected_interface="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
    if [[ -n "$detected_interface" ]]; then
      detected_address="$(ipconfig getifaddr "$detected_interface" 2>/dev/null || true)"
    fi
    if [[ -z "$detected_address" ]]; then
      for detected_interface in en0 en1 en2; do
        detected_address="$(ipconfig getifaddr "$detected_interface" 2>/dev/null || true)"
        [[ -n "$detected_address" ]] && break
      done
    fi
  elif command -v hostname >/dev/null 2>&1; then
    detected_address="$(hostname -I 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i !~ /^127\./) {print $i; exit}}')"
  fi

  if [[ -z "$detected_address" ]] && command -v ifconfig >/dev/null 2>&1; then
    detected_address="$(ifconfig 2>/dev/null | awk '/inet / && $2 !~ /^127\./ {print $2; exit}')"
  fi
  printf '%s' "$detected_address"
}

open_application() {
  local url="$1"
  if [[ "${SCIDOC_NO_BROWSER:-0}" == "1" ]]; then
    echo "Automatic browser opening is disabled for this run."
  elif command -v open >/dev/null 2>&1; then
    echo "Opening $url"
    open "$url"
  elif command -v xdg-open >/dev/null 2>&1; then
    echo "Opening $url"
    xdg-open "$url" >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then
    echo "Opening $url"
    cmd.exe /c start "" "$url"
  else
    echo "Open $url in your browser."
  fi
}

is_scidoc_healthy() {
  curl --silent --fail --max-time 2 http://127.0.0.1:8000/health 2>/dev/null \
    | grep --quiet '"status":"ok"' \
    && curl --silent --fail --max-time 2 http://127.0.0.1:3000 >/dev/null 2>&1
}

share_mode="${SCIDOC_SHARE:-0}"
requested_mode="local"
web_bind_host="127.0.0.1"
browser_host="localhost"

if [[ "$share_mode" == "1" ]]; then
  requested_mode="share"
  browser_host="${SCIDOC_LAN_HOST:-$(detect_lan_address)}"
  if [[ -z "$browser_host" ]] || [[ ! "$browser_host" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "Could not determine a safe LAN address. Set SCIDOC_LAN_HOST to this computer's LAN IPv4 address."
    exit 1
  fi
  web_bind_host="0.0.0.0"
fi

app_url="http://${browser_host}:3000"
api_ready_url="http://127.0.0.1:8000/health"
web_ready_url="http://127.0.0.1:3000"

web_is_shared() {
  curl --noproxy '*' --silent --fail --max-time 2 "$app_url" >/dev/null 2>&1
}

managed_pid=""
if [[ -f "$pid_file" ]]; then
  managed_pid="$(sed -n '1p' "$pid_file" 2>/dev/null || true)"
fi

if port_is_listening 3000 || port_is_listening 8000; then
  if is_scidoc_healthy; then
    if [[ "$requested_mode" == "share" ]] && ! web_is_shared; then
      if [[ "$managed_pid" =~ ^[0-9]+$ ]] && kill -0 "$managed_pid" 2>/dev/null; then
        echo "Switching the managed application from private to LAN sharing mode…"
        kill -TERM "$managed_pid"
        for _ in $(seq 1 40); do
          if ! port_is_listening 3000 && ! port_is_listening 8000; then
            break
          fi
          sleep 0.25
        done
        if port_is_listening 3000 || port_is_listening 8000; then
          echo "The previous managed application did not stop cleanly. Run 'make stop' and try again."
          exit 1
        fi
      else
        echo "A private application is already running outside managed launch mode. Stop its terminal with Ctrl+C, then run 'make share'."
        exit 1
      fi
    else
      echo "Scientific Document Intelligence is already running."
      if [[ "$requested_mode" == "share" ]]; then
        echo "LAN sharing is active: $app_url"
      else
        echo "Local application: $app_url"
      fi
      open_application "$app_url"
      exit 0
    fi
  else
    echo "Port 3000 or 8000 is occupied by another application:"
    if command -v lsof >/dev/null 2>&1; then
      lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null || true
      lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null || true
    fi
    echo "Stop the listed process or configure different ports before trying again."
    exit 1
  fi
fi

.venv/bin/uvicorn scidoc_api.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
SCIDOC_ALLOWED_DEV_ORIGIN="$browser_host" npm run dev --workspace=@scidoc/web -- --hostname "$web_bind_host" --port 3000 &
web_pid=$!
stopping=false

cleanup() {
  if [[ "$stopping" == true ]]; then
    return
  fi
  stopping=true
  echo
  echo "Stopping Scientific Document Intelligence…"
  kill "$api_pid" "$web_pid" 2>/dev/null || true
  wait "$api_pid" "$web_pid" 2>/dev/null || true
  if [[ -f "$pid_file" ]] && [[ "$(sed -n '1p' "$pid_file" 2>/dev/null || true)" == "$$" ]]; then
    rm -f "$pid_file" "$mode_file" "$url_file"
  fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM

mkdir -p "$runtime_dir"
printf '%s\n' "$$" > "$pid_file"
printf '%s\n' "$requested_mode" > "$mode_file"
printf '%s\n' "$app_url" > "$url_file"

wait_for_service() {
  local url="$1"
  local name="$2"
  local pid="$3"
  local attempt
  for attempt in $(seq 1 90); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name stopped before it became ready."
      return 1
    fi
    if curl --silent --fail --max-time 2 "$url" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "$name did not become ready within 90 seconds."
  return 1
}

echo "Starting the API and animated web interface…"
wait_for_service "$api_ready_url" "API" "$api_pid"
wait_for_service "$web_ready_url" "Web interface" "$web_pid"

if [[ "$share_mode" == "1" ]]; then
  echo
  echo "LAN sharing is active: $app_url"
  echo "Only the web port is shared; the API remains loopback-only behind the web proxy."
  echo "Anyone on this network who can reach this address can use the application and access uploaded documents."
fi

open_application "$app_url"
echo "The application is ready. Press Ctrl+C here or run 'make stop' from another terminal."
while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
echo "A service stopped unexpectedly; shutting down the remaining service."
exit 1
