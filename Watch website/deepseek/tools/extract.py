#!/usr/bin/env python3
"""MERIDIAN frame extraction: masters in, optimized webp sequences out."""
import json, os, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MASTERS = ROOT / "assets" / "masters"
SEQ = ROOT / "assets" / "sequences"
POST = ROOT / "assets" / "posters"


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = (s.get("r_frame_rate") or "25/1").split("/")
    return {
        "width": int(s["width"]), "height": int(s["height"]),
        "fps": float(num) / float(den or 1),
        "duration": float(s.get("duration") or 0),
    }


def extract(src, out_dir, width, fps, quality=74, start=0.0, end=None, prefix="f"):
    src = Path(src)
    info = probe(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob(f"{prefix}-*.webp"):
        f.unlink()
    cls = info["height"] / info["width"]
    height = int(round(width * cls / 2) * 2)
    end = end if end is not None else info["duration"]
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-ss", f"{start}", "-to", f"{end}", "-i", str(src),
           "-vf", f"fps={fps},scale={width}:{height}:flags=lanczos",
           "-c:v", "libwebp", "-quality", str(quality), "-compression_level", "6",
           "-preset", "picture", "-an",
           str(out_dir / f"{prefix}-%04d.webp")]
    subprocess.run(cmd, check=True)
    frames = sorted(out_dir.glob(f"{prefix}-*.webp"))
    return {"source": src.name, "width": width, "height": height,
            "fps": fps, "frames": len(frames),
            "start": start, "end": round(end, 3), "src_info": info}


def poster(src, out, width, at=None):
    src = Path(src)
    info = probe(src)
    at = info["duration"] - 0.05 if at is None else at
    cls = info["height"] / info["width"]
    height = int(round(width * cls / 2) * 2)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(src),
                    "-frames:v", "1", "-vf", f"scale={width}:{height}:flags=lanczos",
                    "-c:v", "libwebp", "-quality", "82", str(out)], check=True)
    return str(out)


def last_frame(src, out, width, pad=0.06):
    return poster(src, out, width, at=max(0.0, probe(src)["duration"] - pad))


if __name__ == "__main__":
    print("import this module; use extract()/last_frame()/poster()")


def scale_to(im, width):
    h = int(round(im.height * width / im.width / 2) * 2)
    return im.resize((width, h), Image.LANCZOS)


def still(src, out, width, quality=86):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    im = scale_to(Image.open(src).convert("RGB"), width)
    im.save(out, "WEBP", quality=quality, method=6)
    return out


def webp_sequence(src, out_dir, width, fps, quality=72, start=0.0, end=None, prefix="f"):
    """Decode with ffmpeg to a temp png sequence, encode to webp with Pillow, drop the pngs."""
    import shutil, tempfile
    info = probe(src)
    end = info["duration"] if end is None else end
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob(f"{prefix}-*.webp"):
        f.unlink()
    tmp = Path(tempfile.mkdtemp(prefix="seq-"))
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-to", str(end),
                        "-i", str(src), "-vf", f"fps={fps}", "-an",
                        str(tmp / "src-%05d.png")], check=True)
        srcs = sorted(tmp.glob("src-*.png"))
        for i, p in enumerate(srcs, 1):
            im = scale_to(Image.open(p).convert("RGB"), width)
            im.save(out_dir / f"{prefix}-{i:04d}.webp", "WEBP", quality=quality, method=5)
        out = {"source": Path(src).name, "width": width, "height": None,
               "fps": fps, "frames": len(srcs), "start": start,
               "end": round(end, 3), "src_info": info}
        first = image_size(out_dir / f"{prefix}-0001.webp")
        out["width"], out["height"] = first
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def image_size(path):
    with Image.open(path) as im:
        return im.size


def last_frame_png(src, out, pad=0.06):
    """Real last decoded frame, full source resolution, kept as the master seam frame."""
    info = probe(src)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss",
                    str(max(0.0, info["duration"] - pad)), "-i", str(src),
                    "-frames:v", "1", str(out)], check=True)
    return out


def sheet(paths, out, cell_w=520, cols=3, label_h=24, bg=(22, 22, 24)):
    cells = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        h = int(im.height * cell_w / im.width)
        cells.append((p.name, im.resize((cell_w, h), Image.LANCZOS)))
    if not cells:
        raise SystemExit("no images for sheet")
    cols = min(cols, len(cells))
    rows = (len(cells) + cols - 1) // cols
    row_h = [0] * rows
    for i, (_, im) in enumerate(cells):
        row_h[i // cols] = max(row_h[i // cols], im.height + label_h)
    W = cols * cell_w + (cols + 1) * 8
    H = sum(row_h) + (rows + 1) * 8
    out_im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(out_im)
    y = 8
    for r in range(rows):
        x = 8
        for c in range(cols):
            i = r * cols + c
            if i >= len(cells):
                break
            name, im = cells[i]
            d.text((x + 4, y + 5), name, fill=(200, 200, 206))
            out_im.paste(im, (x, y + label_h))
            x += cell_w + 8
        y += row_h[r] + 8
    out_im.save(out, quality=90)
    return out
