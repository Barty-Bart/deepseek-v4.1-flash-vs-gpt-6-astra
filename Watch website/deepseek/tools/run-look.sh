#!/usr/bin/env bash
# Boot the dev server for one bounded inspection run, then shut it down.
set -uo pipefail
cd "$(dirname "$0")/.."
node node_modules/vite/bin/vite.js --port 5178 --strictPort > build/dev-server.log 2>&1 &
VITE_PID=$!
cleanup() { kill "$VITE_PID" 2>/dev/null; }
trap cleanup EXIT
for _ in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:5178/ && break; sleep 0.4; done
node tools/look.mjs "$1"
