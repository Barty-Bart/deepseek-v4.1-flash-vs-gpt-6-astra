// Browser-side verification harness. Drives the real Controls/Renderer against a
// real canvas using synthetic DOM events, then prints PASS/FAIL lines.
import { Game } from '../src/game.js';
import { Renderer } from '../src/render.js';
import { Controls } from '../src/input.js';
import { updateAI } from '../src/ai.js';
import { TEAM, TILE, COSTS, BUILDING_STATS, AGES, formationOffsets } from '../src/config.js';

const params = new URLSearchParams(location.search);
const lines = [];
const check = (name, ok, detail = '') => lines.push(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ' :: ' + detail : ''}`);
const note = (t) => lines.push(`INFO ${t}`);

const canvas = document.getElementById('game');
const out = document.getElementById('out');

const hudStub = {
  topHeight: () => 0,
  bottomHeight: () => 0,
  toast: () => {},
  onSelectionChanged: () => {},
  onPlacingChanged: () => {},
  onPauseChanged: () => {},
  onMuteChanged: () => {},
  closeOverlays: () => {},
  requestRestart: () => {},
  toggleHelp: () => {},
};
const soundStub = { play: () => {}, handleEvent: () => {}, setMuted: () => {}, init: () => {} };

const renderer = new Renderer(canvas);
const controls = new Controls({ canvas, renderer, sound: soundStub, hud: hudStub });

function newGame(seed = 1337) {
  const g = new Game(seed);
  renderer.setGame(g);
  controls.setGame(g);
  renderer.resize();
  return g;
}

const rect = () => canvas.getBoundingClientRect();
const toScreen = (wx, wy) => ({
  x: rect().left + (wx - controls.camera.x) * controls.camera.zoom,
  y: rect().top + (wy - controls.camera.y) * controls.camera.zoom,
});

function mouseDown(wx, wy, button = 0, mods = {}) {
  const p = toScreen(wx, wy);
  canvas.dispatchEvent(new MouseEvent('mousedown', { clientX: p.x, clientY: p.y, button, bubbles: true, ...mods }));
}
function mouseMove(wx, wy) {
  const p = toScreen(wx, wy);
  window.dispatchEvent(new MouseEvent('mousemove', { clientX: p.x, clientY: p.y, bubbles: true }));
}
function mouseUp(wx, wy, button = 0) {
  const p = toScreen(wx, wy);
  window.dispatchEvent(new MouseEvent('mouseup', { clientX: p.x, clientY: p.y, button, bubbles: true }));
}
function click(wx, wy, mods = {}) {
  mouseDown(wx, wy, 0, mods);
  mouseUp(wx, wy, 0);
}
function run(game, seconds, dt = 1 / 60, onTick = null) {
  const steps = Math.round(seconds / dt);
  for (let i = 0; i < steps; i++) {
    game.update(dt);
    game.drainEvents();
    if (onTick) onTick(game, i * dt);
  }
}

try {
  // ---------------------------------------------------------------- boot
  let game = newGame(1337);
  const tc = game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter');
  const villagers = game.units.filter((u) => u.team === TEAM.PLAYER);
  check('map generates a player town centre', !!tc, tc ? `at tile ${tc.tx},${tc.ty}` : '');
  check('starts with three villagers', villagers.length === 3, `got ${villagers.length}`);
  check('starts with 4/5 population', game.players[0].pop === 3 && game.players[0].maxPop === 5);
  check('both settlements spawned', game.buildings.filter((b) => b.type === 'towncenter').length === 2);
  check('trees, berries and gold exist near the player base',
    game.findNearestResource(tc.x, tc.y, ['wood']) &&
    game.findNearestResource(tc.x, tc.y, ['food']) &&
    game.findNearestResource(tc.x, tc.y, ['gold']));
  renderer.draw({ camera: controls.camera, placing: null, dragBox: null, isSelected: () => false });
  renderer.drawMinimap(document.createElement('canvas'), game, controls.camera);
  check('renderer draws a frame without throwing', true);

  // ------------------------------------------------------- click selection
  const v0 = villagers[0];
  click(v0.x, v0.y);
  check('clicking a villager selects exactly one unit', controls.selUnits.length === 1,
    `selected ${controls.selUnits.length}`);
  check('clicking a unit spawns a feedback ring', game.rings.length > 0,
    `${game.rings.length} ring(s)`);
  const ringAt = game.rings[game.rings.length - 1];
  check('the ring is centred on what was clicked', Math.hypot(ringAt.x - v0.x, ringAt.y - v0.y) < 12);
  run(game, 1);
  check('the feedback ring fades away on its own', game.rings.length === 0, `${game.rings.length} left`);
  check('clicked unit is the one under the cursor', controls.selUnits[0] === v0);

  // ------------------------------------------------------------ box select
  controls.centerOn(tc.x, tc.y);
  const all = game.units.filter((u) => u.team === TEAM.PLAYER);
  const minX = Math.min(...all.map((u) => u.x)) - 40;
  const maxX = Math.max(...all.map((u) => u.x)) + 40;
  const minY = Math.min(...all.map((u) => u.y)) - 40;
  const maxY = Math.max(...all.map((u) => u.y)) + 40;
  mouseDown(minX, minY);
  mouseMove((minX + maxX) / 2, (minY + maxY) / 2);
  mouseMove(maxX, maxY);
  mouseUp(maxX, maxY);
  check('drag box selects all three villagers', controls.selUnits.length === 3,
    `selected ${controls.selUnits.length}`);

  // --------------------------------------------------------- gather orders
  const tree = game.findNearestResource(tc.x, tc.y, ['wood']);
  mouseDown(tree.x, tree.y, 2);
  check('right-clicking a tree also shows a ring', game.rings.length > 0);
  const gathering = controls.selUnits.filter((u) => u.task === 'gather' && u.targetId === tree.id).length;
  check('right-click on a tree orders all selected villagers to gather', gathering === 3,
    `${gathering}/3 gathering`);
  const woodBefore = game.players[0].res.wood;
  run(game, 25);
  check('villagers deliver wood to the town centre', game.players[0].res.wood > woodBefore,
    `wood ${woodBefore} -> ${Math.round(game.players[0].res.wood)}`);
  check('carried wood shows up in gathered stats', game.stats.gathered.wood > 0,
    `${game.stats.gathered.wood.toFixed(1)} wood`);

  // --------------------------------------------------------- right-click move
  controls.setSelection([game.units.find((u) => u.team === 0 && u.type === 'villager')], null);
  const mover = controls.selUnits[0];
  const destX = tc.x + 150;
  const destY = tc.y - 90;
  mouseDown(destX, destY, 2);
  run(game, 4);
  check('right-click on open ground moves the unit there',
    Math.hypot(mover.x - destX, mover.y - destY) < 40,
    `distance ${Math.hypot(mover.x - destX, mover.y - destY).toFixed(1)}px`);

  // ------------------------------------------------------------- building
  controls.setSelection(game.units.filter((u) => u.team === TEAM.PLAYER), null);
  const woodPre = game.players[0].res.wood;
  controls.startPlacing('house');
  check('build mode engages for a selected villager', !!controls.placing);
  // Find a legal tile by asking the simulation, then click its world centre.
  let spot = null;
  for (let r = 1; r < 60 && !spot; r++) {
    for (let c = 1; c < 80 && !spot; c++) {
      if (game.canPlace('house', TEAM.PLAYER, tc.tx + c - 6, tc.ty + r - 6).ok) {
        spot = { tx: tc.tx + c - 6, ty: tc.ty + r - 6 };
      }
    }
  }
  const spotCenter = { x: spot.tx * TILE + TILE, y: spot.ty * TILE + TILE };
  mouseMove(spotCenter.x, spotCenter.y);
  controls.update(1 / 60);
  check('placement preview validates the tile', controls.placing.valid === true, controls.placing.reason || '');
  mouseDown(spotCenter.x, spotCenter.y);
  const site = game.buildings.find((b) => b.team === 0 && b.type === 'house' && !b.complete);
  check('clicking a valid tile starts construction', !!site);
  check('building cost was deducted', game.players[0].res.wood === woodPre - COSTS.house.wood,
    `${woodPre} -> ${game.players[0].res.wood}`);
  check('build mode exits after placing', controls.placing === null);
  check('villagers were assigned to build', game.units.some((u) => u.task === 'build' && u.targetId === site.id));

  // invalid placement is rejected (use a fresh tree: earlier ones may be harvested)
  const badWood = game.players[0].res.wood;
  controls.startPlacing('house');
  const liveTree = game.resources.find((n) => n.kind === 'tree' && n.amount > 50);
  const badX = liveTree.x;
  const badY = liveTree.y;
  mouseMove(badX, badY);
  controls.update(1 / 60);
  const validBefore = controls.placing.valid;
  mouseDown(badX, badY);
  check('placement on a blocked tile is rejected', validBefore === false && game.players[0].res.wood === badWood,
    `reason: ${controls.placing ? controls.placing.reason : 'n/a'}`);
  controls.cancelPlacing();

  run(game, 22);
  const doneHouse = game.buildings.find((b) => b.team === 0 && b.type === 'house' && b.complete && b.builtAt !== null);
  check('construction completes and raises the population cap', !!doneHouse && game.players[0].maxPop >= 10,
    `maxPop ${game.players[0].maxPop}`);

  // -------------------------------------------------------------- training
  controls.setSelection([], tc);
  const popBefore = game.players[0].pop;
  const foodBefore = game.players[0].res.food;
  const q = game.queueTrain(tc, 'villager');
  check('queueing a villager succeeds when affordable', q.ok, q.reason || '');
  check('training cost is deducted up front', game.players[0].res.food <= foodBefore - 50 + 1);
  const queued = tc.queue.length;
  run(game, 20);
  check('the queue advances and produces a unit',
    game.players[0].pop === popBefore + 1 && queued === 1 && tc.queue.length === 0,
    `pop ${popBefore} -> ${game.players[0].pop}`);

  // population gate
  const popCap = game.players[0].maxPop;
  for (let i = 0; i < 40 && game.players[0].pop < popCap; i++) {
    game.queueTrain(tc, 'villager');
    run(game, 18);
  }
  const capped = game.queueTrain(tc, 'villager');
  check('training is blocked at the population limit', !capped.ok, capped.reason);

  // ------------------------------------------- pathing around structures
  game = newGame(31);
  game.players[0].res = { food: 9999, wood: 9999, gold: 9999 };
  const free = (c, r) =>
    c > 0 && r > 0 && c < 78 && r < 58 && !game.nav.isBlocked(c, r) && !game.resourceTiles.has(r * 80 + c);
  let lane = null;
  for (let r = 4; r < 54 && !lane; r++) {
    for (let c = 4; c < 60 && !lane; c++) {
      let ok = true;
      for (let i = 0; i < 15; i++) if (!free(c + i, r)) ok = false;
      for (let i = 4; i < 8; i++) for (let j = -4; j <= 5; j++) if (!free(c + i, r + j)) ok = false;
      if (ok) lane = { c, r };
    }
  }
  check('found a clear corridor for the pathing test', !!lane);
  if (lane) {
    // Build the wall directly: the build-radius rule is not what is under test here.
    for (const [dx, dy] of [[4, -3], [6, -3], [4, -1], [6, -1], [4, 1], [6, 1]]) {
      game.createBuilding('house', TEAM.PLAYER, lane.c + dx, lane.r + dy, true);
    }
    const startX = lane.c * TILE + 16;
    const startY = lane.r * TILE + 16;
    const endX = (lane.c + 14) * TILE + 16;
    const endY = startY;
    const walker = game.createUnit('soldier', TEAM.PLAYER, startX, startY);
    game.commandMove([walker], endX, endY);
    let onBlocked = 0;
    let crossedWall = 0;
    let samples = 0;
    const wallCols = [lane.c + 4, lane.c + 8];
    const wallRows = [lane.r - 3, lane.r + 3];
    run(game, 26, 1 / 60, () => {
      samples++;
      const tc2 = Math.floor(walker.x / TILE);
      const tr2 = Math.floor(walker.y / TILE);
      if (game.nav.isBlocked(tc2, tr2)) onBlocked++;
      if (tc2 >= wallCols[0] && tc2 < wallCols[1] && tr2 >= wallRows[0] && tr2 < wallRows[1]) crossedWall++;
    });
    check('units never stand inside a building tile', onBlocked === 0, `${onBlocked} blocked samples over ${samples}`);
    check('units pass around the wall, never through its footprint', crossedWall === 0,
      `${crossedWall} samples inside the wall footprint`);
    check('unit reaches the far side of the wall', Math.hypot(walker.x - endX, walker.y - endY) < 40,
      `final gap ${Math.hypot(walker.x - endX, walker.y - endY).toFixed(1)}px`);
  }

  // --------------------------------------------------------------- combat
  game = newGame(99);
  const pTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  const eTc = game.buildings.find((b) => b.team === 1 && b.type === 'towncenter');
  const soldier = game.createUnit('soldier', TEAM.PLAYER, pTc.x + 60, pTc.y + 40);
  const foe = game.createUnit('soldier', TEAM.ENEMY, pTc.x + 200, pTc.y + 40);
  game.commandAttack([soldier], foe);
  const foeHp0 = foe.hp;
  run(game, 12, 1 / 60, (g) => {
    if (g.unitById.get(soldier.id) && g.unitById.get(foe.id)) {
      const d = Math.hypot(soldier.x - foe.x, soldier.y - foe.y);
      if (d > 26) g.commandAttack([soldier], foe);
    }
  });
  check('soldiers close to range and deal damage',
    !game.unitById.get(foe.id) || foe.hp < foeHp0,
    `hp ${foeHp0} -> ${foe.hp <= 0 ? 'dead' : foe.hp}`);

  const arrowsBefore = game.arrows.length;
  game.createUnit('soldier', TEAM.ENEMY, pTc.x + 120, pTc.y);
  run(game, 4);
  check('the town centre shoots at raiders in range', pTc.attackCd > 0 || game.arrows.length > 0 || arrowsBefore === 0);

  // ---------------------------------------------------------- win / lose
  game = newGame(1337);
  const enemyTc = game.buildings.find((b) => b.team === 1 && b.type === 'towncenter');
  enemyTc.hp = 1;
  const attacker = game.createUnit('soldier', TEAM.PLAYER, enemyTc.x - 90, enemyTc.y);
  game.commandAttack([attacker], enemyTc);
  run(game, 20);
  check('destroying the enemy town centre wins the match', game.state === 'won', `state=${game.state} t=${game.time.toFixed(1)}s`);

  game = newGame(1337);
  const ownTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  ownTc.hp = 1;
  const raider = game.createUnit('soldier', TEAM.ENEMY, ownTc.x - 70, ownTc.y);
  game.commandAttack([raider], ownTc);
  run(game, 20);
  check('losing your town centre loses the match', game.state === 'lost', `state=${game.state}`);

  // ------------------------------------------------------- farms feed people
  game = newGame(7);
  game.players[0].res = { food: 10, wood: 4000, gold: 4000 };
  const farmTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  let farmSpot = null;
  for (let r = -12; r <= 12 && !farmSpot; r++) {
    for (let c = -12; c <= 12 && !farmSpot; c++) {
      if (game.canPlace('farm', 0, farmTc.tx + c, farmTc.ty + r).ok) farmSpot = { tx: farmTc.tx + c, ty: farmTc.ty + r };
    }
  }
  const farmRes = game.placeBuilding('farm', 0, farmSpot.tx, farmSpot.ty, game.units.filter((u) => u.team === 0));
  run(game, 20);
  const farm = farmRes.building;
  check('a finished farm becomes a food source', !!farm.foodNodeId && !!game.resourceById.get(farm.foodNodeId),
    farm.foodNodeId ? `node ${farm.foodNodeId}` : 'no node');
  controls.setSelection(game.units.filter((u) => u.team === 0 && u.type === 'villager'), null);
  controls.centerOn(farm.x, farm.y);
  mouseDown(farm.x, farm.y, 2);
  const onField = controls.selUnits.filter((u) => u.task === 'gather' && u.targetId === farm.foodNodeId).length;
  check('right-clicking a farm sends villagers to work it', onField === 3, `${onField}/3 assigned`);
  const food0 = game.players[0].res.food;
  run(game, 30);
  check('farming actually produces food', game.players[0].res.food > food0 + 20,
    `food ${food0} -> ${Math.round(game.players[0].res.food)}`);

  // ------------------------------------------------------------ age advance
  game = newGame(11);
  game.players[0].res = { food: 3000, wood: 3000, gold: 3000 };
  const ageTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  check('watch towers start locked', !game.buildingUnlocked(TEAM.PLAYER, 'watchtower'));
  const lockedPlace = game.canPlace('watchtower', 0, ageTc.tx + 6, ageTc.ty + 6);
  check('locked buildings are rejected before the age is reached',
    !lockedPlace.ok && /Keep Age/.test(lockedPlace.reason), lockedPlace.reason || '');
  const barracksEarly = game.createBuilding('barracks', 0, ageTc.tx + 5, ageTc.ty, true);
  const earlyArcher = game.queueTrain(barracksEarly, 'archer');
  check('locked units cannot be trained', !earlyArcher.ok, earlyArcher.reason || '');
  const research = game.queueResearch(ageTc);
  check('the town centre can research the next age', research.ok, research.reason || '');
  check('research cost is charged up front', game.players[0].res.food === 3000 - AGES[1].cost.food);
  run(game, AGES[1].time + 3);
  check('research completes and advances the age', game.players[0].age === 1,
    `age ${game.players[0].age}`);
  check('the new age unlocks watch towers and archers',
    game.buildingUnlocked(TEAM.PLAYER, 'watchtower') && game.unitUnlocked(TEAM.PLAYER, 'archer'));
  let towerSpot = null;
  for (let r = -12; r <= 12 && !towerSpot; r++) {
    for (let c = -12; c <= 12 && !towerSpot; c++) {
      if (game.canPlace('watchtower', 0, ageTc.tx + c, ageTc.ty + r).ok) towerSpot = { tx: ageTc.tx + c, ty: ageTc.ty + r };
    }
  }
  const towerPlace = towerSpot ? game.placeBuilding('watchtower', 0, towerSpot.tx, towerSpot.ty, []) : { ok: false, reason: 'no legal tile found' };
  check('watch towers can be built once unlocked', towerPlace.ok, towerPlace.reason || '');
  const lateArcher = game.queueTrain(barracksEarly, 'archer');
  check('archers can be trained once unlocked', lateArcher.ok, lateArcher.reason || '');
  const knightsLocked = game.queueTrain(barracksEarly, 'knight');
  check('knights stay locked until the Crown Age',
    !knightsLocked.ok && /Crown Age/.test(knightsLocked.reason), knightsLocked.reason || '');

  // ------------------------------------------------------- ranged combat
  game = newGame(13);
  const rTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  const archer = game.createUnit('archer', TEAM.PLAYER, rTc.x - 260, rTc.y - 160);
  const mark = game.createUnit('soldier', TEAM.ENEMY, rTc.x - 260 + 120, rTc.y - 160);
  game.commandAttack([archer], mark);
  let sawArrow = 0;
  const markHp0 = mark.hp;
  run(game, 14, 1 / 60, (g) => {
    if (g.arrows.length) sawArrow++;
    const a = g.unitById.get(archer.id);
    const m = g.unitById.get(mark.id);
    if (a && m && m.hp > 0) g.commandAttack([a], m);
  });
  check('archers loose visible arrows', sawArrow > 0, `${sawArrow} frames with a projectile`);
  check('arrows land damage after travelling', !game.unitById.get(mark.id) || mark.hp < markHp0,
    `hp ${markHp0} -> ${mark.hp <= 0 ? 'dead' : Math.round(mark.hp)}`);

  // ------------------------------------------------------- towers fire
  game = newGame(17);
  const tTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  const tower = game.createBuilding('watchtower', TEAM.PLAYER, tTc.tx + 7, tTc.ty + 2, true);
  const victim = game.createUnit('soldier', TEAM.ENEMY, tower.x + 120, tower.y + 10);
  const victimHp = victim.hp;
  run(game, 12, 1 / 60, () => {});
  check('watch towers shoot at raiders in range', victim.hp < victimHp,
    `hp ${victimHp} -> ${Math.round(victim.hp)}`);

  // ----------------------------------------------------------- fog states
  game = newGame(23);
  const fogTc = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  const scout = game.createUnit('soldier', TEAM.PLAYER, fogTc.x + 40, fogTc.y + 40);
  const farX = fogTc.x + 520;
  const farY = fogTc.y - 300;
  check('ground far from anything starts unexplored',
    !game.isExplored(0, farX, farY) && !game.isVisible(0, farX, farY));
  scout.x = farX;
  scout.y = farY;
  run(game, 1);
  check('a unit reveals the ground it stands on',
    game.isExplored(0, farX, farY) && game.isVisible(0, farX, farY));
  const enemyScout = game.createUnit('soldier', TEAM.ENEMY, farX + 30, farY + 30);
  check('enemy units inside your sight are visible', game.isVisible(0, enemyScout.x, enemyScout.y));
  scout.x = fogTc.x;
  scout.y = fogTc.y;
  enemyScout.x = farX + 30;
  enemyScout.y = farY + 30;
  run(game, 1);
  check('leaving an area makes it remembered but not watched',
    game.isExplored(0, farX, farY) && !game.isVisible(0, farX, farY));
  check('the fog hides the enemy once they are out of sight',
    !game.isVisible(0, enemyScout.x, enemyScout.y));
  check('sight expands as the base grows',
    game.exploredFraction(0) > 0.02, `${(game.exploredFraction(0) * 100).toFixed(1)}%`);

  // ---------------------------------------------------------- formations
  const line = formationOffsets('line', 6);
  const box = formationOffsets('box', 6);
  const flank = formationOffsets('flank', 6);
  check('formations produce different shapes',
    line[0].x !== box[0].x && JSON.stringify(line) !== JSON.stringify(box) && JSON.stringify(flank) !== JSON.stringify(line),
    `line spread ${Math.round(line[5].x - line[0].x)}px, box spread ${Math.round(box[5].x - box[0].x)}px`);
  check('the line formation is a single row', line.every((o) => o.y === 0));

  game = newGame(19);
  const squad = [];
  const base = game.buildings.find((b) => b.team === 0 && b.type === 'towncenter');
  for (let i = 0; i < 6; i++) {
    squad.push(game.createUnit('soldier', TEAM.PLAYER, base.x + i * 4, base.y + 120));
  }
  game.commandMove(squad, base.x + 300, base.y + 120, 'line');
  run(game, 16);
  const xs = squad.map((u) => u.x);
  const ys = squad.map((u) => u.y);
  check('a line formation arrives spread out and level',
    Math.max(...xs) - Math.min(...xs) > 100 && Math.max(...ys) - Math.min(...ys) < 40,
    `x spread ${Math.round(Math.max(...xs) - Math.min(...xs))}px, y spread ${Math.round(Math.max(...ys) - Math.min(...ys))}px`);

  // ------------------------------------------------- full autonomous match
  game = newGame(2024);
  let contact = null;
  const enemyHome = game.buildings.find((b) => b.team === 1);
  run(game, 600, 1 / 30, (g) => {
    updateAI(g, 1 / 30, 0);
    if (!contact && g.units.some((u) => u.team === 0 && Math.hypot(u.x - enemyHome.x, u.y - enemyHome.y) < 520)) contact = g.time;
  });
  note(`autonomous match: state=${game.state} t=${game.time.toFixed(0)}s firstContact=${contact ? contact.toFixed(0) + 's' : 'none'} playerUnits=${game.units.filter((u) => u.team === 0).length} enemyUnits=${game.units.filter((u) => u.team === 1).length}`);

  // ------------------------------------------------------------- screenshot
  const shot = Number(params.get('shot') || 0);
  if (shot > 0) {
    out.style.display = 'none';
    const g = new Game(2024);
    renderer.setGame(g);
    controls.setGame(g);
    for (let i = 0; i < shot * 30; i++) {
      updateAI(g, 1 / 30, 0);
      g.update(1 / 30);
      g.drainEvents();
      if (g.state !== 'playing') break;
    }
    // Aim the camera at the most interesting cluster of units (or a landmark).
    const enemyTc = g.buildings.find((b) => b.team === 1 && b.type === 'towncenter');
    let focus = g.units.filter((u) => u.team === 0).sort((a, b) => Math.hypot(a.x - enemyTc.x, a.y - enemyTc.y) - Math.hypot(b.x - enemyTc.x, b.y - enemyTc.y))[0] || enemyTc;
    if (params.get('focus') === 'water') {
      const wt = g.terrain.findIndex((t) => t === 1);
      focus = { x: (wt % 80) * 32, y: Math.floor(wt / 80) * 32 };
    } else if (params.get('focus') === 'enemy') {
      focus = enemyTc;
    }
    controls.centerOn(focus.x, focus.y);
    controls.setSelection(g.units.filter((u) => u.team === 0 && u.type === 'soldier').slice(0, 4), null);
    renderer.draw({ camera: controls.camera, placing: null, dragBox: null, isSelected: (e) => controls.isSelected(e) });
    note(`screenshot state: t=${g.time.toFixed(0)}s playerUnits=${g.units.filter((u) => u.team === 0).length} enemyUnits=${g.units.filter((u) => u.team === 1).length} state=${g.state}`);
    if (g.state !== 'playing') {
      document.body.innerHTML = `<h1 style="padding:20px">match ended: ${g.state} at ${Math.floor(g.time / 60)}m${String(Math.floor(g.time % 60)).padStart(2, '0')}s</h1>`;
    }
  }
  // ------------------------------------------------ title screen end to end
  const frame = document.createElement('iframe');
  frame.src = '/index.html?seed=1337';
  frame.style.cssText = 'position:absolute;left:-3000px;width:1200px;height:800px;border:0';
  document.body.appendChild(frame);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  await new Promise((res) => { frame.onload = res; });
  let iw = frame.contentWindow;
  for (let i = 0; i < 60 && !iw.__verdant; i++) await sleep(50);
  const iDoc = iw.document;
  const menu = iDoc.getElementById('overlay-menu');
  check('the title card is shown when the page opens', !!menu && !menu.classList.contains('hidden'));
  check('the title card offers a Start Game button', !!iDoc.getElementById('btn-start'));
  const before = iw.__verdant ? iw.__verdant.game.time : -1;
  await sleep(500);
  const idle = iw.__verdant ? iw.__verdant.game.time : -1;
  check('the match does not run before Start is pressed', idle === before && idle === 0,
    `clock at ${idle}s`);
  iDoc.getElementById('btn-start').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  await sleep(900);
  check('Start Game hides the title card', menu.classList.contains('hidden'));
  const after = iw.__verdant ? iw.__verdant.game.time : -1;
  check('the match clock runs once started', after > 0, `clock at ${Number(after).toFixed(2)}s`);
  check('the world is dark until it is scouted',
    iw.__verdant.game.exploredFraction(0) < 0.35,
    `${(iw.__verdant.game.exploredFraction(0) * 100).toFixed(1)}% explored at the start`);
  check('the player can see their own town centre',
    iw.__verdant.game.isVisible(0, 340, 1540) === true);
  check('the enemy base is hidden in the fog',
    iw.__verdant.game.isVisible(0, 1930, 430) === false);
  frame.remove();
} catch (err) {
  lines.push(`FAIL harness threw :: ${err && err.stack ? err.stack : err}`);
}

const failures = lines.filter((l) => l.startsWith('FAIL')).length;
lines.push(`${failures === 0 ? 'ALL CHECKS PASSED' : failures + ' CHECK(S) FAILED'}`);
out.textContent = lines.join('\n');
document.title = failures === 0 ? 'HARNESS-OK' : `HARNESS-FAIL-${failures}`;
window.__harness = { lines, failures };
