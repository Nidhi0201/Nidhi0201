#!/usr/bin/env python3
"""Render data/contributions.json as an animated 53-week contribution heatmap.

Rounded, colored boxes on a GitHub-ish green ramp. The grid reveals once with a
diagonal, line-after-line slide-down (CSS keyframes that play on load then
freeze -- no looping glow), plus a Less->More legend and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py   # writes contrib-heatmap.svg
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "contributions.json"
OUT = Path(__file__).resolve().parent.parent / "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32",
           "#26a641", "#39d353", "#69f0a0"]
#          none -> brightest (level 5 is a neon top end)

BG = "#0d1117"
TEXT = "#c9d1d9"
DIM = "#8b949e"

BOX = 11
GAP = 3
STEP = BOX + GAP
LEFT = 30      # room for weekday labels
TOP = 30       # room for month labels
PAD = 16
FOOTER = 34

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # row idx (Sun=0) -> label


def gh_weekday(d: datetime) -> int:
    """GitHub grid row: Sunday=0 .. Saturday=6."""
    return (d.weekday() + 1) % 7


def build_cells(days, top_threshold):
    first = datetime.strptime(days[0]["date"], "%Y-%m-%d")
    first_sunday = first - timedelta(days=gh_weekday(first))

    cells = []
    max_col = 0
    for day in days:
        d = datetime.strptime(day["date"], "%Y-%m-%d")
        col = (d - first_sunday).days // 7
        row = gh_weekday(d)
        level = day["level"]
        if day["count"] >= top_threshold and level >= 4:
            level = 5
        cells.append({"col": col, "row": row, "level": level,
                      "count": day["count"], "month": d.month, "date": day["date"]})
        max_col = max(max_col, col)
    return cells, max_col


def month_labels(cells, max_col):
    """Return list of (col, 'Mon') where a new month first appears."""
    first_month_at = {}
    for c in cells:
        first_month_at.setdefault(c["col"], c["month"])
    labels = []
    last = None
    for col in range(max_col + 1):
        m = first_month_at.get(col)
        if m and m != last:
            labels.append((col, MONTHS[m - 1]))
            last = m
    return labels


def build_svg(payload) -> str:
    days = payload["days"]
    stats = payload["stats"]
    cells, max_col = build_cells(days, stats.get("top_threshold", 10**9))

    grid_w = (max_col + 1) * STEP
    width = LEFT + grid_w + PAD
    height = TOP + 7 * STEP + FOOTER

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="\'SFMono-Regular\',Consolas,\'Liberation Mono\',Menlo,monospace" '
        f'font-size="10">',
        # Grid reveals once, diagonal slide-down, then freezes (fill mode both).
        "<style>"
        "@keyframes reveal{from{opacity:0;transform:translateY(-6px)}"
        "to{opacity:1;transform:translateY(0)}}"
        ".box{opacity:0;transform-box:fill-box;animation:reveal .5s ease-out both}"
        ".fade{opacity:0;animation:reveal .6s ease-out both}"
        "</style>",
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
    ]

    # Month labels.
    for col, label in month_labels(cells, max_col):
        x = LEFT + col * STEP
        parts.append(f'<text x="{x}" y="{TOP - 8}" fill="{DIM}">{label}</text>')

    # Weekday labels.
    for row, label in WEEKDAY_LABELS.items():
        y = TOP + row * STEP + BOX - 1
        parts.append(f'<text x="0" y="{y}" fill="{DIM}">{label}</text>')

    # Day boxes.
    for c in cells:
        x = LEFT + c["col"] * STEP
        y = TOP + c["row"] * STEP
        delay = (c["col"] + c["row"]) * 0.012
        fill = PALETTE[c["level"]]
        parts.append(
            f'<rect class="box" x="{x}" y="{y}" width="{BOX}" height="{BOX}" '
            f'rx="2" fill="{fill}" style="animation-delay:{delay:.3f}s"/>'
        )

    # Footer: stats (left) + Less->More legend (right).
    fy = TOP + 7 * STEP + 20
    total = stats["total"]
    cur = stats["current_streak"]
    longest = stats["longest_streak"]
    footer_text = (
        f"{total:,} contributions in the last year   \u00b7   "
        f"current streak {cur}d   \u00b7   longest {longest}d"
    )
    parts.append(
        f'<text class="fade" x="{LEFT}" y="{fy}" fill="{TEXT}" '
        f'style="animation-delay:1.1s">{footer_text}</text>'
    )

    # Legend.
    legend_boxes = 5
    legend_w = 60 + legend_boxes * (BOX + 2) + 34
    lx = width - PAD - legend_w
    parts.append(
        f'<text class="fade" x="{lx}" y="{fy}" fill="{DIM}" '
        f'style="animation-delay:1.2s">Less</text>'
    )
    bx = lx + 32
    for i in range(legend_boxes):
        parts.append(
            f'<rect class="fade" x="{bx + i * (BOX + 2)}" y="{fy - BOX + 1}" '
            f'width="{BOX}" height="{BOX}" rx="2" fill="{PALETTE[i]}" '
            f'style="animation-delay:{1.2 + i * 0.05:.2f}s"/>'
        )
    parts.append(
        f'<text class="fade" x="{bx + legend_boxes * (BOX + 2) + 4}" y="{fy}" '
        f'fill="{DIM}" style="animation-delay:1.5s">More</text>'
    )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.write_text(build_svg(payload), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
