#!/usr/bin/env python3
"""Validate the map's static assets against what the code actually asks for.

Catches the failure modes that are invisible until a user hits them: an
icon path that resolves to nothing, a POI sitting outside the map, a tile
pyramid missing the zoom level it advertises, or a deployment that has
drifted past Cloudflare Pages' limits.

Pure stdlib, no browser, no network. Exit code 1 on any error.

    python3 e2e/validate_assets.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
ASSETS = PUBLIC / "palworld"
TILES_SRC = ROOT / "tiles-src"
SRC = ROOT / "src" / "map"

# Cloudflare Pages deployment limits.
MAX_FILES = 20_000
MAX_FILE_BYTES = 25 * 1024 * 1024

# itch.io refuses an HTML5 zip with more files than this. It is far
# tighter than the Pages cap and is what forced the PMTiles packing, so it
# is the limit worth guarding.
MAX_ITCH_FILES = 1_000

# Declared in markerEcs.ts; a tile pyramid covers 0..256 units on both axes.
UNIT_SPAN = 256

errors: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_constants() -> tuple[float, float, float]:
    """Pull the game-to-unit transform out of markerEcs.ts.

    Parsed rather than duplicated: if someone retunes the projection, this
    script follows instead of silently validating against stale numbers.
    """
    s = read(SRC / "markerEcs.ts")
    out = []
    for name in ("MAIN_X0", "MAIN_Y0", "MAIN_S"):
        m = re.search(rf"const {name} = (-?\d+(?:\.\d+)?);", s)
        if not m:
            error(f"markerEcs.ts: cannot find constant {name}")
            return (0.0, 0.0, 1.0)
        out.append(float(m.group(1)))
    return out[0], out[1], out[2]


def game_to_units(gx: float, gy: float, x0: float, y0: float, s: float) -> tuple[float, float]:
    """Mirror of gameToUnits() in markerEcs.ts."""
    return (UNIT_SPAN * (gy - y0) / s, UNIT_SPAN * (1 - (gx - x0) / s))


def parse_kind_meta() -> dict[str, dict[str, object]]:
    """Extract KIND_META entries (icon path, minZoom) from markerEcs.ts."""
    s = read(SRC / "markerEcs.ts")
    body = re.search(r"KIND_META:[^=]*=\s*\{(.*?)\n\};", s, re.S)
    if not body:
        error("markerEcs.ts: cannot locate KIND_META")
        return {}
    meta: dict[str, dict[str, object]] = {}
    for m in re.finditer(r"(\w+):\s*\{(.*?)\}", body.group(1), re.S):
        name, chunk = m.group(1), m.group(2)
        icon = re.search(r"icon:\s*'([^']*)'", chunk)
        min_zoom = re.search(r"minZoom:\s*(\d+)", chunk)
        meta[name] = {
            "icon": icon.group(1) if icon else None,
            "minZoom": int(min_zoom.group(1)) if min_zoom else None,
        }
    return meta


def check_icons(meta: dict[str, dict[str, object]]) -> None:
    """Every icon a marker kind declares must exist on disk."""
    for kind, info in meta.items():
        icon = info["icon"]
        if not icon:
            # boss and player draw from live data, not a static icon.
            continue
        rel = str(icon).lstrip("/")
        if not (PUBLIC / rel).is_file():
            error(f"KIND_META[{kind}].icon -> {icon} does not exist")


def parse_world_bounds() -> tuple[float, float, float, float]:
    """Read worldBounds out of ReactPalworldMap.tsx.

    The map is not a single square: the base island and the wt-overlay
    region occupy different latitude bands, so a POI legitimately sits
    outside the base pyramid. Validating against the union avoids flagging
    real data as broken.
    """
    s = read(SRC / "ReactPalworldMap.tsx")
    m = re.search(
        r"worldBounds = L\.latLngBounds\(\[\s*\[(-?[\d.]+), (-?[\d.]+)\],\s*\[(-?[\d.]+), (-?[\d.]+)\]",
        s,
    )
    if not m:
        error("ReactPalworldMap.tsx: cannot parse worldBounds")
        return (-256.0, -256.0, 256.0, 256.0)
    lat1, lng1, lat2, lng2 = (float(g) for g in m.groups())
    return (min(lat1, lat2), min(lng1, lng2), max(lat1, lat2), max(lng1, lng2))


def point_xy(entry: object) -> tuple[float, float] | None:
    """Normalise a POI entry to (x, y).

    Entries come in three shapes: [x, y], [x, y, label] where the label is
    a biome name or an oil-rig level, and boss records keyed by name.
    """
    if isinstance(entry, dict):
        x, y = entry.get("x"), entry.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (float(x), float(y))
        return None
    if isinstance(entry, list) and len(entry) in (2, 3):
        x, y = entry[0], entry[1]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            return (float(x), float(y))
    return None


def check_pois(
    meta: dict[str, dict[str, object]],
    x0: float,
    y0: float,
    s: float,
    bounds: tuple[float, float, float, float],
) -> None:
    """POI categories must map to marker kinds and land inside the map."""
    pois = json.loads(read(SRC / "pois.json"))
    lat_min, lng_min, lat_max, lng_max = bounds

    for category in pois:
        if category not in meta:
            error(f"pois.json has category '{category}' with no KIND_META entry")

    live_only = {"player"}
    for kind in meta:
        if kind not in pois and kind not in live_only:
            warn(f"KIND_META has '{kind}' but pois.json has no entries for it")

    total = 0
    for category, points in pois.items():
        outside = 0
        for entry in points:
            total += 1
            xy = point_xy(entry)
            if xy is None:
                error(f"pois.json[{category}]: unrecognised entry shape {entry!r}")
                continue
            ux, uy = game_to_units(xy[0], xy[1], x0, y0, s)
            lat, lng = -uy, ux
            if not (lat_min <= lat <= lat_max and lng_min <= lng <= lng_max):
                outside += 1
        if outside:
            error(
                f"pois.json[{category}]: {outside}/{len(points)} points fall "
                f"outside worldBounds"
            )
    print(f"  pois: {total:,} across {len(pois)} categories")


def check_boss_icons() -> None:
    """Boss records name a palicon by key; a bad key is a silent 404."""
    pois = json.loads(read(SRC / "pois.json"))
    bosses = pois.get("boss", [])
    missing = []
    for b in bosses:
        if not isinstance(b, dict):
            error(f"pois.json[boss]: expected an object, got {b!r}")
            continue
        icon = b.get("icon")
        if not icon:
            error(f"pois.json[boss]: entry {b.get('name', '?')!r} has no icon")
            continue
        if not (ASSETS / "palicons" / f"{icon}.webp").is_file():
            missing.append(f"{b.get('name', '?')} -> palicons/{icon}.webp")
    for m in missing:
        error(f"boss icon missing: {m}")
    print(f"  bosses: {len(bosses)} records, {len(bosses) - len(missing)} icons resolve")


def check_pyramids() -> None:
    """Each source layer must cover the zooms the component declares."""
    s = read(SRC / "ReactPalworldMap.tsx")

    def num(name: str) -> int | None:
        m = re.search(rf"const {name} = (\d+);", s)
        return int(m.group(1)) if m else None

    max_zoom = num("MAX_ZOOM")
    pal_native = num("PAL_MAX_NATIVE_ZOOM")
    if max_zoom is None or pal_native is None:
        error("ReactPalworldMap.tsx: cannot read MAX_ZOOM / PAL_MAX_NATIVE_ZOOM")
        return

    for layer, native in (("tiles", pal_native), ("wt-overlay", max_zoom)):
        d = TILES_SRC / layer
        if not d.is_dir():
            error(f"missing tile source: tiles-src/{layer}")
            continue
        zooms = sorted(int(p.name) for p in d.iterdir() if p.is_dir() and p.name.isdigit())
        if not zooms:
            error(f"{layer}: no zoom directories")
            continue
        if native not in zooms:
            error(f"{layer}: declares native zoom {native} but only has {zooms}")
        missing = [z for z in range(min(zooms), native + 1) if z not in zooms]
        if missing:
            error(f"{layer}: gap in zoom levels {missing} (has {zooms})")


def check_archives() -> None:
    """The shipped archives must exist and be newer than their source.

    The loose tiles under tiles-src/ are the source of truth but are never
    served; public/ ships the packed archives. A stale archive means the
    map renders tiles that no longer match the source, which nothing else
    would catch.
    """
    for layer in ("tiles", "wt-overlay"):
        archive = ASSETS / f"{layer}.pmtiles"
        src = TILES_SRC / layer
        if not archive.is_file():
            error(
                f"{layer}.pmtiles is missing — run "
                f"tools/.venv/bin/python tools/build_pmtiles.py"
            )
            continue
        if not src.is_dir():
            continue
        newest = max((p.stat().st_mtime for p in src.rglob("*.webp")), default=0)
        if newest > archive.stat().st_mtime:
            error(
                f"{layer}.pmtiles is older than tiles-src/{layer} — "
                f"rebuild it with tools/build_pmtiles.py"
            )
        print(f"  {layer}.pmtiles: {archive.stat().st_size / 1e6:.1f} MB")


def check_limits() -> None:
    """Guard the Cloudflare Pages caps before a deploy discovers them."""
    files = [p for p in PUBLIC.rglob("*") if p.is_file()]
    if len(files) > MAX_ITCH_FILES:
        error(
            f"public/ has {len(files):,} files, over itch's {MAX_ITCH_FILES:,} "
            f"cap — the build will upload but itch will refuse to process it"
        )
    elif len(files) > MAX_ITCH_FILES * 0.8:
        warn(f"public/ has {len(files):,} files, past 80% of itch's {MAX_ITCH_FILES:,} cap")
    if len(files) > MAX_FILES:
        error(f"public/ has {len(files):,} files, over the {MAX_FILES:,} Pages cap")

    for p in files:
        size = p.stat().st_size
        if size > MAX_FILE_BYTES:
            error(f"{p.relative_to(ROOT)} is {size / 1e6:.1f} MB, over the 25 MiB per-file cap")


def report_duplicates() -> None:
    """Informational: blank tiles repeat heavily and PMTiles would dedupe them."""
    for layer in ("tiles", "wt-overlay"):
        d = TILES_SRC / layer
        if not d.is_dir():
            continue
        seen: dict[str, int] = defaultdict(int)
        total = 0
        for p in d.rglob("*.webp"):
            seen[hashlib.sha1(p.read_bytes()).hexdigest()] += 1
            total += 1
        dupes = sum(n - 1 for n in seen.values() if n > 1)
        if total:
            print(f"  {layer}: {total:,} tiles, {len(seen):,} unique, {dupes:,} duplicates")


def main() -> int:
    if not ASSETS.is_dir():
        print(f"error: {ASSETS} not found", file=sys.stderr)
        return 1

    x0, y0, s = parse_constants()
    meta = parse_kind_meta()

    bounds = parse_world_bounds()

    print("data:")
    check_icons(meta)
    check_pois(meta, x0, y0, s, bounds)
    check_boss_icons()
    check_pyramids()
    print("archives:")
    check_archives()
    check_limits()

    print("tile stats:")
    report_duplicates()

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        return 1
    print(f"\nok — {len(meta)} marker kinds validated, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
