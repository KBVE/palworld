# Palworld Map

Interactive map for the KBVE Palworld gameserver. Deployed on its own,
embedded into `kbve.com`.

## Layout

```
public/palworld/tiles/       base map tile pyramid (XYZ, z2..z6)
public/palworld/wt-overlay/  overlay tile pyramid (z3..z8)
public/palworld/palicons/    item / creature icons
public/palworld/ui/          map chrome
src/map/                     ported map component
src/main.tsx                 standalone entry
```

Tiles and app ship together so the map is one self-contained deployment.
They were split out of `apps/kbve/astro-kbve/public/palworld` in the
`KBVE/kbve` monorepo, where 10,632 tiles were 83% of the site's file count.

## Why its own repo

The tile pyramids are a single logical artifact that nothing else reads,
and they dwarf everything around them. Kept here they stay out of both the
monorepo and `KBVE/cdn`, and this project gets its own deployment budget.
