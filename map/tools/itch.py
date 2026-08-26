#!/usr/bin/env python3
"""Generate itch.io store images from the map's own tiles.

itch wants a 630x500 cover and, optionally, a wide banner. Rather than
maintaining hand-made art that drifts from the map, this stitches the
real tile pyramid into a mosaic and crops it to the sizes itch asks for —
so the store page always shows the map as it currently is.

    python3 tools/itch.py                 # cover + banner into tools/out
    python3 tools/itch.py --zoom 5        # sharper source, slower
    python3 tools/itch.py --layer tiles   # base layer only (default)

Requires Pillow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
TILES = ROOT / "public" / "palworld"
TILE_PX = 256

# itch.io store image sizes.
COVER = (630, 500)
BANNER = (1920, 620)


def load_grid(layer: Path, zoom: int) -> dict[tuple[int, int], Path]:
    """Map (x, y) -> tile path for one zoom level.

    Tile coordinates can be negative, so the grid is keyed by the raw
    values and normalised only when compositing.
    """
    z = layer / str(zoom)
    if not z.is_dir():
        avail = sorted(p.name for p in layer.iterdir() if p.is_dir())
        sys.exit(f"zoom {zoom} not found in {layer.name}; have {avail}")

    grid: dict[tuple[int, int], Path] = {}
    for xdir in z.iterdir():
        if not xdir.is_dir():
            continue
        try:
            x = int(xdir.name)
        except ValueError:
            continue
        for tile in xdir.glob("*.webp"):
            try:
                y = int(tile.stem)
            except ValueError:
                continue
            grid[(x, y)] = tile
    if not grid:
        sys.exit(f"no tiles under {z}")
    return grid


def stitch(grid: dict[tuple[int, int], Path]) -> Image.Image:
    """Composite a tile grid into one image."""
    xs = [x for x, _ in grid]
    ys = [y for _, y in grid]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w = (x1 - x0 + 1) * TILE_PX
    h = (y1 - y0 + 1) * TILE_PX

    canvas = Image.new("RGBA", (w, h), (11, 20, 32, 255))
    for (x, y), path in grid.items():
        with Image.open(path) as im:
            tile = im.convert("RGBA")
            canvas.alpha_composite(tile, ((x - x0) * TILE_PX, (y - y0) * TILE_PX))
    return canvas


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Cover-fit: scale to fill, then centre-crop to the exact size."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    w, h = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    resized = img.resize((w, h), Image.LANCZOS)
    left = (w - tw) // 2
    top = (h - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer", default="tiles", help="tile layer (default: tiles)")
    ap.add_argument("--zoom", type=int, default=4, help="source zoom (default: 4)")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    args = ap.parse_args()

    layer = TILES / args.layer
    if not layer.is_dir():
        sys.exit(f"no such layer: {layer}")

    grid = load_grid(layer, args.zoom)
    print(f"{args.layer} z{args.zoom}: {len(grid)} tiles")

    # No cropping pass: the pyramid is already tight around the playable
    # area — the surrounding ocean is inside the map boundary, not margin.
    full = stitch(grid)
    print(f"stitched: {full.width}x{full.height}")

    args.out.mkdir(parents=True, exist_ok=True)
    for name, size in (("cover", COVER), ("banner", BANNER)):
        out = args.out / f"{name}.png"
        fit(full, size).convert("RGB").save(out, optimize=True)
        print(f"  {out.relative_to(ROOT)}  {size[0]}x{size[1]}  {out.stat().st_size / 1024:.0f} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
