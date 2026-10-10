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
REF_WIDTH = 2048
REF_HEIGHT = 683
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
    """Noncreative mask: only select source pixels outside the wordmark."""
    p = (1438, 70)
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

    curve((1510, 80), (1637, 124), (1738, 185))
    curve((1854, 233), (1934, 318), (1948, 381))
    line((2024, 428))
    bend((2043, 445), (2004, 470))
    bend((1970, 486), (1918, 509))
    curve((1865, 547), (1840, 570), (1801, 597))
    line((1742, 643))
    bend((1734, 601), (1737, 570))
    curve((1733, 548), (1711, 511), (1702, 474))
    line((1748, 419))
    line((1760, 343))
    curve((1720, 335), (1655, 322), (1583, 288))
    curve((1511, 261), (1429, 242), (1332, 229))
    line((1320, 171))
    curve((1376, 171), (1404, 148), (1435, 134))
    line((1438, 70))
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
