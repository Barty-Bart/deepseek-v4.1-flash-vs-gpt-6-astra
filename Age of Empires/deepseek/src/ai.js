// Settlement AI. Written to drive either team so it can also be used as a
// mirror-match balance probe: it gathers, grows, builds and sends attack waves.
import {
  COLS,
  ROWS,
  COSTS,
  BUILDING_STATS,
  RESOURCE_FROM,
  AGES,
  MAX_AGE,
} from './config.js';

export function createAIState() {
  return {
    think: 0,
    nextWaveAt: 200,
    waveSize: 4,
    waveInterval: 92,
    waveSizeStep: 1,
    waveSizeMax: 7,
    maxSites: 2,
    lastTargetId: null,
    rebalanceAt: 0,
    mopUpAt: 0,
  };
}

const other = (team) => 1 - team;
const villagersOf = (game, team) => game.units.filter((u) => u.team === team && u.type === 'villager');
// Every combat unit counts towards the army, not just the basic soldier.
const COMBAT = ['soldier', 'archer', 'knight'];
const armyOf = (game, team) => game.units.filter((u) => u.team === team && COMBAT.includes(u.type));
const mineBuildings = (game, team, type) =>
  game.buildings.filter((b) => b.team === team && (!type || b.type === type));

// Desired share of the workforce in each resource.
const WANT = { food: 0.42, wood: 0.36, gold: 0.22 };

// Army mix by age: index matches the player's age.
const COMPOSITION = [
  [['soldier', 1]],
  [['soldier', 0.6], ['archer', 0.4]],
  [['knight', 0.4], ['archer', 0.35], ['soldier', 0.25]],
];

function desiredUnitType(game, team, armyTarget, army) {
  const mix = COMPOSITION[Math.min(game.players[team].age, COMPOSITION.length - 1)];
  let best = null;
  let bestGap = 0;
  for (const [type, share] of mix) {
    const want = armyTarget * share;
    const have = army.filter((u) => u.type === type).length + game.countQueued(team, type);
    const gap = want - have;
    if (gap > bestGap) {
      bestGap = gap;
      best = type;
    }
  }
  return best;
}

// Age advancement is a real investment: the settlement waits until the economy
// can carry it and keeps a food buffer so unit production does not stall.
function research(game, team) {
  const p = game.players[team];
  if (p.age >= MAX_AGE) return false;
  const tc = mineBuildings(game, team, 'towncenter').find((b) => b.complete);
  if (!tc || tc.research) return false;
  if (villagersOf(game, team).length < 6) return false;
  const cost = AGES[p.age + 1].cost;
  if (!game.canAfford(team, cost)) return false;
  if (p.res.food - cost.food < 60) return false;
  return game.queueResearch(tc).ok;
}

function chosenGatherKind(game, team) {
  const have = { food: 0, wood: 0, gold: 0 };
  let total = 0;
  for (const u of villagersOf(game, team)) {
    if (u.task !== 'gather' && u.task !== 'return') continue;
    const node = game.resourceById.get(u.targetId);
    const kind = node ? RESOURCE_FROM[node.kind] : u.carryKind;
    if (kind && have[kind] !== undefined) {
      have[kind]++;
      total++;
    }
  }
  let bestKind = 'food';
  let bestScore = -Infinity;
  for (const kind of ['food', 'wood', 'gold']) {
    const share = total > 0 ? have[kind] / total : 0;
    const score = WANT[kind] - share;
    if (score > bestScore) {
      bestScore = score;
      bestKind = kind;
    }
  }
  return bestKind;
}

// Villagers loop between a node and the drop-off forever, so a one-off
// assignment never adapts. This periodically moves a few workers from an
// over-staffed resource to whichever one the settlement needs most.
function rebalanceWorkforce(game, team, ai) {
  if (game.time < (ai.rebalanceAt || 0)) return 0;
  ai.rebalanceAt = game.time + 6;

  const gatherers = villagersOf(game, team).filter((u) => u.task === 'gather' || u.task === 'return');
  if (gatherers.length < 4) return 0;

  const kinds = ['food', 'wood', 'gold'];
  const counts = { food: 0, wood: 0, gold: 0 };
  const byKind = { food: [], wood: [], gold: [] };
  for (const u of gatherers) {
    const node = game.resourceById.get(u.targetId);
    const kind = node ? RESOURCE_FROM[node.kind] : u.carryKind;
    if (!kind || counts[kind] === undefined) continue;
    counts[kind]++;
    byKind[kind].push(u);
  }
  const total = counts.food + counts.wood + counts.gold;
  if (!total) return 0;

  const res = game.players[team].res;
  const pressure = {};
  for (const k of kinds) {
    // Target share, nudged by how much is actually in the bank.
    pressure[k] = WANT[k] - counts[k] / total + (res[k] < 150 ? 0.3 : 0) - (res[k] > 700 ? 0.25 : 0);
  }

  let moves = 0;
  for (let pass = 0; pass < 2; pass++) {
    const need = kinds.slice().sort((a, b) => pressure[b] - pressure[a])[0];
    const surplus = kinds.slice().sort((a, b) => pressure[a] - pressure[b])[0];
    if (need === surplus) break;
    if (pressure[need] <= 0.06 || pressure[surplus] >= -0.06) break;
    if (counts[surplus] <= 1) break;
    const u = byKind[surplus].pop();
    if (!u) break;
    const node = game.findNearestResource(u.x, u.y, [need]);
    if (!node) break;
    game.commandGather([u], node);
    counts[surplus]--;
    counts[need]++;
    pressure[surplus] += 1 / total;
    pressure[need] -= 1 / total;
    moves++;
  }
  return moves;
}

// Keep every construction site staffed, and every idle villager working.
function manageWorkers(game, team, ai) {
  const villagers = villagersOf(game, team);
  const sites = game.buildings.filter((b) => b.team === team && !b.complete);

  for (const site of sites) {
    const onIt = villagers.filter((u) => u.task === 'build' && u.targetId === site.id).length;
    if (onIt >= 2) continue;
    const idle = villagers.filter((u) => u.task === 'idle' && u.carry === 0);
    idle
      .sort((a, b) => Math.hypot(a.x - site.x, a.y - site.y) - Math.hypot(b.x - site.x, b.y - site.y))
      .slice(0, 2 - onIt)
      .forEach((u) => game.commandBuild([u], site));
  }

  rebalanceWorkforce(game, team, ai);

  const kind = chosenGatherKind(game, team);
  for (const u of villagers) {
    if (u.task !== 'idle') continue;
    if (u.carry > 0) {
      game.startReturn(u);
      continue;
    }
    const node =
      game.findNearestResource(u.x, u.y, [kind]) || game.findNearestResource(u.x, u.y, null);
    if (node) game.commandGather([u], node);
  }

  // Replace a food source the settlement has outgrown.
  const farms = mineBuildings(game, team, 'farm').length;
  if (farms < 3 && villagers.length >= 6 && game.canAfford(team, COSTS.farm)) {
    tryBuild(game, team, 'farm');
  }
}

function findBuildSpot(game, team, type) {
  const tc = mineBuildings(game, team, 'towncenter').find((b) => b.complete);
  if (!tc) return null;
  const s = BUILDING_STATS[type];
  const offsets = [];
  for (let ring = 1; ring <= 8; ring++) {
    for (let dy = -ring; dy <= ring; dy++) {
      for (let dx = -ring; dx <= ring; dx++) {
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue;
        offsets.push([dx, dy]);
      }
    }
  }
  for (const [dx, dy] of offsets) {
    const tx = tc.tx + dx * (s.w + 1);
    const ty = tc.ty + dy * (s.h + 1);
    if (tx < 1 || ty < 1 || tx + s.w >= COLS || ty + s.h >= ROWS) continue;
    if (game.canPlace(type, team, tx, ty).ok) return { tx, ty };
  }
  return null;
}

function tryBuild(game, team, type) {
  if (!game.canAfford(team, COSTS[type])) return false;
  const spot = findBuildSpot(game, team, type);
  if (!spot) return false;
  return game.placeBuilding(type, team, spot.tx, spot.ty, []).ok;
}

function economy(game, team, ai) {
  const p = game.players[team];
  const sites = game.buildings.filter((b) => b.team === team && !b.complete).length;
  if (sites >= ai.maxSites) return;

  const workers = villagersOf(game, team).length;
  const houses = mineBuildings(game, team, 'house').length;
  const housesDone = mineBuildings(game, team, 'house').filter((b) => b.complete).length;
  const farmsDone = mineBuildings(game, team, 'farm').filter((b) => b.complete).length;
  const barracks = mineBuildings(game, team, 'barracks').length;
  const headroom = p.maxPop - p.pop;

  if (workers >= 3 && housesDone < 3 && (headroom <= 2 || houses < 2) && game.canAfford(team, COSTS.house)) {
    if (tryBuild(game, team, 'house')) return;
  }
  if (barracks < 1 && workers >= 4 && game.canAfford(team, COSTS.barracks)) {
    if (tryBuild(game, team, 'barracks')) return;
  }
  if (farmsDone < 2 && workers >= 5 && p.res.food < 260 && game.canAfford(team, COSTS.farm)) {
    if (tryBuild(game, team, 'farm')) return;
  }
  if (housesDone < 4 && p.res.wood > 170 && game.canAfford(team, COSTS.house)) {
    if (tryBuild(game, team, 'house')) return;
  }
  if (farmsDone < 4 && p.res.wood > 260 && game.canAfford(team, COSTS.farm)) {
    tryBuild(game, team, 'farm');
    return;
  }
  // Towers anchor the base once the settlement reaches the Keep Age.
  const towers = mineBuildings(game, team, 'watchtower').length;
  if (game.players[team].age >= 1 && towers < 2 && workers >= 5 && game.canAfford(team, COSTS.watchtower)) {
    tryBuild(game, team, 'watchtower');
  }
}

function train(game, team) {
  const age = game.players[team].age;
  const armyTarget = Math.min(9, 3 + Math.floor(game.time / 100) + age);
  const army = game.units.filter(
    (u) => u.team === team && (u.type === 'soldier' || u.type === 'archer' || u.type === 'knight'),
  );
  const villagers = villagersOf(game, team).length;

  for (const tc of mineBuildings(game, team, 'towncenter')) {
    if (tc.complete && tc.queue.length < 2 && villagers + game.countQueued(team, 'villager') < 9) {
      game.queueTrain(tc, 'villager');
    }
  }
  const wanted = desiredUnitType(game, team, armyTarget, army);
  if (!wanted) return;
  for (const br of mineBuildings(game, team, 'barracks')) {
    if (br.complete && br.queue.length < 2) game.queueTrain(br, wanted);
  }
}

function nearestEnemyBuilding(game, team, x, y) {
  let best = null;
  let bestD = Infinity;
  for (const b of game.buildings) {
    if (b.team === team) continue;
    const d = (b.x - x) ** 2 + (b.y - y) ** 2;
    if (d < bestD) {
      bestD = d;
      best = b;
    }
  }
  return best;
}

function defence(game, team) {
  const base = mineBuildings(game, team, 'towncenter')[0];
  if (!base) return;
  const raiders = game.units.filter(
    (u) => u.team !== team && Math.hypot(u.x - base.x, u.y - base.y) < 430,
  );
  if (!raiders.length) return;
  for (const s of armyOf(game, team)) {
    if (s.task === 'attack') continue;
    let closest = null;
    let bestD = 520 * 520;
    for (const r of raiders) {
      const d = (r.x - s.x) ** 2 + (r.y - s.y) ** 2;
      if (d < bestD) {
        bestD = d;
        closest = r;
      }
    }
    if (closest) game.commandAttack([s], closest);
  }
}

function manageArmy(game, team, ai) {
  const soldiers = armyOf(game, team);
  if (!soldiers.length) return;

  const enemySoldiers = armyOf(game, 1 - team).length;
  const waveReady = game.time >= ai.nextWaveAt && soldiers.length >= ai.waveSize;
  // With the enemy army gone, keep pushing so the match actually resolves.
  const mopUp = enemySoldiers === 0 && soldiers.length >= 2;
  if (!waveReady && !(mopUp && game.time >= (ai.mopUpAt || 0))) return;

  const target = nearestEnemyBuilding(game, team, soldiers[0].x, soldiers[0].y);
  if (!target) return;

  if (waveReady) {
    ai.nextWaveAt = game.time + ai.waveInterval;
    ai.waveSize = Math.min(ai.waveSizeMax, ai.waveSize + ai.waveSizeStep);
    game.emit('warcry', { x: soldiers[0].x, y: soldiers[0].y, team });
  } else {
    // Re-issue periodically: units that finished a fight go home and idle.
    ai.mopUpAt = game.time + 16;
  }
  ai.lastTargetId = target.id;
  game.commandMove(soldiers, target.x, target.y);
}

export function updateAI(game, dt, team = 1) {
  if (game.state !== 'playing') return;
  const ai = game.ai[team];
  manageWorkers(game, team, ai);
  defence(game, team);
  ai.think -= dt;
  if (ai.think > 0) return;
  ai.think = 0.5;
  research(game, team);
  economy(game, team, ai);
  train(game, team);
  manageArmy(game, team, ai);
}

export { other };
