// Headless balance/behaviour harness: drives the simulation without a browser.
// Usage: node tools/simulate.mjs [minutes] [-v] [--idle] [--seed=1337] [--push=<n>]
import { Game } from '../src/game.js';
import { COSTS, BUILDING_STATS, COLS, ROWS, RESOURCE_FROM } from '../src/config.js';

const args = process.argv.slice(2);
const minutes = Number(args.find((a) => /^\d+(\.\d+)?$/.test(a)) || 8);
const verbose = args.includes('-v');
const idle = args.includes('--idle');
const seedArg = args.find((a) => a.startsWith('--seed='));
const seed = seedArg ? Number(seedArg.split('=')[1]) : 1337;
const pushArg = args.find((a) => a.startsWith('--push='));
const pushAt = pushArg ? Number(pushArg.split('=')[1]) : 6;

const game = new Game(seed);
const DT = 1 / 30;
const steps = Math.round((minutes * 60) / DT);

const villagers = () => game.units.filter((u) => u.team === 0 && u.type === 'villager');
const soldiers = () => game.units.filter((u) => u.team === 0 && u.type === 'soldier');
const mine = (type) => game.buildings.filter((b) => b.team === 0 && b.type === type);
const WANT = { food: 0.42, wood: 0.36, gold: 0.22 };

function chosenKind() {
  const have = { food: 0, wood: 0, gold: 0 };
  let total = 0;
  for (const u of villagers()) {
    if (u.task !== 'gather' && u.task !== 'return') continue;
    const node = game.resourceById.get(u.targetId);
    const kind = node ? RESOURCE_FROM[node.kind] : u.carryKind;
    if (kind && have[kind] !== undefined) { have[kind]++; total++; }
  }
  let best = 'food';
  let bestScore = -Infinity;
  for (const k of ['food', 'wood', 'gold']) {
    const score = WANT[k] - (total ? have[k] / total : 0);
    if (score > bestScore) { bestScore = score; best = k; }
  }
  return best;
}

function placeNear(type, anchor) {
  const s = BUILDING_STATS[type];
  for (let cx = anchor.tx - 14; cx <= anchor.tx + 14; cx++) {
    for (let cy = anchor.ty - 14; cy <= anchor.ty + 14; cy++) {
      if (cx < 1 || cy < 1 || cx + s.w >= COLS || cy + s.h >= ROWS) continue;
      if (!game.canPlace(type, 0, cx, cy).ok) continue;
      const r = game.placeBuilding(type, 0, cx, cy, []);
      if (r.ok) return r.building;
    }
  }
  return null;
}

const order = ['house', 'barracks', 'house', 'farm', 'house', 'farm', 'farm', 'house'];
let orderIndex = 0;
let lastPush = -1;

function playerStep() {
  if (idle) return;
  const p = game.players[0];
  const tc = mine('towncenter').find((b) => b.complete);
  if (!tc) return;

  // Staff construction sites first.
  const sites = game.buildings.filter((b) => b.team === 0 && !b.complete);
  for (const site of sites) {
    const onIt = game.units.filter((u) => u.team === 0 && u.task === 'build' && u.targetId === site.id).length;
    if (onIt >= 2) continue;
    const pool = game.units.filter((u) => u.team === 0 && u.type === 'villager' && u.task === 'idle' && u.carry === 0);
    pool.slice(0, 2 - onIt).forEach((u) => game.commandBuild([u], site));
  }

  const kind = chosenKind();
  for (const u of villagers()) {
    if (u.task !== 'idle') continue;
    if (u.carry > 0) { game.startReturn(u); continue; }
    const node = game.findNearestResource(u.x, u.y, [kind]) || game.findNearestResource(u.x, u.y, null);
    if (node) game.commandGather([u], node);
  }

  const siteCount = game.buildings.filter((b) => b.team === 0 && !b.complete).length;
  if (siteCount < 2 && orderIndex < order.length && game.canAfford(0, COSTS[order[orderIndex]])) {
    const type = order[orderIndex];
    if (placeNear(type, tc)) orderIndex++;
  }

  if (villagers().length + game.countQueued(0, 'villager') < 10) game.queueTrain(tc, 'villager');
  const br = mine('barracks').find((b) => b.complete);
  if (br && soldiers().length + game.countQueued(0, 'soldier') < 8) game.queueTrain(br, 'soldier');

  const army = soldiers();
  if (army.length >= pushAt && game.time > 240) {
    const enemyTc = game.buildings.find((b) => b.team === 1 && b.type === 'towncenter');
    if (enemyTc) game.commandMove(army, enemyTc.x, enemyTc.y);
  }
}

let lastLog = -1;
for (let i = 0; i < steps; i++) {
  playerStep();
  game.update(DT);
  game.drainEvents();
  if (game.state !== 'playing') break;
  const sec = Math.floor(game.time);
  if (verbose && sec % 30 === 0 && sec !== lastLog) {
    lastLog = sec;
    const P = game.players[0];
    const E = game.players[1];
    console.log(
      `${String(Math.floor(sec / 60)).padStart(2)}:${String(sec % 60).padStart(2, '0')} ` +
      `P ${P.pop}/${P.maxPop} f${Math.round(P.res.food)} w${Math.round(P.res.wood)} g${Math.round(P.res.gold)} v${villagers().length} s${soldiers().length} ` +
      `| E ${E.pop}/${E.maxPop} f${Math.round(E.res.food)} w${Math.round(E.res.wood)} g${Math.round(E.res.gold)} s${game.units.filter((u) => u.team === 1 && u.type === 'soldier').length}`,
    );
  }
}

const mm = Math.floor(game.time / 60);
const ss = Math.floor(game.time % 60);
console.log('---');
console.log(`seed=${seed} result=${game.state} time=${mm}m${String(ss).padStart(2, '0')}s`);
console.log(`player  pop=${game.players[0].pop}/${game.players[0].maxPop} villagers=${villagers().length} soldiers=${soldiers().length} buildings=${game.buildings.filter((b) => b.team === 0).length} res=${JSON.stringify(game.players[0].res)}`);
console.log(`enemy   pop=${game.players[1].pop}/${game.players[1].maxPop} units=${game.units.filter((u) => u.team === 1).length} buildings=${game.buildings.filter((b) => b.team === 1).length} res=${JSON.stringify(game.players[1].res)}`);
console.log(`stats   gathered=${JSON.stringify(game.stats.gathered)} trained=${game.stats.trained} built=${game.stats.built} kills=${game.stats.kills} losses=${game.stats.losses}`);
console.log(`resources left=${game.resources.length}`);
