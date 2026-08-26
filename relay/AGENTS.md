# AGENTS.md — Relay

The live API for the Palworld gameserver. Tails chat and event logs, polls
RCON and the game's REST endpoint, writes snapshots to ClickHouse, bridges
to IRC, and serves `/live/players` and `/live/bases`.

## Consumers

`/live/*` has two consumers, and only one of them lives in this repo:

- `map/` — the interactive map, in this repo, so a shape change and the
  code reading it move together.
- `apps/discordsh/discordsh-bot/src/discord/commands/palworld.rs` in
  `KBVE/kbve` — a Discord bot that cannot move with us.

Changing a response shape therefore breaks something you cannot see from
here. Treat `/live/players` and `/live/bases` as a published contract:
add fields, do not rename or remove them.

## Rules

**Configuration comes from the environment, never from source.** The
relay reads 17 variables including `PALWORLD_RCON_PASSWORD`,
`PALWORLD_ADMIN_PASSWORD`, `CLICKHOUSE_PASSWORD`, and `IRC_PASSWORD`. This
repo is public and this service speaks RCON — remote command execution on
a live server. Never commit a credential, and never add a default that
embeds one.

**`jedi` comes from crates.io, not a path.** The monorepo builds it as
`packages/rust/jedi`; here it is the published `0.2.3` release, used for
`jedi::rcon` and `jedi::state::sidecar::ClickHouseConfig`. Do not
reintroduce a path dependency — this repo has to build on its own.

**Workspace dependency versions mirror the monorepo** so the relay builds
identically in both places. They live in the root `Cargo.toml`.

## Schema

ClickHouse tables are defined in `data/clickhouse/palworld.sql`. The
writer targets `gameops.palworld_snapshots_raw` and
`gameops.palworld_player_events_raw`; a column change needs both sides.
