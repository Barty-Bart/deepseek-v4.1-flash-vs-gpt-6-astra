#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
node node_modules/vite/bin/vite.js preview --port 5179 --strictPort > build/preview.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:5179/ && break; sleep 0.4; done
node tools/inspect.mjs "${1:-tools/views.json}"
