#!/usr/bin/env python3
"""
prep_photo.py — turn a source photo into a clean grayscale image ready
for ASCII-fication.

Pipeline:
  1. Remove the background with rembg so only the subject remains.
  2. Boost local contrast with OpenCV CLAHE (this is what gives a flat
     face/character real highlights and shadows).
  3. Composite onto pure white so the background maps to the blank end
     of the ASCII ramp (white -> space character).

Usage:
    python scripts/prep_photo.py source-photo.jpg
Writes:
    source-prepped.png (grayscale, same folder as input unless -o given)
"""
import sys
import argparse
import numpy as np
import cv2
from PIL import Image
from rembg import remove, new_session

# u2netp is the small (~4MB) variant of the background-removal net.
# The default model rembg picks these days is a ~1GB model that will
# OOM on modest hardware / CI runners — u2netp is plenty for this use case.
_SESSION = new_session("u2netp")


def prep(input_path: str, output_path: str, size: int = 900):
    with open(input_path, "rb") as f:
        input_bytes = f.read()

    # 1. Remove background -> RGBA with alpha mask around the subject
    result_bytes = remove(input_bytes, session=_SESSION)
    rgba = Image.open(__import__("io").BytesIO(result_bytes)).convert("RGBA")

    # Downscale to a sane working size (keeps the ASCII step fast)
    rgba.thumbnail((size, size), Image.LANCZOS)

    # 2. Composite onto pure white using the alpha mask
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_bg, rgba).convert("RGB")

    # 3. CLAHE contrast boost (operate in LAB's L channel so colors don't skew)
    arr = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(arr)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    arr = cv2.merge((l, a, b))
    contrasted = cv2.cvtColor(arr, cv2.COLOR_LAB2RGB)

    # Convert to grayscale for the ASCII density mapping
    gray = cv2.cvtColor(contrasted, cv2.COLOR_RGB2GRAY)

    # Re-flatten background to pure white using the original alpha mask,
    # so anything rembg marked as "not subject" reliably maps to space glyphs.
    alpha = np.array(rgba.split()[-1])
    gray = np.where(alpha > 10, gray, 255).astype(np.uint8)

    Image.fromarray(gray).save(output_path)
    print(f"wrote {output_path}  ({gray.shape[1]}x{gray.shape[0]})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="source photo path")
    ap.add_argument("-o", "--output", default="source-prepped.png")
    args = ap.parse_args()
    prep(args.input, args.output)
