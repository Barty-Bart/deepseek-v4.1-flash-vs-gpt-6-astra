#!/usr/bin/env bash
# Self-contained inspection run: boot the dev server, drive headless Chrome,
# capture screenshots, then shut everything down. Nothing is left running.
set -uo pipefail
cd "$(dirname "$0")/.."

PORT=5178
LOG=build/dev-server.log
mkdir -p build

cleanup() {
  [ -n "${VITE_PID:-}" ] && kill "$VITE_PID" 2>/dev/null
  [ -n "${CHROME_PID:-}" ] && kill "$CHROME_PID" 2>/dev/null
}
trap cleanup EXIT

node node_modules/vite/bin/vite.js --port "$PORT" --strictPort > "$LOG" 2>&1 &
VITE_PID=$!

for i in $(seq 1 60); do
  if curl -sf -o /dev/null "http://127.0.0.1:${PORT}/"; then break; fi
  sleep 0.4
done

if ! curl -sf -o /dev/null "http://127.0.0.1:${PORT}/"; then
  echo "dev server failed to start"; cat "$LOG"; exit 1
fi

PORT_PREVIEW=${PREVIEW_PORT:-0}
node tools/inspect.mjs "${1:-tools/views.json}"
