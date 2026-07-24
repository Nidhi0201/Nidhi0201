#!/usr/bin/env python3
"""Fetch a GitHub user's contribution calendar as public HTML -- no token.

GitHub serves the calendar the profile page itself uses at
    https://github.com/users/<username>/contributions
We parse the day cells with BeautifulSoup and write data/contributions.json
with the raw days plus derived stats (streaks, best day, monthly totals).

Username resolves from $GH_USERNAME, else the DEFAULT_USERNAME below.

Usage:
    python scripts/fetch_contributions.py
"""
import json
import os
import re
from collections import OrderedDict
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "Nidhi0201"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

_COUNT_RE = re.compile(r"([\d,]+)\s+contribution")


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (profile-art bot; +https://github.com)",
        "Accept": "text/html",
        "X-Requested-With": "XMLHttpRequest",
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str):
    """Return a date-sorted list of {date, count, level, weekday}."""
    soup = BeautifulSoup(html, "html.parser")

    # Tooltips carry the human-readable count, keyed by the day cell id.
    tip_counts = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        text = tip.get_text(" ", strip=True)
        m = _COUNT_RE.search(text)
        tip_counts[target] = int(m.group(1).replace(",", "")) if m else 0

    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        d = td.get("data-date")
        if not d:
            continue
        level = int(td.get("data-level", 0) or 0)
        cid = td.get("id")
        count = tip_counts.get(cid)
        if count is None:
            # Fallbacks for older/alt markup.
            if td.has_attr("data-count"):
                count = int(td["data-count"])
            else:
                m = _COUNT_RE.search(td.get("aria-label", "") or "")
                count = int(m.group(1).replace(",", "")) if m else 0
        weekday = datetime.strptime(d, "%Y-%m-%d").date().weekday()  # Mon=0
        days.append({"date": d, "count": count, "level": level, "weekday": weekday})

    days.sort(key=lambda x: x["date"])
    return days


def compute_stats(days):
    total = sum(d["count"] for d in days)

    # Streaks (counting days with >=1 contribution).
    longest = cur = 0
    for d in days:
        if d["count"] > 0:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    # Current streak = trailing run ending today (or yesterday if today empty).
    current = 0
    today = date.today().isoformat()
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["count"] > 0:
            current += 1
        elif d["date"] == today:
            # today may simply be unfinished; keep looking back
            continue
        else:
            break

    best = max(days, key=lambda x: x["count"], default={"date": None, "count": 0})

    monthly = OrderedDict()
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]

    # Neon top-end threshold (level 5) for standout days.
    nonzero = sorted(d["count"] for d in days if d["count"] > 0)
    if nonzero:
        p = nonzero[min(len(nonzero) - 1, int(len(nonzero) * 0.98))]
        top_threshold = max(10, p)
    else:
        top_threshold = 10**9

    return {
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "top_threshold": top_threshold,
    }


def main() -> None:
    username = os.environ.get("GH_USERNAME", DEFAULT_USERNAME)
    print(f"fetching contributions for {username} ...")
    html = fetch_html(username)
    days = parse_days(html)
    if not days:
        raise SystemExit("no day cells parsed -- GitHub markup may have changed")

    stats = compute_stats(days)
    payload = {
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "stats": stats,
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT}  ({len(days)} days, {stats['total']} contributions)")


if __name__ == "__main__":
    main()
