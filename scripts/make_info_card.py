#!/usr/bin/env python3
"""
make_info_card.py — hand-authored neofetch-style SVG panel.

Renders a title bar + colored key/value rows (Now, Prev, Stack, Highlights).
Each line fades + slides in on a short stagger, like it's printing next
to the ASCII portrait. Set STATIC=1 to emit a frozen end-state frame
(handy for local Quick Look previews where SMIL doesn't animate).

Usage:
    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py -o info-card-static.svg
"""
import os
import argparse

# ---- content -----------------------------------------------------------
USER = "nithinsj-code"
HOST = "github"

FIELDS = [
    ("Now", "AI/ML student, building solo AI + SaaS products"),
    ("Prev", "Freelance web developer"),
    ("Stack", "Next.js \u00b7 FastAPI \u00b7 Supabase \u00b7 Python"),
    ("Highlights", "DrRag \u00b7 ResearchLens \u00b7 Pitch2Scale \u00b7 Nitz"),
]

# ---- palette (Dracula-ish terminal) -------------------------------------
BG = "#161b22"
BORDER = "#30363d"
TITLEBAR = "#21262d"
KEY_COLOR = "#39d353"      # bright green for keys, echoes the heatmap
VAL_COLOR = "#c9d1d9"
PROMPT_COLOR = "#58a6ff"
DIM = "#8b949e"
FONT = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(static: bool, width: int = 490) -> str:
    pad = 22
    row_h = 30
    header_h = 70
    rows = len(FIELDS)
    height = header_h + rows * row_h + pad

    stagger = 0.18
    dur = 0.5

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    parts.append(
        f'<style>'
        f'.mono{{font-family:{FONT};}}'
        f'.key{{fill:{KEY_COLOR};font-weight:600;}}'
        f'.val{{fill:{VAL_COLOR};}}'
        f'.dim{{fill:{DIM};}}'
        f'</style>'
    )

    # card background + border
    parts.append(
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>'
    )
    # title bar
    parts.append(f'<rect x="0.5" y="0.5" width="{width-1}" height="34" rx="10" fill="{TITLEBAR}"/>')
    parts.append(f'<rect x="0.5" y="24.5" width="{width-1}" height="10" fill="{TITLEBAR}"/>')
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{20 + i*18}" cy="17.5" r="6" fill="{c}"/>')
    parts.append(
        f'<text x="{width/2:.0f}" y="22" text-anchor="middle" class="mono dim" '
        f'font-size="12">{USER}@{HOST}</text>'
    )

    # prompt line
    y0 = 58
    parts.append(
        f'<text x="{pad}" y="{y0}" class="mono" font-size="13">'
        f'<tspan fill="{PROMPT_COLOR}">{USER}@{HOST}</tspan>'
        f'<tspan fill="{DIM}"> ~ $ </tspan>'
        f'<tspan fill="{VAL_COLOR}">whoami</tspan>'
        f'</text>'
    )
    parts.append(f'<line x1="{pad}" y1="{y0+14}" x2="{width-pad}" y2="{y0+14}" stroke="{BORDER}"/>')

    key_col_w = 100
    start_y = y0 + 40

    for i, (key, val) in enumerate(FIELDS):
        y = start_y + i * row_h
        g_id = f"row{i}"
        begin = 0.15 + i * stagger

        if static:
            transform_open = f'<g id="{g_id}">'
        else:
            transform_open = (
                f'<g id="{g_id}" opacity="0" transform="translate(-8,0)">'
                f'<animate attributeName="opacity" from="0" to="1" '
                f'begin="{begin:.2f}s" dur="{dur}s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="-8,0" to="0,0" begin="{begin:.2f}s" dur="{dur}s" '
                f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            )

        parts.append(transform_open)
        parts.append(
            f'<text x="{pad}" y="{y}" class="mono key" font-size="13">{esc(key)}</text>'
        )
        val_size = 13 if len(val) <= 34 else 11.5
        parts.append(
            f'<text x="{pad + key_col_w}" y="{y}" class="mono val" font-size="{val_size}">'
            f'{esc(val)}</text>'
        )
        parts.append('</g>')

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="info-card.svg")
    args = ap.parse_args()
    static = bool(os.environ.get("STATIC"))
    svg = build_svg(static=static)
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"wrote {args.output} (static={static})")
