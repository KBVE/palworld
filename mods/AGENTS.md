# AGENTS.md — Mods

Server-side mods for the KBVE Palworld gameserver.

```
PalForge/            Lua: signboards, guardian, positioning
PalChatRelay/        Lua: chat -> relay
PalEventRelay/       Lua: events -> relay
PalSchema/           JSON/JSONC: items, NPCs, shops, blueprints
chef_paldon_yumsay/  Steam Workshop food mod, with a python build step
```

## Rules

**`PalSchema/mods/KBVEShops/raw/kbve-shops.json` is generated today, not
authored.** Its source is MDX under `src/content/docs/palworld/palshop`
in `KBVE/kbve`, converted by `scripts/generate-palworld-shops.mjs` there.
Both that script and its validator read the MDX directly, so they stay in
that repo — moved here they would be tools that cannot run.

The intended direction is the reverse: this JSON becomes the source of
truth and the site renders from it, so shop data lives with the mod that
consumes it rather than in a docs page. That flip needs a delivery route
for the site to read this file — published to the CDN, or a package —
which is not decided yet. Until then, edit the MDX and regenerate;
hand-edits here are overwritten on the next run.

**The Lua mods talk to the relay.** `PalChatRelay` and `PalEventRelay`
write the log lines `relay/src/chat_tail.rs` and `event_tail.rs` parse. A
format change on either side needs the other.

**`chef_paldon_yumsay` has a real build.** `build/` holds python that
generates placeholder art and validates the food TOMLs, with tests
alongside. Run them after touching `foods/`.
