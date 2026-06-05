#!/usr/bin/env python3
"""
Gradient-map body recolor for Panamera renders (port of the JS engine in the colour site).
Takes the real white base render + body mask, repaints ONLY the masked body into an exact
target colour while keeping real reflections, shading, gloss, glass, wheels and background.

Usage:  python3 tools/recolor.py <color-id> <hex>      e.g.  python3 tools/recolor.py popular-montego-blue-metallic 1a3556
Renders all 6 views into public/panamera_google_assistant_assets/generated-renders/<color-id>/<view>.jpg
"""
import sys, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "public")
CAR = os.path.join(PUB, "tuning-assets", "base", "car")
MASKS = os.path.join(PUB, "tuning-assets", "base", "masks")
OUT = os.path.join(PUB, "panamera_google_assistant_assets", "generated-renders")
VIEWS = ["front-left", "side", "rear-left", "top", "front", "rear"]

# tunables — must match index.html drawPreview
LP = 0.80
CONTRAST = 1.5
SHADOW_MUL = 0.18


def recolor_view(base_path, mask_path, target):
    base = np.asarray(Image.open(base_path).convert("RGB"), dtype=np.float64)
    mask = Image.open(mask_path).convert("RGB").resize(
        (base.shape[1], base.shape[0]), Image.BILINEAR)
    a = np.minimum(245.0, np.asarray(mask, dtype=np.float64)[:, :, 0]) / 255.0  # red channel -> alpha
    tr, tg, tb = target
    tlum = (0.299 * tr + 0.587 * tg + 0.114 * tb) / 255.0
    spec = min(0.94, max(0.30, 0.92 - 0.58 * tlum))
    sh = np.array([tr, tg, tb]) * SHADOW_MUL
    L = (0.299 * base[:, :, 0] + 0.587 * base[:, :, 1] + 0.114 * base[:, :, 2]) / 255.0
    x = np.clip(LP + (L - LP) * CONTRAST, 0.0, 1.0)
    out = np.empty_like(base)
    lower = x <= LP
    # lower branch: shadow -> target
    t_lo = (x / LP)[..., None]
    lo = sh + (np.array([tr, tg, tb]) - sh) * t_lo
    # upper branch: target -> white specular
    t_hi = (((x - LP) / (1.0 - LP)) ** 2 * spec)[..., None]
    hi = np.array([tr, tg, tb]) + (255.0 - np.array([tr, tg, tb])) * t_hi
    out = np.where(lower[..., None], lo, hi)
    a3 = a[..., None]
    comp = base * (1.0 - a3) + out * a3
    return Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8), "RGB")


def main():
    cid, hexv = sys.argv[1], sys.argv[2].lstrip("#")
    target = (int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16))
    dst = os.path.join(OUT, cid)
    os.makedirs(dst, exist_ok=True)
    for v in VIEWS:
        img = recolor_view(os.path.join(CAR, v + ".jpg"), os.path.join(MASKS, v + ".png"), target)
        img.save(os.path.join(dst, v + ".jpg"), "JPEG", quality=88)
        print("wrote", os.path.join(cid, v + ".jpg"))
    print("done:", cid, "#" + hexv)


if __name__ == "__main__":
    main()
