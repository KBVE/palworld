# KBVE Palworld

Everything for the KBVE Palworld gameserver.

| Path      | What                                                       |
| --------- | ---------------------------------------------------------- |
| `map/`    | Interactive map — Leaflet + Vite, ships to itch.io          |
| `relay/`  | Live API serving `/live/players` and `/live/bases`          |
| `server/` | Gameserver images and compose files                         |
| `mods/`   | PalForge, PalSchema, chat/event relays, food mods           |
| `deploy/` | Kubernetes manifests, reconciled by ArgoCD                  |
| `data/`   | ClickHouse schema the relay writes to                       |

## Map

```bash
cd map
pnpm install
pnpm dev        # http://localhost:4322
pnpm validate   # static asset checks
pnpm test:e2e   # playwright
pnpm build      # -> map/dist
```

## Relay

```bash
cargo check --workspace
cargo test --workspace
```
