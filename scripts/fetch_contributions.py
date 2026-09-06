#!/usr/bin/env python3
"""
fetch_contributions.py — pull the real contribution calendar without any
GraphQL API or personal access token.

GitHub serves the calendar as public HTML at
https://github.com/users/<username>/contributions — the same fragment the
profile page itself fetches. We parse the day cells with BeautifulSoup and
write data/contributions.json with raw days plus a few derived stats
(current streak, longest streak, best day, monthly totals).

Usage:
    python scripts/fetch_contributions.py [username]
"""
import sys
import json
import datetime as dt
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "nithinsj-code"
URL_TMPL = "https://github.com/users/{user}/contributions"


def fetch_days(username: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)"}
    resp = requests.get(URL_TMPL.format(user=username), headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    days = []
    # Current markup: <td class="ContributionCalendar-day" data-date="YYYY-MM-DD"
    #                  data-level="0-4" tooltip via aria-label / role=gridcell>
    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        # older markup fallback: rect elements
        cells = soup.select("rect.ContributionCalendar-day")

    for cell in cells:
        date = cell.get("data-date")
        level = cell.get("data-level")
        if date is None:
            continue
        level = int(level) if level is not None else 0
        # count comes from the tooltip text ("N contributions on ...")
        count = 0
        tt_id = cell.get("id")
        label = None
        if tt_id:
            tooltip = soup.select_one(f'tool-tip[for="{tt_id}"]')
            if tooltip:
                label = tooltip.get_text(strip=True)
        if not label:
            label = cell.get("aria-label", "")
        if label:
            first_tok = label.split(" ")[0]
            count = 0 if first_tok.lower() == "no" else _safe_int(first_tok)
        days.append({"date": date, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def _safe_int(tok: str) -> int:
    try:
        return int(tok.replace(",", ""))
    except ValueError:
        return 0


def derive_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)

    # streaks
    longest = current = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    # current streak = run ending at the last day with data
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        else:
            break

    best = max(days, key=lambda d: d["count"], default=None)

    monthly = defaultdict(int)
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] += d["count"]

    return {
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best,
        "monthly": dict(sorted(monthly.items())),
    }


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_USERNAME
    days = fetch_days(username)
    stats = derive_stats(days)
    out = {
        "username": username,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "days": days,
        "stats": stats,
    }
    with open("data/contributions.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote data/contributions.json  ({len(days)} days, {stats['total']} total)")


if __name__ == "__main__":
    main()
