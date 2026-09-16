# Verdant Vale

A small, complete browser RTS inspired by classic medieval settlement games. Two
settlements — **Riverwatch** (you) and **Ashfell** (the opponent) — race to gather
resources, advance through the ages, raise buildings and field soldiers. Destroy the
enemy town centre to win; lose your own and the match is over.

Everything here is original: the map, art, names and sound are generated locally.
No external asset packs or paid media generation were used.

## Run it

The game opens on a title card. Press **Start Game** to begin — the map renders behind
the menu, but the match clock does not run until you start.

```bash
node serve.mjs          # http://localhost:4173/
```

ES modules need to be served over HTTP, so open the URL above rather than the file
directly. `PORT=8080 node serve.mjs` changes the port.

The starting map is deterministic (seed 1337), so every fresh match begins from the
same layout. `?seed=12345` uses a different map, and `?seed=random` rolls a new one.

## Fog of war

The map starts dark. Ground your units and buildings can currently see is drawn in full
colour; ground you have seen before but cannot watch right now is dimmed to a slate wash;
ground you have never seen is black. Enemy units and buildings are only drawn while they
are inside your sight, and the minimap is fogged the same way. Vision radii live in
`src/config.js` — villagers see 5 tiles, the town centre 11, watch towers 13.

## Click feedback

Every left click draws a ring that expands and fades, sized to whatever you hit — a unit,
a building, a tree or bare ground. Right clicks draw a ring in green (move, gather, build)
or red (attack) so the order is always acknowledged.

## Controls

| Action | Input |
| --- | --- |
| Select a unit or building | Left click |
| Select many units | Left drag a box |
| Add to selection | Shift + click |
| Move, gather, attack, help build | Right click |
| Pan | `W A S D`, arrow keys, screen edge, or middle-drag |
| Zoom | Mouse wheel |
| Jump to town centre | `H` or the **Home** button |
| Jump camera anywhere | Click the minimap |
| Set a formation | Select 2+ units, then pick **Line / Box / Staggered / Flank** |
| Stop | `X` |
| Pause / mute / restart | `P` / `M` / `R` |
| Cancel placement or selection | `Esc` |
| Show controls | **Controls** button or `?` |

Buildings are placed from the command card: select a villager, click **Build House**,
**Build Farm**, **Build Barracks** or **Build Watch Tower**, then click a tile. Hold
Shift while placing to keep building. Green means the tile is legal, red means it is
not — the reason is shown as a toast. Buttons for things you have not unlocked are
greyed out and say which age brings them.

## Ages

Select your town centre to research the next age. It costs resources and research time,
and unlocks new options:

| Age | Cost | Time | Unlocks |
| --- | --- | --- | --- |
| **Hearth Age** | — | — | Houses, farms, barracks, villagers, soldiers |
| **Keep Age** | 350 food + 120 gold | 40s | **Watch Towers** and **Archers** (ranged) |
| **Crown Age** | 700 food + 350 gold | 55s | **Knights** (heavy melee), and every watch tower hits 60% harder |

## Formations

Select two or more units and the command card shows the classic four group shapes.
Picking one immediately re-forms the group in place, and the choice is used for every
move order you give afterwards.

| Formation | Shape |
| --- | --- |
| Line | A single wide row — good for a firing line |
| Box | A compact square block |
| Staggered | A checkerboard, so units are not packed shoulder to shoulder |
| Flank | Two curved wings with a refused centre |

## Ranged combat

Archers and watch towers fire real projectiles that travel to the target and only deal
damage on arrival, so an arrow in flight can be seen crossing the map. Archers are
fragile and poor against buildings; knights are expensive and break structures quickly.

## How a match plays

Villagers walk to a tree, berry bush or gold mine, gather until they are carrying 10,
then walk the load back to the town centre. Farms are a renewable food source paid for
with wood, so food income stays alive once the berries run dry.

The town centre grants 5 population, each house another 5 (hard cap 50). Villagers
cost food, soldiers cost food and gold, and every building has a real cost and build
time. The town centre and watch towers shoot arrows at raiders inside their range, so
an early rush is not free. Ashfell runs the same rules: it gathers, advances ages,
builds houses, farms, a barracks and towers, trains an army and sends a bigger raiding
party roughly every 90 seconds.

Soldiers pick their own targets inside a 190px aggro radius, break off to fight, and do
extra damage to buildings. Villagers run for the town centre when enemy soldiers get
close and go back to work afterwards.

## Files

```
index.html        page shell and HUD markup
styles.css        HUD styling
src/config.js     all balance numbers (costs, HP, speeds, build times, ages)
src/game.js       simulation: units, buildings, resources, combat, victory
src/ai.js         opponent settlement AI (usable for either team)
src/world.js      deterministic map generation
src/pathfinding.js grid + A* navigation with string pulling
src/render.js     canvas renderer: depth sorting, shadows, fog, minimap
src/input.js      camera, selection, placement and command handling
src/ui.js         HUD: resources, selection panel, command card, overlays
src/icons.js      inline SVG icon set for the command card and resource strip
src/audio.js      WebAudio synthesised sound effects
src/main.js       bootstrap and game loop
serve.mjs         static file server
tools/            verification harnesses (see below)
```

## Verification

```bash
node tools/simulate.mjs 8 -v        # scripted player vs the AI, with a timeline
node tools/simulate.mjs 12 --idle   # passive player: confirms the defeat path
node tools/mirror.mjs 12            # both settlements run the same AI
node tools/probe-ai.mjs 12 --both   # dump a late-match snapshot of both sides
node tools/probe-farm.mjs           # regression check for farm food nodes
```

The browser harness drives the real input layer with synthetic DOM events, so it
exercises selection, right-click orders, placement validation, construction, training,
farming, age research and unlocking, ranged projectiles, tower fire, formations,
pathing, combat and both end states:

```
http://localhost:4173/tools/harness.html          # PASS/FAIL report
http://localhost:4173/tools/hud.html?scenario=villagers   # real HUD, driven state
```

The simulation is deterministic for a given seed, so these runs are repeatable.
Routine checks were run in Node and headless Chrome; measurements are reported in the
task summary rather than stored here. The suite covers 59 assertions, including the
title-card start gate, all three fog states, and click-ring feedback.

## Rendering notes

Buildings are drawn in a fixed 3/4 view: a wall face with stone courses, a two-plane
pitched roof with an overhang, a rim light along the top-left edges and a soft contact
shadow at the base. Eight building types and every unit are drawn with a pre-rendered
radial-gradient shadow sprite rather than a flat ellipse. All world objects are put in
one list and sorted by their ground-contact point before drawing, so a villager standing
south of a house overlaps it correctly. Water carries an animated shimmer. This is an
oblique 3/4 projection, not a true isometric diamond grid.
