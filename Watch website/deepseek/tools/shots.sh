#!/usr/bin/env bash
# Render the local preview at a viewport and scroll offset, then screenshot it.
#   tools/shots.sh <name> <width> <height> <scrollY> [reduced]
set -euo pipefail
name="$1"; w="$2"; h="$3"; y="${4:-0}"; mode="${5:-}"
flags=(--headless=new --disable-gpu --hide-scrollbars --force-color-profile=srgb
       --window-size="${w},${h}" --virtual-time-budget=6000)
if [ "$mode" = "reduced" ]; then
  flags+=(--force-prefers-reduced-motion)
fi
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "${flags[@]}" \
  --screenshot="build/shots/${name}.png" \
  "http://127.0.0.1:5178/#${y}"
