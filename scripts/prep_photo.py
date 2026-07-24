#!/usr/bin/env python3
"""Prep a photo for ASCII conversion.

Pipeline:
  1. Remove the background (rembg) so the subject is isolated.
  2. Boost local contrast with CLAHE so a flat face gains highlights/shadows.
  3. Composite onto pure white so the background maps to the blank end of the
     ASCII ramp (white -> spaces).

Usage:
    python scripts/prep_photo.py source-photo.jpg [output.png]

Output defaults to scripts/source-prepped.png, which make_ascii_svg.py reads.
"""
import sys
from pathlib import Path

import cv2
import numpy as np


def remove_background(rgb: np.ndarray) -> np.ndarray:
    """Return an RGBA image with the background removed via rembg."""
    from rembg import remove
    from PIL import Image

    pil = Image.fromarray(rgb)
    cut = remove(pil)  # RGBA PIL image
    return np.array(cut.convert("RGBA"))


def crop_to_subject(rgba: np.ndarray, margin: float = 0.06) -> np.ndarray:
    """Crop to the alpha bounding box (+margin) so the subject fills the frame."""
    alpha = rgba[:, :, 3]
    ys, xs = np.where(alpha > 24)
    if ys.size == 0:
        return rgba
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    h, w = rgba.shape[:2]
    my = int((y1 - y0) * margin)
    mx = int((x1 - x0) * margin)
    y0 = max(0, y0 - my); y1 = min(h - 1, y1 + my)
    x0 = max(0, x0 - mx); x1 = min(w - 1, x1 + mx)
    return rgba[y0:y1 + 1, x0:x1 + 1]


def composite_on_white(rgba: np.ndarray) -> np.ndarray:
    """Alpha-composite an RGBA image over a pure white background -> RGB."""
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = (rgba[:, :, 3:4].astype(np.float32)) / 255.0
    white = np.full_like(rgb, 255.0)
    out = rgb * alpha + white * (1.0 - alpha)
    return out.astype(np.uint8)


def boost_contrast(gray: np.ndarray) -> np.ndarray:
    """Contrast-limited adaptive histogram equalization."""
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    return clahe.apply(gray)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python scripts/prep_photo.py <source-photo> [output.png]")
        sys.exit(1)

    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("source-prepped.png")

    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if bgr is None:
        print(f"could not read image: {src}")
        sys.exit(1)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    print("removing background...")
    rgba = remove_background(rgb)

    print("cropping to subject...")
    rgba = crop_to_subject(rgba)

    print("compositing on white...")
    rgb_white = composite_on_white(rgba)

    print("boosting contrast (CLAHE)...")
    gray = cv2.cvtColor(rgb_white, cv2.COLOR_RGB2GRAY)
    gray = boost_contrast(gray)

    cv2.imwrite(str(out), gray)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
