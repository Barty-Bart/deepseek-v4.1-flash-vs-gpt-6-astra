#!/usr/bin/env python3
"""Write site/src/manifest.json from the frames actually extracted.

Reads build/*_counts.json (written by tools/extract-frames.py) so the manifest can
never disagree with the files on disk.
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FPS = 12

# Travel per beat in viewports. Equal beats means the film advances at a constant
# frames-per-pixel rate for its whole length: no flat holds, no density changes
# between clips. The copy beats are labels only - they never stall the picture.
BEATS = {
    "desktop": [
        {"id": "assembled", "label": "I", "travel": 1.2},
        {"id": "exploded", "label": "II", "travel": 1.2},
        {"id": "macro", "label": "III", "travel": 1.2},
        {"id": "wrist", "label": "IV", "travel": 1.2},
    ],
    "mobile": [
        {"id": "assembled", "label": "I", "travel": 0.9},
        {"id": "exploded", "label": "II", "travel": 0.9},
        {"id": "macro", "label": "III", "travel": 0.9},
        {"id": "wrist", "label": "IV", "travel": 0.9},
    ],
}

VARIANTS = {
    "landscape": {
        "width": 1152, "height": 648,
        "countsFile": "build/counts-landscape.json",
        "clips": ["assets/masters/video/L1.mp4", "assets/masters/video/L2.mp4",
                  "assets/masters/video/L3.mp4", "assets/masters/video/L4.mp4"],
        "timeline": "desktop",
    },
    "portrait": {
        "width": 720, "height": 1280,
        "countsFile": "build/counts-portrait.json",
        "clips": ["assets/masters/video/P1.mp4", "assets/masters/video/P2.mp4",
                  "assets/masters/video/P3.mp4", "assets/masters/video/P4.mp4"],
        "timeline": "mobile",
    },
}


def build_timeline(rows, counts):
    """Map scroll progress straight onto frame index.

    The film is one continuous strip of frames, so the mapping is a single linear
    function from progress to frame. Beats only supply the copy label for the
    frame being shown, which is why a beat change can never hide motion: there is
    no separate hold segment to sit through.
    """
    total = sum(counts)
    last = total - 1

    stops = []
    beats = []
    frame = 0
    # one linear segment per beat keeps the arithmetic exact at every seam
    p = 0.0
    for i, row in enumerate(rows):
        seg_frames = counts[i] - 1
        p_end = (frame + seg_frames) / last
        stops.append({"p": round(p, 5), "frame": frame, "kind": "travel"})
        beats.append({
            "id": row["id"], "label": row["label"],
            "start": round(p, 5), "end": round(p_end, 5),
            "frameStart": frame, "frameEnd": frame + seg_frames,
        })
        p = p_end
        frame += counts[i]
    stops.append({"p": 1.0, "frame": last, "kind": "travel"})
    return stops, beats


def main():
    manifest_variants = {}
    timelines = {}
    for key, spec in VARIANTS.items():
        counts = json.loads((ROOT / spec["countsFile"]).read_text())
        total = sum(counts)
        stops, beats = build_timeline(BEATS[spec["timeline"]], counts)
        manifest_variants[key] = {
            "width": spec["width"], "height": spec["height"], "fps": FPS,
            "frames": total, "clips": counts,
            "path": f"./media/seq/{key}/f{{i}}.webp",
            "poster": f"./media/posters/{key}-poster.webp",
            "clipsSource": [{"clip": n + 1, "file": f} for n, f in enumerate(spec["clips"])],
        }
        timelines[spec["timeline"]] = {
            "stageViewports": round(sum(r["travel"] for r in BEATS[spec["timeline"]]) + 1, 4),
            "fps": FPS, "clipFrames": counts, "totalFrames": total,
            "stops": stops, "beats": beats,
        }

    manifest = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": "generated masters; frames extracted with ffmpeg + Pillow (webp q72)",
        "qualityNote": "landscape 1152x648, portrait 720x1280, 10 fps target, webp q58/q52",
        "posters": {
            "landscape": "./media/posters/landscape-poster.webp",
            "portrait": "./media/posters/portrait-poster.webp",
        },
        "variants": manifest_variants,
        "timeline": timelines,
    }
    (ROOT / "site/src/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for k, v in timelines.items():
        print(k, "stageViewports", v["stageViewports"], "frames", v["totalFrames"], v["clipFrames"])


if __name__ == "__main__":
    main()
