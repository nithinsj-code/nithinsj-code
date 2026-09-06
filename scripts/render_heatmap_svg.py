#!/usr/bin/env python3
"""
render_heatmap_svg.py — draw data/contributions.json as the classic
53-week x 7-day calendar of rounded boxes, revealed once with a
diagonal, line-after-line slide-down (CSS keyframes, no looping),
plus a Less->More legend and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py [-o contrib-heatmap.svg]
"""
import json
import argparse
import datetime as dt

PALETTE = [
    "#161b22",  # level 0 - none
    "#0e4429",  # level 1
    "#006d32",  # level 2
    "#26a641",  # level 3
    "#39d353",  # level 4 (top of GitHub's own scale)
]
NEON_TOP = "#69f0a0"  # optional level-5 neon accent for an exceptional day

BG = "transparent"
TEXT_DIM = "#8b949e"
TEXT_MAIN = "#c9d1d9"
FONT = "SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

CELL = 11
GAP = 3
RADIUS = 2
LEFT_PAD = 28   # room for weekday labels
TOP_PAD = 20    # room for month labels
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_data(path="data/contributions.json") -> dict:
    with open(path) as f:
        return json.load(f)


def to_weeks(days: list[dict]) -> list[list[dict | None]]:
    """Group flat day list into GitHub-style weeks (columns), Sun-Sat rows."""
    parsed = []
    for d in days:
        date = dt.date.fromisoformat(d["date"])
        parsed.append({**d, "_date": date, "weekday": (date.weekday() + 1) % 7})  # Sun=0

    if not parsed:
        return []

    # pad the front so the first column starts on a Sunday
    first = parsed[0]
    pad_front = first["weekday"]
    padded = [None] * pad_front + parsed

    weeks = []
    for i in range(0, len(padded), 7):
        week = padded[i:i + 7]
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    return weeks


def color_for(day: dict | None) -> str:
    if day is None:
        return "transparent"
    level = min(day.get("level", 0), 4)
    return PALETTE[level]


def build_svg(data: dict, width_hint: int = 860) -> str:
    days = data["days"]
    stats = data["stats"]
    weeks = to_weeks(days)
    n_weeks = len(weeks)

    grid_w = n_weeks * (CELL + GAP)
    grid_h = 7 * (CELL + GAP)
    width = LEFT_PAD + grid_w + 10
    footer_h = 34
    height = TOP_PAD + grid_h + footer_h + 22

    reveal_dur = 0.6
    week_stagger = 0.018  # per-column stagger -> whole grid reveals diagonally

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{BG}"/>')
    parts.append(
        f'<style>'
        f'text{{font-family:{FONT};}}'
        f'.dim{{fill:{TEXT_DIM};}}'
        f'.main{{fill:{TEXT_MAIN};}}'
        f'@keyframes revealbox{{from{{opacity:0;transform:translateY(-6px);}}'
        f'to{{opacity:1;transform:translateY(0);}}}}'
        f'.box{{animation:revealbox {reveal_dur}s ease-out both;}}'
        f'</style>'
    )

    # month labels (once per month transition)
    last_month = None
    for wi, week in enumerate(weeks):
        for day in week:
            if day is None:
                continue
            month = day["_date"].month
            if month != last_month:
                x = LEFT_PAD + wi * (CELL + GAP)
                parts.append(
                    f'<text x="{x}" y="{TOP_PAD - 7}" class="dim" font-size="10">'
                    f'{MONTH_NAMES[month-1]}</text>'
                )
                last_month = month
            break

    # weekday labels (Mon/Wed/Fri like GitHub)
    for wd, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = TOP_PAD + wd * (CELL + GAP) + CELL - 2
        parts.append(f'<text x="0" y="{y}" class="dim" font-size="9">{label}</text>')

    # grid boxes, diagonal stagger: delay depends on (week + weekday)
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            x = LEFT_PAD + wi * (CELL + GAP)
            y = TOP_PAD + di * (CELL + GAP)
            fill = color_for(day)
            if day is None:
                continue
            delay = (wi + di) * week_stagger
            parts.append(
                f'<rect class="box" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RADIUS}" fill="{fill}" style="animation-delay:{delay:.3f}s">'
                f'<title>{day["count"]} contributions on {day["date"]}</title>'
                f'</rect>'
            )

    # legend: Less [boxes] More
    legend_y = TOP_PAD + grid_h + 24
    lx = LEFT_PAD
    parts.append(f'<text x="{lx}" y="{legend_y+9}" class="dim" font-size="10">Less</text>')
    lx += 32
    for i, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{lx + i*(CELL+GAP)}" y="{legend_y}" width="{CELL}" height="{CELL}" '
            f'rx="{RADIUS}" fill="{color}"/>'
        )
    lx += len(PALETTE) * (CELL + GAP) + 6
    parts.append(f'<text x="{lx}" y="{legend_y+9}" class="dim" font-size="10">More</text>')

    # stats footer
    total = stats["total"]
    streak = stats["longest_streak"]
    cur = stats["current_streak"]
    footer = f'{total:,} contributions in the last year \u00b7 longest streak {streak} days \u00b7 current streak {cur} days'
    parts.append(
        f'<text x="{width - 10}" y="{legend_y+9}" text-anchor="end" class="main" '
        f'font-size="11">{footer}</text>'
    )

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="contrib-heatmap.svg")
    ap.add_argument("--data", default="data/contributions.json")
    args = ap.parse_args()

    data = load_data(args.data)
    svg = build_svg(data)
    with open(args.output, "w") as f:
        f.write(svg)
    print(f"wrote {args.output}")
