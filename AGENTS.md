# AGENTS.md — KBVE Palworld

Everything for the KBVE Palworld gameserver: the interactive map, the
live API it reads, the server images, and the mods.

## Layout

```
map/       interactive map — vite + leaflet, tile pyramids, static build
relay/     live API (rust) serving /live/players and /live/bases     [pending]
server/    agones images, docker-compose                             [pending]
mods/      PalForge, PalSchema, chat/event relays, food mods         [pending]
data/      pal + item records shared by map and mods                 [later]
```

Each area has its own `AGENTS.md` with rules that apply there. Read the
one next to the code you are changing.

## Why one repo

The map is the only consumer of the relay's `/live/*` responses. Split
across repos, a response-shape change lands in one and breaks the other
silently. Together, the change and its consumer move in a single commit
and share one set of fixtures.

## Rules

**Deploy targets differ per area.** `map/` builds to a static bundle;
`server/` and `relay/` build container images. CI must use `paths:`
filters so a tile change never rebuilds a server image, and vice versa.

**This repo is public.** It describes a live gameserver, and `relay/`
speaks RCON — remote command execution. Never commit hostnames,
credentials, tokens, or RCON passwords. Configuration comes from the
environment at runtime.

**Commit messages: no `Co-Authored-By` trailers.**
