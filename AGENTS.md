# AGENTS.md — Palworld Map

Interactive map for the KBVE Palworld gameserver, embedded into
`kbve.com`. Scope: the tile pyramids, map icons, and the app that renders
them. Nothing else.

## Layout

```
public/tiles/       base tile pyramid (XYZ, z2..z6)
public/wt-overlay/  overlay tile pyramid (z3..z8)
public/palicons/    item / creature icons
public/ui/          map chrome
src/                map application
```

## Rules

**Tiles are generated output — never hand-edit them.** A tile pyramid is
derived from a source image. If a tile is wrong, the source or the
generation step is wrong. Regenerate the affected zoom levels; do not
patch individual `.webp` files.

**Deep links are the feature.** The map must encode position and zoom in
the URL hash (`#/lat/lng/z`) so a view can be pasted into Discord. This is
the main distribution loop, and it is the one thing an iframe embed makes
harder — do not let it regress.

**Watch the file count.** The two pyramids are ~10,600 files. Cloudflare
Pages caps a deployment at 20,000, so a new zoom level is a real budget
decision: each level is 4x the one above it. Before adding z7 to `tiles/`,
check what the map actually requests — unused depth is pure weight.

**Live gameserver state comes from the API, not the build.** Player
counts, base locations, and server status are fetched at runtime from
`api.kbve.com` (cross-origin, CORS). Never bake them into tiles or a
static JSON in this repo.

**No game builds here.** This is a map, not a playable build. Anything
with a wasm/engine export ships to itch instead.

## Working here

`public/` is ~10,600 files. Never `grep`/`find` across it without a path
filter; scope searches to `src/`, `*.md`, or a single icon directory.

Commit messages: no `Co-Authored-By` trailers.
