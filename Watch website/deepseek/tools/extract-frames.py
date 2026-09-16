#!/usr/bin/env python3
"""Decode accepted clips into flat, manifest-matching webp sequences.

  python3 tools/extract-frames.py landscape   (or portrait)

Writes public/media/seq/<key>/f0001.webp ... and build/<key>_counts.json.
The originals in assets/masters/video are never modified.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import scale_to  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "landscape": {"width": 1152, "file": "L", "clips": [1, 2, 3, 4], "dir": "assets/masters/video/normalised"},
    "portrait": {"width": 720, "file": "P", "clips": [1, 2, 3, 4], "dir": "assets/masters/video/normalised"},
}


def run(key, fps=16, quality=68):
    spec = SOURCES[key]
    out = ROOT / "public/media/seq" / key
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.webp"):
        old.unlink()
    counts, index = [], 1
    for n in spec["clips"]:
        src = ROOT / f"{spec.get('dir', 'assets/masters/video')}/{spec['file']}{n}.mp4"
        if not src.exists():
            raise SystemExit(f"missing master: {src}")
        tmp = Path(tempfile.mkdtemp(prefix="seq-"))
        try:
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"fps={fps}", "-an",
                 str(tmp / "s-%05d.png")], check=True)
            frames = sorted(tmp.glob("s-*.png"))
            for p in frames:
                im = scale_to(Image.open(p).convert("RGB"), spec["width"])
                im.save(out / f"f{index:04d}.webp", "WEBP", quality=quality, method=5)
                index += 1
            counts.append(len(frames))
            print(f"{key} {src.name}: {len(frames)} frames", flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    (ROOT / f"build/counts-{key}.json").write_text(json.dumps(counts))
    print(f"{key} total {sum(counts)} frames at {spec['width']}px, fps={fps}, q={quality}", counts)


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "landscape"
    fps = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 68
    run(key, fps=fps, quality=quality)
