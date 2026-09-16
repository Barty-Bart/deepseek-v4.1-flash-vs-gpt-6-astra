#!/usr/bin/env python3
"""Build site/src/manifest.json from the accepted clip order.

The manifest is the single source of truth the player reads: real frame counts,
real dimensions, a valid poster per variant and the naming pattern.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import webp_sequence, probe  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEQ = ROOT / "public" / "media" / "seq"
POST = ROOT / "public" / "media" / "posters"
OUT = ROOT / "site" / "src" / "manifest.json"

CLIPS = json.loads((ROOT / "tools" / "clips.json").read_text())

# travel (viewport multiples) and hold (progress fraction) per beat.
# Driven by the brief: desktop ~1 / 1.5 / 1 / 1.5 viewports, mobile ~0.7 / 1 / 0.7 / 1.
BEATS = {
    "desktop": [
        {"id": "assembled", "label": "I", "travel": 1.0, "hold": 0.1},
        {"id": "exploded", "label": "II", "travel": 1.5, "hold": 0.12},
        {"id": "macro", "label": "III", "travel": 1.0, "hold": 0.02},
        {"id": "wrist", "label": "IV", "travel": 1.5, "hold": 0.16},
    ],
    "mobile": [
        {"id": "assembled", "label": "I", "travel": 0.7, "hold": 0.1},
        {"id": "exploded", "label": "II", "travel": 1.0, "hold": 0.12},
        {"id": "macro", "label": "III", "travel": 0.7, "hold": 0.02},
        {"id": "wrist", "label": "IV", "travel": 1.0, "hold": 0.16},
    ],
}

WIDTH = {"landscape": 1440, "portrait": 720}
FPS = 18


def build_timeline(rows, counts):
    """Convert per-beat travel/hold into stops with strictly increasing p values."""
    total_travel = sum(r["travel"] for r in rows)
    total_hold = sum(r["hold"] for r in rows)
    scale = (1 - total_hold) / total_travel

    stops = [{"p": 0.0, "frame": 0, "kind": "travel"}]
    beats = []
    cursor = 0.0
    frame = 1
    for i, row in enumerate(rows):
        start_frame = frame
        end_frame = frame + counts[i] - 1
        travel = row["travel"] * scale
        p_travel_end = cursor + travel
        p_hold_end = p_travel_end + row["hold"]

        if i > 0:
            stops.append({"p": round(cursor, 5), "frame": start_frame - 1, "kind": "travel"})
        stops.append({"p": round(p_travel_end, 5), "frame": end_frame, "kind": "travel"})

        beats.append({
            "id": row["id"],
            "label": row["label"],
            "start": round(cursor, 5),
            "end": round(p_travel_end, 5),
            "holdEnd": round(p_hold_end, 5),
            "frameStart": start_frame,
            "frameEnd": end_frame,
        })

        cursor = p_hold_end
        frame = end_frame + 1

    stops.append({"p": round(min(1.0, cursor), 5), "frame": frame - 1, "kind": "hold"})
    return stops, beats


def main():
    variants = {}
    for key, clips in CLIPS.items():
        width = WIDTH[key]
        out_dir = SEQ / key
        counts = []
        sources = []
        for clip in clips:
            src = ROOT / clip["file"]
            info = webp_sequence(src, out_dir, width, FPS, quality=72,
                                 prefix=f"f{clip['n']}")
            counts.append(info["frames"])
            sources.append({"clip": clip["n"], "file": clip["file"],
                            "frames": info["frames"], "src": probe(src)})
            print(f"{key} clip {clip['n']}: {info['frames']} frames", flush=True)

        total = sum(counts)
        rows = BEATS[key]
        stops, beats = build_timeline(rows, counts)
        variants[key] = {
            "width": width,
            "height": None,
            "fps": FPS,
            "frames": total,
            "clips": counts,
            "path": f"./media/seq/{key}/f{{i}}.webp",
            "poster": f"./media/posters/{key}-poster.webp",
            "sources": sources,
        }
        variants[key]["stops"] = stops
        variants[key]["beats"] = beats
        if key == "portrait":
            variants[key]["height"] = 1290
        else:
            variants[key]["height"] = 810

    timeline = {}
    for kind, keys in (("desktop", ["landscape"]), ("mobile", ["portrait"])):
        rows = BEATS[kind]
        counts = sum((variants[k]["clips"] for k in keys), [])
        total = sum(counts)
        per = counts[: len(rows)]
        road = rows
        timeline[kind] = {
            "stageViewports": round(sum(r["travel"] for r in road) + 1, 4),
            "totalFrames": total,
            "fps": FPS,
            "clipFrames": per,
            "stops": variants[keys[0]]["stops"],
            "beats": variants[keys[0]]["beats"],
        }
        for k in keys:
            del variants[k]["stops"]
            del variants[k]["beats"]

    manifest = {
        "generatedAt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "source": "generated masters, frames extracted with ffmpeg + Pillow (webp)",
        "qualityNote": "landscape 1440px wide, portrait 720px wide, 18 fps target",
        "posters": {
            "landscape": "./media/posters/landscape-poster.webp",
            "portrait": "./media/posters/portrait-poster.webp",
        },
        "variants": variants,
        "timeline": timeline,
    }
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
