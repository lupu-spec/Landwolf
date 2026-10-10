#!/usr/bin/env python3
"""Extract existing LandWolf wolf pixels; never redraw the logo.

Source: beta/web/assets/landwolf-logo.png, the flattened original image.
Output: transparent PNG with lettering excluded by a manually bounded mask.
The mask is intentionally conservative near letters that touch the artwork.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "beta/web/assets/landwolf-logo.png"
OUTPUT = ROOT / "beta/web/assets/landwolf-wolf-only.png"
REF_WIDTH = 2172
REF_HEIGHT = 724
AA = 3


def cubic(p0, p1, p2, p3, steps=28):
    return [
        (
            (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0]
            + 3 * (1 - t) * t * t * p2[0] + t ** 3 * p3[0],
            (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1]
            + 3 * (1 - t) * t * t * p2[1] + t ** 3 * p3[1],
        )
        for i in range(1, steps + 1)
        for t in [i / steps]
    ]


def quad(p0, p1, p2, steps=20):
    return [
        (
            (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
            (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1],
        )
        for i in range(1, steps + 1)
        for t in [i / steps]
    ]


def original_wolf_boundary():
    """Conservatively keep the ORIGINAL face and jaw, excluding wordmark."""
    p = (1525, 75)
    points = [p]

    def line(end):
        nonlocal p
        points.append(end)
        p = end

    def curve(c1, c2, end):
        nonlocal p
        points.extend(cubic(p, c1, c2, end))
        p = end

    def bend(c, end):
        nonlocal p
        points.extend(quad(p, c, end))
        p = end

    curve((1650, 100), (1800, 150), (1900, 225))
    curve((2000, 285), (2050, 345), (2080, 398))
    line((2155, 452))
    bend((2170, 466), (2130, 488))
    bend((2070, 520), (2020, 540))
    curve((1965, 575), (1920, 610), (1850, 680))
    bend((1835, 635), (1840, 603))
    curve((1810, 555), (1770, 510), (1740, 480))
    line((1835, 408))
    line((1850, 369))
    curve((1780, 360), (1720, 340), (1660, 310))
    curve((1600, 290), (1560, 230), (1525, 75))
    return points

def main():
    src = Image.open(SOURCE).convert("RGB")
    width, height = src.size
    sx = width / REF_WIDTH
    sy = height / REF_HEIGHT
    pts = [
        (round(x * sx * AA), round(y * sy * AA))
        for x, y in original_wolf_boundary()
    ]
    debug = src.copy()
    draw = ImageDraw.Draw(debug)
    for x in range(0, width, 200):
        draw.line((x, 0, x, height), fill=(185, 185, 185), width=2)
        draw.text((x + 4, 10), str(x), fill=(220, 0, 0))
    for y in range(0, height, 100):
        draw.line((0, y, width, y), fill=(185, 185, 185), width=2)
        draw.text((8, y + 4), str(y), fill=(220, 0, 0))
    draw.line([(int(x * sx), int(y * sy)) for x, y in original_wolf_boundary()] + [(int(1525 * sx), int(75 * sy))], fill=(255, 0, 0), width=5)
    debug.save(OUTPUT.with_name("landwolf-mask-debug.png"), optimize=True)
    boundary = Image.new("L", (width * AA, height * AA), 0)
    ImageDraw.Draw(boundary).polygon(pts, fill=255)
    boundary = boundary.resize((width, height), Image.Resampling.LANCZOS)
    ink = ImageOps.invert(src.convert("L"))
    alpha = ImageChops.multiply(ink, boundary)

    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    out.putalpha(alpha)
    bbox = out.getbbox()
    if bbox is None:
        raise ValueError("No visible wolf pixels found in masked image.")
    margin = 16
    left, top, right, bottom = bbox
    bbox = (
        max(0, left - margin), max(0, top - margin),
        min(width, right + margin), min(height, bottom + margin),
    )
    out = out.crop(bbox)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUTPUT, optimize=True)
    preview = Image.new("RGBA", out.size, "white")
    preview.alpha_composite(out)
    preview.convert("RGB").save(OUTPUT.with_name("landwolf-wolf-only-preview.png"), optimize=True)
    print("Alpha extrema:", out.getchannel("A").getextrema(), "Nonzero bbox:", bbox)
    print(f"Extracted {out.width}x{out.height} PNG: {OUTPUT}")


if __name__ == "__main__":
    main()
