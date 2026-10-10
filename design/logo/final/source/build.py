"""Build the Data Story logo set from the author's final raster (traced into exact two-colour vectors)."""
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SCALE = 4
BLUE, DARK = "#174690", "#3B3B38"
src = Image.open("source.jpg").convert("RGB")
X0, Y0, X1, Y1 = 305, 180, 1103, 577
crop = src.crop((X0, Y0, X1, Y1))
big = np.array(crop.resize((crop.width * SCALE, crop.height * SCALE), Image.LANCZOS)).astype(float)
big = cv2.GaussianBlur(big, (0, 0), 1.2)
ink = (255 - big.min(axis=2)) / 255
blueish = (big[..., 2] - big[..., 0]) > 35
solid = ink > 0.45
H, W = solid.shape


def region(mask, y_from, y_to, x_from=0, x_to=None):
    out = np.zeros_like(mask)
    out[int(y_from * SCALE) : int(y_to * SCALE), int(x_from * SCALE) : int((x_to or W / SCALE) * SCALE)] = mask[
        int(y_from * SCALE) : int(y_to * SCALE), int(x_from * SCALE) : int((x_to or W / SCALE) * SCALE)
    ]
    return out


def trace(mask, eps=0.6):
    m = cv2.morphologyEx((mask * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    d, pts = [], []
    for c in contours:
        if cv2.contourArea(c) < 40:
            continue
        c = cv2.approxPolyDP(c, eps, True)[:, 0, :] / SCALE
        pts.append(c)
        d.append("M" + "L".join(f"{x:.2f} {y:.2f}" for x, y in c) + "Z")
    allp = np.vstack(pts)
    return "".join(d), (allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())


# pieces in crop coordinates (crop is 798 × 397); mark above y=230, name 230–350, tagline below
PIECES = {
    "mark": (region(solid & blueish, 0, 230), BLUE),
    "book": (region(solid & blueish, 0, 230, 357), BLUE),
    "data": (region(solid & blueish, 230, 350), BLUE),
    "story": (region(solid & ~blueish, 230, 350), DARK),
    "tag": (region(solid & ~blueish, 350, 397), DARK),
}
P = {name: (*trace(mask), color) for name, (mask, color) in PIECES.items()}


def place(name, x, y, height=None, width=None):
    d, (bx0, by0, bx1, by1), color = P[name]
    s = height / (by1 - by0) if height else width / (bx1 - bx0)
    return (
        f'<path fill="{color}" fill-rule="evenodd" transform="translate({x:.2f} {y:.2f}) scale({s:.5f}) '
        f'translate({-bx0:.2f} {-by0:.2f})" d="{d}"/>',
        (bx1 - bx0) * s,
        (by1 - by0) * s,
    )


def svg(w, h, parts, pad=0):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad:.2f} {h + 2 * pad:.2f}">{"".join(parts)}</svg>'


out = Path("final")
out.mkdir(exist_ok=True)
files = {}

# 1. full stacked logo exactly as the author's composition, tight bounds
boxes = [P[k][1] for k in ("mark", "data", "story", "tag")]
fx0, fy0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
fx1, fy1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
files["logo-full.svg"] = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fx0:.2f} {fy0:.2f} {fx1 - fx0:.2f} {fy1 - fy0:.2f}">'
    + "".join(f'<path fill="{P[k][2]}" fill-rule="evenodd" d="{P[k][0]}"/>' for k in ("mark", "data", "story", "tag"))
    + "</svg>"
)

# 2. mark only (collapsed menu) and book (square favicon)
d, (bx0, by0, bx1, by1), c = P["mark"]
files["logo-mark.svg"] = svg(bx1 - bx0, by1 - by0, [place("mark", 0, 0, height=by1 - by0)[0]])
d, (bx0, by0, bx1, by1), c = P["book"]
bw, bh = bx1 - bx0, by1 - by0
side = max(bw, bh)
files["logo-icon.svg"] = svg(side, side, [place("book", (side - bw) / 2, (side - bh) / 2, height=bh)[0]], pad=side * 0.04)

# 3. horizontal: mark left, name + tagline right
m, mw, mh = place("mark", 0, 0, height=120)
dp, dw, dh = place("data", mw + 28, 22, height=52)
sp, sw, sh = place("story", mw + 28 + dw + 16, 22, height=52)
tw = dw + 16 + sw
tp, _, th = place("tag", mw + 28, 22 + 52 + 18, width=tw)
files["logo-horizontal.svg"] = svg(mw + 28 + tw, 120, [m, dp, sp, tp])

# 4. side panel (≈208 px): the author's stacked composition scaled to the panel width
files["logo-panel.svg"] = files["logo-full.svg"]

for name, text in files.items():
    (out / name).write_text(text, encoding="utf-8")
print({k: len(v) for k, v in files.items()})
