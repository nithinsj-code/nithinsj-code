#!/usr/bin/env python3
"""
make_ascii_svg.py — convert the prepped grayscale image into a
self-typing, monochrome ASCII-art SVG.

Each row of characters sits behind its own horizontal <clipPath> that
wipes open left-to-right (a small block "cursor" rides the wipe edge),
staggered top-to-bottom so the portrait appears to type itself in.
It plays once and freezes — no looping. Pure SMIL, no JS, no external CSS.

Usage:
    python scripts/make_ascii_svg.py [source-prepped.png] [-o avi-ascii.svg]
"""
import argparse
import numpy as np
from PIL import Image

# bright (sparse) -> dark (dense); leading space clears background to nothing
RAMP = " .`:-=+*cs#%@"

FILL = "#8fd6a8"          # single monochrome color (soft terminal green)
BG = "transparent"
FONT = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

# monospace glyphs are roughly this wide relative to their line-height
CHAR_ASPECT = 0.56


def image_to_grid(img: Image.Image, cols: int) -> list[str]:
    w, h = img.size
    cell_w = w / cols
    # convert cols (char units) to rows (char units) accounting for
    # glyphs being taller than they are wide
    rows = max(1, round((h / cell_w) * CHAR_ASPECT))
    small = img.resize((cols, rows), Image.LANCZOS)
    arr = np.array(small, dtype=np.float32) / 255.0  # 0=black,1=white

    lines = []
    n = len(RAMP) - 1
    for y in range(rows):
        row_chars = []
        for x in range(cols):
            brightness = arr[y, x]
            # invert: bright -> low density index (sparse), dark -> high
            idx = int(round((1.0 - brightness) * n))
            row_chars.append(RAMP[idx])
        lines.append("".join(row_chars))
    return trim_blank_margins(lines)


def trim_blank_margins(lines: list[str], pad: int = 2) -> list[str]:
    """Crop fully-blank rows/columns around the subject, with a small pad."""
    non_blank_rows = [i for i, l in enumerate(lines) if l.strip()]
    if not non_blank_rows:
        return lines
    top, bottom = non_blank_rows[0], non_blank_rows[-1]

    width = max(len(l) for l in lines)
    cols_used = set()
    for l in lines:
        for x, ch in enumerate(l):
            if ch != " ":
                cols_used.add(x)
    left, right = min(cols_used), max(cols_used)

    top = max(0, top - pad)
    bottom = min(len(lines) - 1, bottom + pad)
    left = max(0, left - pad)
    right = min(width - 1, right + pad)

    return [l[left:right + 1].ljust(right - left + 1) for l in lines[top:bottom + 1]]


def build_svg(lines: list[str], font_size: int = 9) -> str:
    cols = max(len(l) for l in lines)
    rows = len(lines)
    char_w = font_size * CHAR_ASPECT
    line_h = font_size * 1.0
    width = cols * char_w
    height = rows * line_h

    row_dur = 0.9          # seconds for a single row's wipe
    row_stagger = 0.045    # seconds between successive row starts
    cursor_w = char_w * 1.1

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG}"/>')
    parts.append(
        f'<style>text{{font-family:{FONT};font-size:{font_size}px;'
        f'fill:{FILL};white-space:pre;}}</style>'
    )

    for i, line in enumerate(lines):
        y = (i + 1) * line_h - line_h * 0.22
        start = i * row_stagger
        clip_id = f"clip{i}"
        row_w = len(line) * char_w

        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(f'<rect x="0" y="{i*line_h:.2f}" width="0" height="{line_h:.2f}">')
        parts.append(
            f'<animate attributeName="width" from="0" to="{row_w:.2f}" '
            f'begin="{start:.3f}s" dur="{row_dur}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )
        parts.append('</rect>')
        parts.append('</clipPath>')

        safe_line = (
            line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(f'<text x="0" y="{y:.2f}">{safe_line}</text>')
        parts.append('</g>')

        # small block cursor that rides the wipe edge, then vanishes
        parts.append(
            f'<rect x="0" y="{i*line_h:.2f}" width="{cursor_w:.2f}" '
            f'height="{line_h:.2f}" fill="{FILL}" opacity="0.9">'
        )
        parts.append(
            f'<animate attributeName="x" from="0" to="{row_w:.2f}" '
            f'begin="{start:.3f}s" dur="{row_dur}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )
        parts.append(
            f'<animate attributeName="opacity" from="0.9" to="0" '
            f'begin="{start + row_dur:.3f}s" dur="0.15s" fill="freeze"/>'
        )
        parts.append('</rect>')

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?", default="source-prepped.png")
    ap.add_argument("-o", "--output", default="avi-ascii.svg")
    ap.add_argument("--cols", type=int, default=100)
    ap.add_argument("--font-size", type=int, default=9)
    args = ap.parse_args()

    img = Image.open(args.input).convert("L")
    lines = image_to_grid(img, args.cols)
    svg = build_svg(lines, font_size=args.font_size)

    with open(args.output, "w") as f:
        f.write(svg)
    print(f"wrote {args.output}  ({len(lines)} rows x {args.cols} cols)")
