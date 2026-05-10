#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

run_or_die() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

run_or_die "npm"
run_or_die "livekit-server"
run_or_die "ngrok"
run_or_die "cloudflared"

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

pids=()

cleanup() {
  echo "Stopping services..."
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT

start_tunnels() {
  echo "Starting Tunnels..."
  
  # One Ngrok tunnel for both Dashboard (3000) and Backend (proxied via 3000)
  ngrok http 3000 --log=stdout > "$LOG_DIR/ngrok.log" 2>&1 &
  pids+=("$!")
  
  # Cloudflare Tunnel for LiveKit (7880)
  cloudflared tunnel --url http://localhost:7880 --logfile "$LOG_DIR/cloudflared_livekit.log" --loglevel info > /dev/null 2>&1 &
  pids+=("$!")

  echo "Waiting 15 seconds for URLs..."
  sleep 10
  
  local MASTER_URL
  local LIVEKIT_URL
  
  MASTER_URL=$(curl -s http://localhost:4040/api/tunnels | "$PYTHON_BIN" -c "import sys, json; print(next(t['public_url'] for t in json.load(sys.stdin)['tunnels'] if t['name'] == 'command_line'))" || echo "")
  LIVEKIT_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$LOG_DIR/cloudflared_livekit.log" | tail -1 || echo "")

  echo "Updating dashboard/.env..."
  # Both Backend and Dashboard use the SAME URL now thanks to Next.js rewrites
  cat <<EOF > "$ROOT_DIR/dashboard/.env"
NEXT_PUBLIC_API_BASE_URL=$MASTER_URL/api/backend
NEXT_PUBLIC_LIVEKIT_URL=$LIVEKIT_URL
LIVEKIT_API_KEY=hawkeye_dev_key
LIVEKIT_API_SECRET=hawkeye_dev_secret_2026_xxxxxxxxxxxxxxxx
EOF

  echo "==========================================================="
  echo "🚀 LIVE URLS READY:"
  echo "   Dashboard: $MASTER_URL"
  echo "   Camera:    $MASTER_URL/camera"
  echo "   LiveKit:   $LIVEKIT_URL"
  echo "==========================================================="
}

start_services() {
  echo "Starting Backend (8000)..."
  "$PYTHON_BIN" -m uvicorn app.main:app --app-dir "$ROOT_DIR/backend" --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
  pids+=("$!")

  echo "Starting LiveKit (7880)..."
  livekit-server --config "$ROOT_DIR/livekit.yaml" > "$LOG_DIR/livekit.log" 2>&1 &
  pids+=("$!")

  echo "Starting Dashboard (3000)..."
  (cd "$ROOT_DIR/dashboard" && npm run dev -- -H 0.0.0.0 -p 3000) > "$LOG_DIR/dashboard.log" 2>&1 &
  pids+=("$!")

  echo "Starting AI Worker..."
  (cd "$ROOT_DIR/backend" && LIVEKIT_ROOM=hawkeye "$PYTHON_BIN" worker.py) > "$LOG_DIR/worker.log" 2>&1 &
  pids+=("$!")
}

start_tunnels
start_services
wait
