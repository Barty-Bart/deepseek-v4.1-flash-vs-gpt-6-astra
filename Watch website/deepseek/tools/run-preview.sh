#!/usr/bin/env bash
# Boot the built site, run a bounded smoke check, then shut it down.
set -uo pipefail
cd "$(dirname "$0")/.."
node node_modules/vite/bin/vite.js preview --port 5179 --strictPort > build/preview.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:5179/ && break; sleep 0.4; done
echo "index:   $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5179/)"
echo "frames:  $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5179/media/seq/landscape/f0001.webp)"
echo "portrait:$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5179/media/seq/portrait/f0001.webp)"
echo "poster:  $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5179/media/posters/landscape-poster.webp)"
node tools/look.mjs "${1:-tools/look-alias.json}"
