# AGENTS.md — Palworld Map

Scoped to `map/`. Repo-wide rules live in the root `AGENTS.md`.

Interactive map for the KBVE Palworld gameserver, embedded into
`kbve.com`. Scope: the tile pyramids, map icons, and the app that renders
them. Nothing else.

## Layout

```
tiles-src/tiles/             base tile pyramid, source (XYZ, z0..z6)
tiles-src/wt-overlay/        overlay tile pyramid, source (z0..z8)
public/palworld/*.pmtiles    the packed archives that actually ship
public/palworld/palicons/    item / creature icons
public/palworld/ui/          map chrome
src/map/                     ported map component + marker ECS + live poller
src/events.ts                local event bus (replaces @kbve/droid)
src/main.tsx                 standalone entry
```

## Rules

**Tiles ship as PMTiles archives, never as loose files.** itch.io refuses
an HTML5 project with more than 1000 files and the two pyramids are
~10,600 of them — the first publish uploaded fine and itch rejected the
zip on processing. Loose tiles live in `tiles-src/`, deliberately outside
`public/` so vite cannot copy them into a build. After changing them run:

    tools/.venv/bin/python tools/build_pmtiles.py

`pnpm validate` fails if an archive is older than its source, so a stale
archive cannot ship silently.

The overlay sits at negative tile coordinates, which PMTiles cannot
address, so each zoom is shifted to a non-negative origin and the shift is
stored in the archive metadata for `src/map/pmtilesLayer.ts` to undo. Its
z0 spans two tiles where zoom 0 holds one, so that level is dropped and
Leaflet upscales z1 via `minNativeZoom`.

**Tiles are generated output — never hand-edit them.** A tile pyramid is
derived from a source image. If a tile is wrong, the source or the
generation step is wrong. Regenerate the affected zoom levels; do not
patch individual `.webp` files.

**Deep links are the feature.** The map must encode position and zoom in
the URL hash (`#/lat/lng/z`) so a view can be pasted into Discord. This is
the main distribution loop, and it is the one thing an iframe embed makes
harder — do not let it regress.

**Watch the file count.** `dist/` is ~105 files against itch's cap of
1000; Pages allows 20,000. Anything that puts many files into `public/`
threatens the itch build, which is the tighter of the two.

**Live gameserver state comes from the API, not the build.** Player
counts, base locations, and server status are fetched at runtime from
`api.kbve.com` (cross-origin, CORS). Never bake them into tiles or a
static JSON in this repo.

**No game builds here.** This is a map, not a playable build. Anything
with a wasm/engine export ships to itch instead.

## Validating

`pnpm validate` (`e2e/validate_assets.py`, stdlib only) checks the static
assets against what the code actually asks for: every `KIND_META` icon and
every boss palicon resolves, POI coordinates land inside `worldBounds`,
each tile layer has the zoom levels the component declares, and the
deployment stays under the Pages caps.

It parses the projection constants and bounds out of the source rather
than duplicating them, so retuning the map updates the checks too. Run it
after touching tiles, icons, or `pois.json`.

`pnpm test:e2e` runs the Playwright suite for what only a browser can
answer: the map paints, tiles resolve from both pyramids with no 4xx, the
filter control renders, and live data drives the player count in both the
populated and offline directions.

Always stub the live endpoints with `page.route`. A test that reaches
`palworld.kbve.com` depends on the gameserver being up and will fail for
reasons that have nothing to do with the change under test.

## Publishing

The map ships to itch.io as a static build. `.github/workflows/publish-itch.yaml`
runs on `workflow_dispatch` or a `map-v*` tag — deliberately not on every
push to main, since an itch upload is a public release and main moves for
other reasons.

It revalidates, typechecks, and builds before pushing, so a build that
fails its own checks never reaches the store page. Requires a
`ITCH_API` secret — the KBVE org secret, exposed to butler as
`BUTLER_API_KEY`, matching `kbve/brackeys-16`. Its visibility is `all`, so
every org repo including this one already has it; nothing to configure.
The workflow still checks before building, so if that ever changes the
failure costs seconds rather than a full build.

`python3 tools/itch.py` regenerates the store images (630x500 cover,
1920x620 banner) by stitching the real tile pyramid, so the store art
cannot drift from the map. Output lands in `tools/out/`, which is
gitignored — upload it to itch by hand.

## Working here

`tiles-src/` is ~10,600 files. Never `grep`/`find` across it without a
path filter; scope searches to `src/`, `*.md`, or a single icon directory.

Assets keep the `/palworld/` URL prefix they had on the site, so the
component's tile and icon paths needed no edits and existing deep links
stay valid. Do not "tidy" this away without rewriting all 11 call sites.

Commit messages: no `Co-Authored-By` trailers.
