#!/usr/bin/env python3
"""Pack the tile pyramids into PMTiles archives.

itch.io caps an HTML5 project at 1000 files and the pyramids are 10,632
of them, so the map cannot ship as loose tiles. PMTiles stores a whole
pyramid in one file that the client reads with HTTP range requests, which
takes dist/ from ~10,740 files to a few hundred.

    tools/.venv/bin/python tools/build_pmtiles.py

Reads tiles-src/<layer>/ and writes public/palworld/<layer>.pmtiles. The
loose tiles are the source of truth and deliberately live outside public/
so they are never copied into a build.

The base layer is a standard XYZ pyramid. The overlay is a sparse region
that sits at negative tile coordinates, which PMTiles cannot address, so
each zoom is shifted to a non-negative origin and the shift is recorded
in the archive metadata for the client to undo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".venv" / "lib"))

try:
    from pmtiles.tile import Compression, TileType, zxy_to_tileid
    from pmtiles.writer import Writer
except ImportError:
    sys.exit(
        "pmtiles is missing. Create the venv first:\n"
        "  python3 -m venv tools/.venv && tools/.venv/bin/pip install pmtiles"
    )

ROOT = Path(__file__).resolve().parent.parent
# Loose tiles are source and stay out of public/, or vite would copy all
# ~10,600 of them into dist and blow past itch's 1000-file cap — the whole
# reason these archives exist.
SRC = ROOT / "tiles-src"
DEST = ROOT / "public" / "palworld"
LAYERS = ("tiles", "wt-overlay")

# Whole-world bounds in the e7 fixed-point form PMTiles headers use. The
# map is a game world on CRS.Simple, not geography, so these are just a
# valid envelope rather than meaningful coordinates.
E7 = 10_000_000


def collect(layer: Path) -> dict[int, dict[tuple[int, int], Path]]:
    """Gather tiles per zoom level."""
    out: dict[int, dict[tuple[int, int], Path]] = defaultdict(dict)
    for zdir in layer.iterdir():
        if not zdir.is_dir() or not zdir.name.isdigit():
            continue
        z = int(zdir.name)
        for xdir in zdir.iterdir():
            if not xdir.is_dir():
                continue
            try:
                x = int(xdir.name)
            except ValueError:
                continue
            for tile in xdir.glob("*.webp"):
                try:
                    out[z][(x, int(tile.stem))] = tile
                except ValueError:
                    continue
    return out


def source_hash(layer: Path) -> str:
    """Content hash of every source tile in a layer.

    Covers all tiles, including zoom levels the archive drops, so the
    check answers "does this archive correspond to the current source"
    rather than "does it match the subset that happened to be packed".

    Freshness cannot be judged by mtime: git does not preserve it, so a
    fresh checkout gives every file the same timestamp in arbitrary order.
    Hashing the bytes is the only check that survives a clone.
    """
    h = hashlib.sha256()
    for p in sorted(layer.rglob("*.webp"), key=lambda p: p.relative_to(layer).as_posix()):
        h.update(p.relative_to(layer).as_posix().encode())
        h.update(hashlib.sha1(p.read_bytes()).digest())
    return h.hexdigest()


def build(layer_name: str, dest: Path) -> dict[str, object]:
    layer = SRC / layer_name
    if not layer.is_dir():
        sys.exit(f"no such layer: {layer}")

    by_zoom = collect(layer)
    if not by_zoom:
        sys.exit(f"no tiles found under {layer}")

    # Shift each zoom so the lowest coordinate lands on zero. Layers that
    # are already standard XYZ get a zero shift and are untouched.
    #
    # A zoom whose extent is wider than the grid at that level cannot be
    # addressed no matter how it is shifted — the overlay's z0 spans two
    # tiles where zoom 0 has room for one. Those levels are dropped and
    # the client renders them by upscaling the nearest packed zoom, which
    # is what Leaflet's minNativeZoom does anyway.
    offsets: dict[str, list[int]] = {}
    skipped: list[str] = []
    for z in sorted(by_zoom):
        tiles = by_zoom[z]
        xs = [x for x, _ in tiles]
        ys = [y for _, y in tiles]
        limit = 1 << z
        if (max(xs) - min(xs) + 1) > limit or (max(ys) - min(ys) + 1) > limit:
            skipped.append(f"z{z} ({len(tiles)} tiles)")
            continue
        offsets[str(z)] = [min(0, min(xs)), min(0, min(ys))]

    by_zoom = {z: t for z, t in by_zoom.items() if str(z) in offsets}
    if not by_zoom:
        sys.exit(f"{layer_name}: no zoom level fits a PMTiles grid")

    entries: list[tuple[int, Path]] = []
    for z, tiles in by_zoom.items():
        off_x, off_y = offsets[str(z)]
        for (x, y), path in tiles.items():
            sx, sy = x - off_x, y - off_y
            limit = 1 << z
            if not (0 <= sx < limit and 0 <= sy < limit):
                sys.exit(
                    f"{layer_name} z{z}: tile ({x},{y}) shifts to ({sx},{sy}), "
                    f"outside the 0..{limit - 1} range PMTiles can address"
                )
            entries.append((zxy_to_tileid(z, sx, sy), path))

    # write_tile expects ascending tile ids to produce a clustered archive.
    entries.sort(key=lambda e: e[0])

    with open(dest, "wb") as f:
        writer = Writer(f)
        for tile_id, path in entries:
            writer.write_tile(tile_id, path.read_bytes())

        metadata = {
            "name": layer_name,
            "type": "baselayer" if layer_name == "tiles" else "overlay",
            "format": "webp",
            "tile_size": 256,
            # The client adds these back before looking a tile up.
            "kbve:offsets": offsets,
            "kbve:minzoom": min(by_zoom),
            "kbve:maxzoom": max(by_zoom),
        }
        writer.finalize(
            {
                "tile_type": TileType.WEBP,
                "tile_compression": Compression.NONE,
                "min_lon_e7": -180 * E7,
                "min_lat_e7": -85 * E7,
                "max_lon_e7": 180 * E7,
                "max_lat_e7": 85 * E7,
                "center_lon_e7": 0,
                "center_lat_e7": 0,
                "center_zoom": min(by_zoom),
            },
            metadata,
        )

    zooms = sorted(by_zoom)
    return {
        "layer": layer_name,
        "source_hash": source_hash(layer),
        "tiles": len(entries),
        "zooms": f"z{zooms[0]}..z{zooms[-1]}",
        "bytes": dest.stat().st_size,
        "shifted": {z: o for z, o in offsets.items() if o != [0, 0]},
        "skipped": skipped,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer", choices=LAYERS, help="only build one layer")
    args = ap.parse_args()

    lock_path = Path(__file__).parent / "pmtiles.lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.is_file() else {}

    for name in [args.layer] if args.layer else LAYERS:
        dest = DEST / f"{name}.pmtiles"
        info = build(name, dest)
        lock[name] = {
            "source_hash": info["source_hash"],
            "tiles": info["tiles"],
            "bytes": info["bytes"],
        }
        print(
            f"{info['layer']:11} {info['tiles']:>6} tiles  {info['zooms']:9} "
            f"-> {dest.name}  {info['bytes'] / 1e6:.1f} MB"
        )
        if info["shifted"]:
            print(f"            shifted: {info['shifted']}")
        if info["skipped"]:
            print(f"            skipped (too wide for the grid): {', '.join(info['skipped'])}")

    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(f"wrote {lock_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
