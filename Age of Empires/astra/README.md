# Hearth & Banner · v1.1

An original, focused browser RTS: three villagers, one town centre, and a rival settlement across the borderlands. Gather and deliver resources, build a village, advance your civilization, raise watchtowers, explore the dark frontier, train spearmen, survive Redfen raids, and destroy the enemy town centre.

## Run

Requires Node.js 20.19+ or 22.12+.

```sh
npm ci
npm run dev -- --port 5173
```

Open **http://localhost:5173**. The initial screen waits for **Found your settlement**. Restart always restores the same map and resources (seed `73421`). The preview is also exposed on your local network by Vite.

```sh
npm run build
npm run preview -- --port 4173
```

The production build is in `dist/`. All graphics, fonts, and sound run locally; gameplay makes no external network requests.

## Controls

| Control                                         | Action                                                     |
| ----------------------------------------------- | ---------------------------------------------------------- |
| Left click                                      | Select a unit, building, or resource                       |
| Left drag                                       | Select a group of your units                               |
| Shift + click / drag                            | Add to selection; Shift-click a selected unit to remove it |
| Right click                                     | Move, gather, construct, or attack according to the target |
| Right click with a production building selected | Set its rally point                                        |
| WASD / arrows / screen edge                     | Pan the camera                                             |
| Middle mouse drag                               | Drag the map                                               |
| Mouse wheel / + and − buttons                   | Zoom                                                       |
| H / Home Base                                   | Centre the camera on your town                             |
| Click minimap                                   | Jump to a map location                                     |
| .                                               | Cycle through idle villagers                               |
| Q                                               | Select your entire army                                    |
| 1 / 2 / 3 / 4 with villagers selected           | Place a house / farm / barracks / watchtower               |
| V with town centre / barracks selected          | Queue a villager / spearman                                |
| Small × on a queued unit                        | Cancel and refund that unit                                |
| U at the town centre                            | Advance to the next age                                    |
| Click the age below the game title              | Select your town centre and its advancement actions        |
| X                                               | Stop selected units                                        |
| Escape / right click during placement           | Cancel placement                                           |
| Space                                           | Pause / resume                                             |
| M                                               | Mute / unmute                                              |
| ?                                               | Open controls                                              |

The game automatically pauses when the window loses focus or the tab is hidden. Controls are designed for a desktop mouse and keyboard. The layout adapts to smaller screens, but full touch commands are not implemented.

## Civilization, watchtowers and discovery

Select your **town centre** and click **Banner Age**, or press **U**, to advance. The age badge below the game title returns you to these actions. Research costs are paid immediately; the progress bar shows the time remaining. Villager training waits during research and resumes afterward. Cancel advancement to refund its full cost.

| Age               | Research cost      | Time       | Civilization benefits                                                                             |
| ----------------- | ------------------ | ---------- | ------------------------------------------------------------------------------------------------- |
| I · Hearth Age    | Starting age       | —          | Base economy, spearmen and timber watchtowers                                                     |
| II · Banner Age   | 200 food, 100 gold | 35 seconds | +15% gathering rate; spearmen gain 20 health and 3 attack; towers become stone                    |
| III · Citadel Age | 350 food, 200 gold | 45 seconds | +30% total gathering rate; spearmen gain 40 health and 6 attack in total; towers gain battlements |

Select a **villager**, then click **Watchtower** or press **4**. A tower costs **110 wood and 50 gold**, takes **22 seconds** for one worker to build, and automatically fires arrows at enemy units. Towers reveal distant terrain even without nearby villagers. Selecting a finished tower shows its firing range. All existing and future towers improve when their civilization advances, at no separate upgrade cost.

| Tower age | Health | Arrow damage | Range   | Vision   |
| --------- | ------ | ------------ | ------- | -------- |
| Hearth    | 650    | 12           | 7 tiles | 10 tiles |
| Banner    | 850    | 18           | 8 tiles | 11 tiles |
| Citadel   | 1,050  | 24           | 9 tiles | 12 tiles |

The main map and minimap now share three visibility states:

- **Dark:** never explored. Send a unit into the darkness with a right-click to scout.
- **Clear:** currently within sight of your units or buildings.
- **Dim:** explored before, but currently out of sight. Terrain stays charted; enemy units disappear. Buildings and resources show only their last observed state until you revisit them.

You cannot select hidden enemies, see live changes to remembered structures, or place buildings in an area nobody can currently see. The charted percentage is shown above the minimap. Sight is circular and does not model elevation or tree occlusion. The rival can also advance its civilization and build a defensive watchtower.

## A useful opening

Send two villagers to berries and one to wood. Train more villagers early and put some on gold. Build a house before reaching the population limit, then a barracks. Keep a few spearmen near home before the first raid, around 1:55. Grow toward roughly ten workers, favour food, and gather an army of at least ten spearmen before pushing toward the red settlement. A watchtower near your gold and berries can protect the economy and extend your view. Save 100 gold for Banner Age once your workers are established. A second barracks helps replace losses; focus enemy watchtowers before pushing on the town centre.

Villagers carry up to 14 resources and must return to their town centre to deliver them. Houses add five population on completion. Each farm supplies 2,400 food. Several villagers can build together, and farm builders start working their finished farm. New orders can redirect workers carrying a load; that load stays with them until delivery. Units automatically find paths around buildings, trees, gold and water. Soldiers automatically engage nearby enemies.

| Item       | Cost              | Time                       | Effect                                |
| ---------- | ----------------- | -------------------------- | ------------------------------------- |
| Villager   | 50 food           | 12 seconds                 | Gathers, builds, and can fight weakly |
| House      | 65 wood           | 15 seconds with one worker | +5 population                         |
| Farm       | 55 wood           | 12 seconds with one worker | Gatherable food                       |
| Barracks   | 150 wood          | 28 seconds with one worker | Trains spearmen                       |
| Watchtower | 110 wood, 50 gold | 22 seconds with one worker | Automatic arrows and extended vision  |
| Spearman   | 60 food, 30 gold  | 15 seconds                 | 115 health, 14 attack                 |

Costs and population are reserved when a unit is queued. Training waits if housing is destroyed and the current population exceeds capacity. Destroying the enemy town centre wins; losing your own ends the match in defeat.

## Verification

```sh
npm test                 # deterministic simulation tests
npm run test:browser     # actual browser controls and end dialogs
node tests/balance.mjs   # accelerated, resource-constrained strategy run
node tests/inspect.mjs   # screenshots and a rendering sample
```

Browser checks use Playwright with installed Google Chrome (`channel: 'chrome'`). Install Google Chrome, or install Playwright Chromium and remove the channel option in `playwright.config.js` and `tests/inspect.mjs`. Browser tests start/reuse the local Vite server. Run the dev server first for the standalone inspection script.

The 23 simulation checks cover the opening, delivery of all three resources, construction costs and duration, invalid placement, farm work, training/refunds/population, obstacle navigation, combat, both match outcomes, enemy growth/raids, pause, crowding regressions, advancement costs/timing/bonuses/refunds, tower combat, discovery, and last-seen building/resource memory. Six browser scenarios cover real mouse/keyboard commands, group selection, construction, training, movement, pan/zoom, minimap, pause, controls, mute, both end dialogs, both age upgrades, all tower appearances, real scouting commands, hidden enemy selection, explored fog, and restart.

The final strategy run follows real costs, build times, gathering, and combat and wins at approximately **6:24 of simulated match time**. It includes a defensive watchtower and Banner Age research and uses an automated player and an accelerated clock; this is not a timed human playthrough. Leaving the settlement completely unattended loses at approximately **3:10**. The browser research checks supply test funds; the ending checks supply test armies and then use real damage to destroy each town centre. Test helpers are available only in the development build; they are not player controls or included in the production bundle.

Current screenshots and measurements are in `artifacts/v1.1/`; v1.0 records remain available in `artifacts/`. Visual review covered 1440×1000 and 1024×768 desktop layouts, plus a 390×844 layout capture. A 5-second headless Chrome sample with 32 units at 1440×1000 and device pixel ratio 1 measured approximately **59.8 FPS**, **1.06 ms mean canvas draw time**, and **1.30 ms p95 draw time**. These are this machine's measurements, not a performance guarantee. `artifacts/v1.1/inspection.json` contains the raw sample and browser version.

No known blocking defects remain. There is no save/load, multiplayer, or full touch control. Soldiers use soft separation rather than a rigid collision system; workers can overlap while gathering. Chrome was tested; Safari and Firefox were not. Audio initialization and mute were exercised, but speaker output was not auditioned. Browser screenshots were visually reviewed; no human-length manual match was performed.

## Editable sources and assets

- `src/simulation.js`: deterministic world, A* paths, economy, construction, queues, combat, opponent, and victory/defeat.
- `src/visibility.js`: current sight, permanent exploration, and last-observed buildings/resources.
- `src/renderer.js`: original procedural isometric terrain, architecture, vegetation, workers, soldiers, portraits, map, and effects. Art version 1.1, including three tower designs and advancing town centres.
- `src/main.js`: player inputs, contextual UI, camera, pause, notifications, and match lifecycle.
- `src/data.js`: balance values, building definitions, team colours, projection, and map seed utilities.
- `src/audio.js`: original Web Audio cues for commands, work completion, combat, alerts, victory, and defeat. Sound version 1.1, including tower arrows.
- `src/style.css`, `index.html`: responsive interface and local typography.
- `public/crest.svg`: editable original crest.
- `public/fonts/`: local font files and their SIL Open Font License texts.

No paid media generation, paid assets, or Descript services were used. Model/API monetary cost is not exposed by this environment.

## Third-party notices

Cormorant Garamond and DM Sans were obtained from Google Fonts and are distributed under the SIL Open Font License. Their license texts are included in `public/fonts/`. Vite and Playwright are development tooling; their licenses are retained in their installed packages. Game names, artwork, crest, and synthesized sound cues were authored for this project. This is an independent game and is not affiliated with Age of Empires.
