#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
node node_modules/vite/bin/vite.js preview --port 5178 --strictPort > build/preview.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null' EXIT
for _ in $(seq 1 60); do curl -sf -o /dev/null http://127.0.0.1:5178/ && break; sleep 0.4; done
echo "index:    $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5178/)"
echo "frame 1:  $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5178/media/seq/landscape/f0001.webp)"
echo "frame 240:$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5178/media/seq/landscape/f0240.webp)"
echo "portrait: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5178/media/seq/portrait/f0240.webp)"
echo "wrist:    $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5178/media/products/m02-atelier-wrist.webp)"
