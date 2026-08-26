# KBVE Palworld

Everything for the KBVE Palworld gameserver.

| Path      | What                                                      |
| --------- | --------------------------------------------------------- |
| `map/`    | Interactive map — Leaflet + Vite, builds to a static site |
| `relay/`  | Live API serving `/live/players` and `/live/bases`         |
| `server/` | Agones images and compose files                            |
| `mods/`   | Server mods                                                |

## Map

```bash
cd map
pnpm install
pnpm dev        # http://localhost:4322
pnpm validate   # static asset checks
pnpm test:e2e   # playwright
pnpm build      # -> map/dist
```
