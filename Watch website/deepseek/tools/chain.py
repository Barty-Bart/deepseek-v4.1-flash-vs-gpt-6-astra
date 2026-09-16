#!/usr/bin/env python3
"""Frame-chain helpers for the MERIDIAN film.

    python3 tools/chain.py last  <clip.mp4> <out.png>     # real last decoded frame
    python3 tools/chain.py probe <clip.mp4> a b c ...      # contact sheet of frame numbers
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import probe, last_frame_png, sheet  # noqa: E402


def frame_at(src, n, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-vf", f"select=eq(n\\,{n - 1})", "-frames:v", "1", str(out)], check=True)
    return out


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "last":
        out = last_frame_png(sys.argv[2], sys.argv[3])
        print(out)
    elif cmd == "probe":
        src = sys.argv[2]
        nums = [int(x) for x in sys.argv[3:]]
        info = probe(src)
        total = int(info["duration"] * info["fps"])
        tmp = Path("build/probe")
        tmp.mkdir(parents=True, exist_ok=True)
        stem = Path(src).stem
        paths = []
        for n in nums:
            if n > total:
                n = total
            paths.append(frame_at(src, n, tmp / f"{stem}-{n}.png"))
        out = tmp / f"{stem}-sheet.png"
        sheet(paths, out, cell_w=430, cols=3)
        print(out, f"src frames~{total} {info['width']}x{info['height']}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
