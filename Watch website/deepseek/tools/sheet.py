#!/usr/bin/env python3
"""Build a labelled contact sheet from image paths so several assets can be inspected together."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

def build(paths, out, cell_w=760, cols=2, label_h=26, bg=(24, 24, 26)):
    cells = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        im = Image.open(p).convert("RGB")
        h = int(im.height * cell_w / im.width)
        cells.append((p.name, im.resize((cell_w, h), Image.LANCZOS)))
    if not cells:
        raise SystemExit("no images")
    cols = min(cols, len(cells))
    rows = (len(cells) + cols - 1) // cols
    row_h = [0] * rows
    for i, (_, im) in enumerate(cells):
        row_h[i // cols] = max(row_h[i // cols], im.height + label_h)
    W = cols * cell_w + (cols + 1) * 10
    H = sum(row_h) + (rows + 1) * 10
    sheet = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(sheet)
    y = 10
    for r in range(rows):
        x = 10
        for c in range(cols):
            i = r * cols + c
            if i >= len(cells):
                break
            name, im = cells[i]
            d.text((x + 4, y + 6), name, fill=(210, 210, 215))
            sheet.paste(im, (x, y + label_h))
            x += cell_w + 10
        y += row_h[r] + 10
    sheet.save(out, quality=92)
    print(out, sheet.size)

if __name__ == "__main__":
    out = sys.argv[1]
    build(sys.argv[2:], out)
