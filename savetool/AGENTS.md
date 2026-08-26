# AGENTS.md — Savetool

Reads Palworld save files and writes base intel as JSON. Runs as a
sidecar on an interval; `relay/` picks the output up from
`SAVE_INTEL_PATH` and serves it as `/live/bases`.

## Rules

**Output shape is the relay's input.** `save_intel.py` writes the guild
and base records that `relay/src/live_api.rs` returns to the map and the
Discord bot. Changing a field here surfaces two hops away, in a browser.

**Dependencies come from a pinned commit.** `requirements.txt` installs
PalworldSaveTools from git at an exact SHA, because save formats change
with game patches and an unpinned upgrade would silently alter parsing.
Bump it deliberately and re-run the tests.

**Configuration is environment-driven:** `SAVE_INTEL_SAVE_DIR`,
`SAVE_INTEL_OUT`, `SAVE_INTEL_INTERVAL_S`.
