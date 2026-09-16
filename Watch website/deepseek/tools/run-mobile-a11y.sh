#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
node node_modules/vite/bin/vite.js --port 5178 --strictPort > build/dev-server.log 2>&1 &
VITE_PID=$!
trap 'kill $VITE_PID 2>/dev/null' EXIT
for _ in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:5178/ && break; sleep 0.4; done
node tools/mobile-a11y.mjs
