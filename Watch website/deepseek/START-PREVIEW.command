#!/usr/bin/env bash
# MERIDIAN — local preview launcher.
# Serves the built site at http://127.0.0.1:5178/  (Ctrl-C to stop)
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d dist ]; then
  echo "Building first..."
  npm run build
fi
echo
echo "  MERIDIAN preview:  http://127.0.0.1:5178/"
echo
exec npx --no-install vite preview --port 5178 --strictPort
