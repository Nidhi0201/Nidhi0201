#!/usr/bin/env python3
"""Convert a prepped grayscale photo into a self-typing monochrome ASCII SVG.

Reads scripts/source-prepped.png (produced by prep_photo.py). If that file is
missing, a procedurally shaded bust silhouette is used instead so the pipeline
always produces a clean placeholder portrait.

Each row is revealed with a left-to-right wipe (a small block cursor rides the
wipe edge), staggered top to bottom. The whole portrait prints once and
freezes -- no looping. Motion is pure SMIL so GitHub renders it inside <img>.

Usage:
    python scripts/make_ascii_svg.py            # writes avi-ascii.svg
"""
import math
from pathlib import Path

RAMP = " .`:-=+*cs#%@"   # bright (sparse) -> dark (dense)
#        ^ leading space clears the background to nothing

COLS = 100
ROWS = 53

# SVG cell metrics (monospace).
CW = 6.0     # character advance width
CH = 11.0    # line height
FONT_SIZE = 10
FILL = "#c9d1d9"      # one light-gray fill -- monochrome on purpose
CURSOR = "#39d353"    # block cursor riding the wipe edge

# Animation timing.
STAGGER = 0.055       # delay between consecutive rows (s)
ROW_DUR = 0.45        # wipe duration per row (s)

PREPPED = Path(__file__).with_name("source-prepped.png")
MASK = Path(__file__).with_name("source-mask.png")
OUT = Path(__file__).resolve().parent.parent / "avi-ascii.svg"

# Silhouette fill: subject renders as one uniform density (no facial features);
# anti-aliased edges ride the lighter end of the ramp for a clean outline.
SIL_DARK = 40      # interior value -> dense glyph
SIL_EDGE = 210     # faint edge value -> sparse glyph


def load_values_from_image():
    """Return ROWS x COLS grayscale values (0..255) from the prepped photo.

    Fits the subject into the grid preserving aspect ratio (accounting for the
    non-square character cell), then centers it on a white field so padding maps
    to spaces rather than stretching the face.
    """
    from PIL import Image, ImageFilter

    img = Image.open(PREPPED).convert("L")
    w, h = img.size
    box_w, box_h = COLS * CW, ROWS * CH
    scale = min(box_w / w, box_h / h)
    cols_used = max(1, min(COLS, round(w * scale / CW)))
    rows_used = max(1, min(ROWS, round(h * scale / CH)))

    # Blur before downsampling so fine facial features (eyes, teeth, mouth)
    # dissolve into smooth tone -- a clean likeness, not an uncanny expression.
    blur_radius = max(1.0, (w / cols_used) * 0.9)
    img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    resized = img.resize((cols_used, rows_used), Image.LANCZOS)
    # A second gentle blur on the small grid smooths cell-to-cell speckle.
    resized = resized.filter(ImageFilter.GaussianBlur(radius=0.6))
    px = resized.load()

    col_off = (COLS - cols_used) // 2
    row_off = (ROWS - rows_used) // 2
    grid = [[255] * COLS for _ in range(ROWS)]
    for r in range(rows_used):
        for c in range(cols_used):
            grid[row_off + r][col_off + c] = px[c, r]
    return grid


def load_values_from_mask():
    """Render a featureless silhouette from the subject mask.

    Subject area maps to a single uniform density; anti-aliased edges map to
    lighter glyphs so the outline stays clean. No facial features at all.
    """
    from PIL import Image, ImageFilter

    mask = Image.open(MASK).convert("L")
    w, h = mask.size
    box_w, box_h = COLS * CW, ROWS * CH
    scale = min(box_w / w, box_h / h)
    cols_used = max(1, min(COLS, round(w * scale / CW)))
    rows_used = max(1, min(ROWS, round(h * scale / CH)))

    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(1.0, (w / cols_used) * 0.5)))
    resized = mask.resize((cols_used, rows_used), Image.LANCZOS)
    px = resized.load()

    col_off = (COLS - cols_used) // 2
    row_off = (ROWS - rows_used) // 2
    grid = [[255] * COLS for _ in range(ROWS)]
    for r in range(rows_used):
        for c in range(cols_used):
            a = px[c, r] / 255.0          # 1 = solid subject, 0 = background
            if a <= 0.12:
                continue                   # background -> space
            # Uniform interior; only the soft edge fades toward sparse glyphs.
            value = SIL_EDGE - a * (SIL_EDGE - SIL_DARK)
            grid[row_off + r][col_off + c] = int(max(0, min(255, value)))
    return grid


def synth_placeholder():
    """Procedurally shade a bust silhouette -> ROWS x COLS values (0..255).

    Pure-python (no numpy) so it runs anywhere. A sphere-shaded head plus
    shoulders gives the ASCII ramp real highlights and shadows.
    """
    # Light direction (upper-left, toward viewer), normalized.
    lx, ly, lz = -0.4, -0.55, 0.73
    lm = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / lm, ly / lm, lz / lm

    hx, hy, rx, ry = 0.50, 0.34, 0.19, 0.25   # head ellipse
    out = []
    for r in range(ROWS):
        y = r / (ROWS - 1)
        row = []
        for c in range(COLS):
            x = c / (COLS - 1)
            v = 255.0  # white background

            # Head (shaded sphere).
            nx = (x - hx) / rx
            ny = (y - hy) / ry
            d2 = nx * nx + ny * ny
            if d2 <= 1.0:
                nz = math.sqrt(1.0 - d2)
                intensity = max(0.0, nx * lx + ny * ly + nz * lz)
                v = 55.0 + intensity * 175.0

            # Shoulders / bust (a broad ellipse below the head).
            sx = (x - 0.5) / 0.42
            sy = (y - 1.02) / 0.42
            if sx * sx + sy * sy <= 1.0 and y > hy + ry * 0.55:
                shade = 120.0 - (y - 0.6) * 90.0 - (x - 0.5) * 60.0
                v = min(v, max(45.0, shade))

            # Neck.
            if 0.42 < x < 0.58 and hy + ry * 0.6 < y < 0.66:
                v = min(v, 95.0)

            row.append(int(max(0, min(255, v))))
        out.append(row)
    return out


def to_glyph(value: int) -> str:
    """Map a 0..255 brightness to a ramp glyph (white -> space)."""
    idx = int(round((1.0 - value / 255.0) * (len(RAMP) - 1)))
    return RAMP[max(0, min(len(RAMP) - 1, idx))]


def xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(grid) -> str:
    width = COLS * CW
    height = ROWS * CH + 6
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" '
        f'font-family="\'SFMono-Regular\',Consolas,\'Liberation Mono\',Menlo,monospace" '
        f'font-size="{FONT_SIZE}">',
        f'<rect width="100%" height="100%" fill="#0d1117"/>',
        "<defs>",
    ]

    # One wipe clip per row.
    for r in range(ROWS):
        delay = r * STAGGER
        y = r * CH + 3
        parts.append(
            f'<clipPath id="cp{r}"><rect x="0" y="{y:.1f}" width="0" height="{CH:.1f}">'
            f'<animate attributeName="width" from="0" to="{width:.0f}" '
            f'dur="{ROW_DUR}s" begin="{delay:.3f}s" fill="freeze"/></rect></clipPath>'
        )
    parts.append("</defs>")

    # Rows: clipped text + a block cursor riding the wipe edge.
    for r in range(ROWS):
        delay = r * STAGGER
        baseline = r * CH + 3 + FONT_SIZE - 1
        line = "".join(to_glyph(v) for v in grid[r])
        parts.append(
            f'<g clip-path="url(#cp{r})">'
            f'<text x="0" y="{baseline:.1f}" xml:space="preserve" fill="{FILL}">'
            f"{xml_escape(line)}</text></g>"
        )
        cy = r * CH + 4
        parts.append(
            f'<rect x="0" y="{cy:.1f}" width="{CW:.1f}" height="{CH - 2:.1f}" '
            f'fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.9;0.9;0" '
            f'keyTimes="0;0.02;0.98;1" dur="{ROW_DUR}s" begin="{delay:.3f}s" fill="freeze"/>'
            f'<animate attributeName="x" from="0" to="{width - CW:.1f}" '
            f'dur="{ROW_DUR}s" begin="{delay:.3f}s" fill="freeze"/></rect>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    if MASK.exists():
        print(f"using subject mask: {MASK.name} (featureless silhouette)")
        grid = load_values_from_mask()
    elif PREPPED.exists():
        print(f"using prepped photo: {PREPPED.name}")
        grid = load_values_from_image()
    else:
        print("no source-prepped.png found -> generating placeholder portrait")
        grid = synth_placeholder()

    OUT.write_text(build_svg(grid), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
