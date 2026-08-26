# AGENTS.md — KBVE Palworld

Everything for the KBVE Palworld gameserver: the interactive map, the
live API it reads, the server images, and the mods.

## Layout

```
map/       interactive map — vite + leaflet, pmtiles archives, static build
relay/     live API (rust) serving /live/players and /live/bases
server/    gameserver images, docker-compose, ue4ss + shim scripts
savetool/  save parser (python) feeding the relay's /live/bases
mods/      PalForge, PalSchema, chat/event relays, food mods
deploy/    kubernetes manifests, reconciled by ArgoCD
data/      clickhouse schema the relay writes to
```

Each area has its own `AGENTS.md` with rules that apply there. Read the
one next to the code you are changing.

## Why one repo

The map reads the relay's `/live/*` responses. Split across repos, a
shape change lands in one and breaks the other silently; together they
move in a single commit and share one set of fixtures. The same applies
to the Lua mods, which write the log lines the relay parses.

One consumer stays outside: the Discord bot at
`apps/discordsh/discordsh-bot` in `KBVE/kbve` also calls `/live/*`. That
contract is invisible from here, which is why `relay/AGENTS.md` treats
those responses as published — add fields, never rename or remove.

## Rules

**Images are version-gated, not commit-gated.** Each of `relay/`,
`server/`, and `savetool/` carries a `version.toml`, and
`.github/workflows/images.yaml` builds an image only when that version has
no tag in ghcr yet. `deploy/` pins exact versions, so silently replacing
an existing tag would change what the cluster runs with no manifest
saying so. Bump the `version.toml` to ship.

**Dockerfiles build from the repo root.** The server images copy from
`mods/`, and the relay copies the workspace manifest, so every `docker
build` needs `-f <area>/Dockerfile .` from the top. They previously used
monorepo-relative paths and had to be rewritten.

**Deploy targets differ per area.** `map/` builds to a static bundle and
ships to itch; `relay/` and `server/` build container images; `deploy/` is
manifests ArgoCD reconciles. CI uses `paths:` filters so a tile change
never rebuilds the relay, and a mod change never republishes the map.

**Nothing here may depend on a path inside `KBVE/kbve`.** The relay takes
`jedi` from crates.io rather than `packages/rust/jedi`, and the map
carries its own event bus rather than `@kbve/droid`. A satellite that
cannot build alone is not a satellite.

**This repo is public.** It describes a live gameserver, and `relay/`
speaks RCON — remote command execution. Never commit hostnames,
credentials, tokens, or RCON passwords. Configuration comes from the
environment at runtime.

**Commit messages: no `Co-Authored-By` trailers.**
