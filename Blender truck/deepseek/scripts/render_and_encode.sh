#!/bin/zsh
# Render the film in chunks and encode with the system ffmpeg.
# This Blender 5.2.1 build cannot write video directly (FFMPEG is not offered in
# scene.render.image_settings.file_format), and the boot disk is nearly full, so
# each chunk of PNG frames is encoded to an H.264 segment and then deleted.
set -e
ROOT=.
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
FFMPEG=/opt/homebrew/bin/ffmpeg
cd "$ROOT"
mkdir -p renders/frames renders/segments
rm -f renders/frames/*.png renders/segments/*.mp4 renders/render_log.txt
start=1
chunk=${1:-96}
samples=${2:-48}
idx=0
while [ $start -le 672 ]; do
  end=$((start+chunk-1))
  [ $end -gt 672 ] && end=672
  echo "=== chunk $idx: frames $start-$end ===" >> renders/render_log.txt
  "$BLENDER" --background --factory-startup --python scripts/render_film.py -- \
      --start $start --end $end --samples $samples --out renders/frames/ \
      >> renders/render_log.txt 2>&1
  "$FFMPEG" -y -loglevel error -framerate 24 -start_number $start \
      -i renders/frames/%04d.png -c:v libx264 -preset medium -crf 17 \
      -pix_fmt yuv420p "renders/segments/seg_$(printf %02d $idx).mp4" \
      >> renders/render_log.txt 2>&1
  rm -f renders/frames/*.png
  echo "chunk $idx done (frames $start-$end)" >> renders/render_log.txt
  start=$((end+1))
  idx=$((idx+1))
done
ls renders/segments/*.mp4 | sed "s|^|file '|;s|\$|'|" > renders/concat.txt
"$FFMPEG" -y -loglevel error -f concat -safe 0 -i renders/concat.txt -c copy \
    renders/pickup_truck_1080p.mp4 >> renders/render_log.txt 2>&1
rm -rf renders/frames renders/segments renders/concat.txt
echo "ALL DONE $(date)" >> renders/render_log.txt
