#!/usr/bin/env python3
"""Hand-author a neofetch-style info card SVG that prints line by line.

Edit CONTENT below to tell your story -- keep GitHub stats out of here (the
contribution graph already covers those); this card is for the things numbers
can't say.

Set STATIC=1 to emit a frozen frame (handy for local Quick Look previews):
    STATIC=1 python scripts/make_info_card.py

Usage:
    python scripts/make_info_card.py   # writes info-card.svg
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# EDIT ME: your story. Labels are colored, values are light gray.
# ---------------------------------------------------------------------------
USER = "nidhi"
HOST = "github"
CONTENT = [
    ("Name",       "Nidhi Prajapati"),
    ("Location",   "Hayward, CA"),
    ("Now",        "Full-stack + AI/ML engineer"),
    ("Stack",      "Python \u00b7 FastAPI \u00b7 React \u00b7 Next.js"),
    ("Also",       "LangGraph \u00b7 Java \u00b7 ASP.NET \u00b7 scikit-learn"),
    ("Building",   "AI CRM \u00b7 Resume Reviewer Agent \u00b7 devflow-ai"),
    ("Community",  "HackHayward organizer"),
    ("Motto",      "Always learning, always building"),
]
# ---------------------------------------------------------------------------

OUT = Path(__file__).resolve().parent.parent / "info-card.svg"

# Palette.
BG = "#0d1117"
FRAME = "#30363d"
FG = "#c9d1d9"
ACCENT = "#39d353"     # user@host + labels
DIM = "#8b949e"
BLOCKS = ["#ff7b72", "#d29922", "#39d353", "#58a6ff", "#bc8cff", "#39c5cf"]

# Metrics.
PAD = 22
LH = 26
FS = 14
LABEL_W = 132

STATIC = os.environ.get("STATIC") == "1"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line(idx, y, inner, delay):
    """Wrap one row in a fade + slide-in group (or a frozen group if STATIC)."""
    if STATIC:
        return f'<g transform="translate({PAD},{y})">{inner}</g>'
    return (
        f'<g transform="translate({PAD - 8},{y})" opacity="0">'
        f'<animate attributeName="opacity" from="0" to="1" dur="0.35s" '
        f'begin="{delay:.2f}s" fill="freeze"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'from="{PAD - 8},{y}" to="{PAD},{y}" dur="0.35s" begin="{delay:.2f}s" '
        f'fill="freeze"/>'
        f"{inner}</g>"
    )


def build_svg() -> str:
    rows = len(CONTENT)
    width = 640
    # title + rule + rows + palette
    height = PAD * 2 + LH * (rows + 3) + 8
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="\'SFMono-Regular\',Consolas,\'Liberation Mono\',Menlo,monospace" '
        f'font-size="{FS}">',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        f'fill="{BG}" stroke="{FRAME}"/>',
    ]

    y = PAD + FS
    delay = 0.0
    step = 0.18

    # Title: user@host
    title = (
        f'<text x="0" y="0" fill="{ACCENT}" font-weight="bold">'
        f'{esc(USER)}<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{ACCENT}" font-weight="bold">{esc(HOST)}</tspan></text>'
    )
    parts.append(line(0, y, title, delay))
    y += LH
    delay += step

    # Separator rule (dashes).
    dashes = "-" * 40
    parts.append(line(1, y, f'<text x="0" y="0" fill="{DIM}">{dashes}</text>', delay))
    y += LH
    delay += step

    # Key/value rows.
    for label, value in CONTENT:
        inner = (
            f'<text x="0" y="0" fill="{ACCENT}" font-weight="bold">{esc(label)}</text>'
            f'<text x="{LABEL_W}" y="0" fill="{DIM}">:</text>'
            f'<text x="{LABEL_W + 14}" y="0" fill="{FG}">{esc(value)}</text>'
        )
        parts.append(line(2, y, inner, delay))
        y += LH
        delay += step

    # neofetch color blocks.
    y += 6
    block = 18
    gap = 6
    blocks = []
    for i, col in enumerate(BLOCKS):
        bx = i * (block + gap)
        blocks.append(
            f'<rect x="{bx}" y="{-block + 4}" width="{block}" height="{block}" '
            f'rx="3" fill="{col}"/>'
        )
    parts.append(line(3, y, "".join(blocks), delay))

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    OUT.write_text(build_svg(), encoding="utf-8")
    mode = "static" if STATIC else "animated"
    print(f"wrote {OUT} ({mode})")


if __name__ == "__main__":
    main()
