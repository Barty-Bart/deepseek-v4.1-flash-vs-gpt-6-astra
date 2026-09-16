// Core simulation. Deliberately DOM-free so it can be driven headlessly in tests.
import {
  TILE,
  COLS,
  ROWS,
  WORLD_W,
  WORLD_H,
  COSTS,
  TRAIN_TIME,
  BUILD_TIME,
  POP_CAP_TC,
  POP_CAP_HOUSE,
  POP_CAP_MAX,
  BUILD_RADIUS_TILES,
  UNIT_STATS,
  BUILDING_STATS,
  RESOURCE_AMOUNT,
  RESOURCE_LABEL,
  RESOURCE_FROM,
  START_RESOURCES,
  BASE_POS,
  TEAM_COLORS,
  AGES,
  MAX_AGE,
  formationOffsets,
  FOG,
} from './config.js';
import { NavGrid, findPath } from './pathfinding.js';
import { generateWorld } from './world.js';
import { mulberry32 } from './rng.js';
import { createAIState, updateAI } from './ai.js';

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

export class Game {
  constructor(seed = 1337) {
    this.reset(seed);
  }

  reset(seed = this.seed || 1337) {
    this.seed = seed;
    this.time = 0;
    this.nextId = 1;
    this.units = [];
    this.buildings = [];
    this.resources = [];
    this.unitById = new Map();
    this.buildingById = new Map();
    this.resourceById = new Map();
    this.resourceTiles = new Set();
    this.events = [];
    this.floaters = [];
    this.particles = [];
    this.arrows = [];
    this.rings = [];
    this.state = 'playing';
    this.endTime = null;
    this.stats = {
      gathered: { food: 0, wood: 0, gold: 0 },
      trained: 0,
      built: 0,
      kills: 0,
      losses: 0,
    };

    this.nav = new NavGrid(COLS, ROWS);
    this.players = {
      0: { team: 0, res: { ...START_RESOURCES }, pop: 0, maxPop: POP_CAP_TC, age: 0 },
      1: { team: 1, res: { ...START_RESOURCES }, pop: 0, maxPop: POP_CAP_TC, age: 0 },
    };

    generateWorld(this, mulberry32(seed));
    this.spawnBase(0);
    this.spawnBase(1);
    this.recomputePop(0);
    this.recomputePop(1);
    this.ai = [createAIState(), createAIState()];

    // Fog of war: `explored` is remembered ground, `visible` is what is in
    // sight right now.
    const n = COLS * ROWS;
    this.fog = [0, 1].map(() => ({
      explored: new Uint8Array(n),
      visible: new Uint8Array(n),
      counts: new Uint16Array(n),
    }));
    this.fogTimer = 0;
    this.updateFog();
  }

  // --------------------------------------------------------------- fog of war

  updateFog() {
    for (const team of [0, 1]) {
      const f = this.fog[team];
      f.counts.fill(0);
      const stamp = (x, y, radiusTiles) => {
        const c0 = Math.floor(x / TILE);
        const r0 = Math.floor(y / TILE);
        const R = Math.ceil(radiusTiles);
        for (let r = r0 - R; r <= r0 + R; r++) {
          if (r < 0 || r >= ROWS) continue;
          for (let c = c0 - R; c <= c0 + R; c++) {
            if (c < 0 || c >= COLS) continue;
            const dx = c - c0;
            const dy = r - r0;
            if (dx * dx + dy * dy > R * R) continue;
            f.counts[r * COLS + c] = 1;
          }
        }
      };
      for (const u of this.units) {
        if (u.team === team) stamp(u.x, u.y, UNIT_STATS[u.type].sight || 5);
      }
      for (const b of this.buildings) {
        if (b.team !== team) continue;
        const reach = (BUILDING_STATS[b.type].sight || 6) + (b.complete ? 0 : -2);
        stamp(b.x, b.y, Math.max(2, reach));
      }
      for (let i = 0; i < f.counts.length; i++) {
        if (f.counts[i]) {
          f.visible[i] = 1;
          f.explored[i] = 1;
        } else {
          f.visible[i] = 0;
        }
      }
    }
    this.fogVersion = (this.fogVersion || 0) + 1;
  }

  isVisible(team, x, y) {
    const c = Math.floor(x / TILE);
    const r = Math.floor(y / TILE);
    if (c < 0 || r < 0 || c >= COLS || r >= ROWS) return false;
    return this.fog[team].visible[r * COLS + c] === 1;
  }

  isExplored(team, x, y) {
    const c = Math.floor(x / TILE);
    const r = Math.floor(y / TILE);
    if (c < 0 || r < 0 || c >= COLS || r >= ROWS) return false;
    return this.fog[team].explored[r * COLS + c] === 1;
  }

  // How much of the world team 0 has seen, for the end-of-match summary.
  exploredFraction(team) {
    const f = this.fog[team];
    let n = 0;
    for (let i = 0; i < f.explored.length; i++) n += f.explored[i];
    return n / f.explored.length;
  }

  emit(type, data) {
    if (this.events.length > 240) return;
    this.events.push({ type, ...data });
  }

  // ---------------------------------------------------------------- creation

  createResource(kind, x, y, opts = {}) {
    const c = Math.floor(x / TILE);
    const r = Math.floor(y / TILE);
    if (!this.nav.inBounds(c, r)) return null;
    // Farm plots sit inside the farm's own footprint, which blocks that tile.
    if (!opts.allowBlocked && this.nav.isBlocked(c, r)) return null;
    const key = r * COLS + c;
    if (!opts.allowBlocked && this.resourceTiles.has(key)) return null;

    const amount = kind === 'farm' ? BUILDING_STATS.farm.food : RESOURCE_AMOUNT[kind];
    if (amount === undefined) return null;
    const node = {
      __kind: 'resource',
      id: this.nextId++,
      kind,
      x: c * TILE + TILE / 2,
      y: r * TILE + TILE / 2,
      tile: key,
      amount,
      max: amount,
      radius: kind === 'tree' ? 13 : kind === 'gold' ? 14 : kind === 'farm' ? 46 : 11,
      blocks: kind === 'tree' || kind === 'gold',
      jitter: ((key * 2654435761) % 1000) / 1000,
    };
    this.resources.push(node);
    this.resourceById.set(node.id, node);
    this.resourceTiles.add(key);
    if (node.blocks) this.nav.set(c, r, true);
    return node;
  }

  removeResource(node) {
    const i = this.resources.indexOf(node);
    if (i >= 0) this.resources.splice(i, 1);
    this.resourceById.delete(node.id);
    this.resourceTiles.delete(node.tile);
    if (node.blocks) {
      const c = node.tile % COLS;
      const r = (node.tile - c) / COLS;
      this.nav.set(c, r, false);
    }
    if (node.buildingId) {
      const b = this.buildingById.get(node.buildingId);
      if (b) b.foodNodeId = null;
    }
    for (const u of this.units) {
      if (u.targetKind === 'resource' && u.targetId === node.id) {
        u.task = 'idle';
        u.targetId = null;
        u.targetKind = null;
        u.path = null;
      }
    }
  }

  createUnit(type, team, x, y) {
    const st = UNIT_STATS[type];
    const u = {
      __kind: 'unit',
      id: this.nextId++,
      type,
      team,
      x: clamp(x, 12, WORLD_W - 12),
      y: clamp(y, 12, WORLD_H - 12),
      hp: st.hp,
      maxHp: st.hp,
      radius: st.radius,
      task: 'idle',
      targetKind: null,
      targetId: null,
      lastResourceId: null,
      path: null,
      pathIndex: 0,
      pathGoal: null,
      moveDest: null,
      repathCd: 0,
      attackCd: 0,
      carry: 0,
      carryKind: null,
      facing: 1,
      animPhase: (this.nextId % 17) * 0.37,
      walking: false,
      building: false,
      lastX: x,
      lastY: y,
      stuckTimer: 0,
      fleeCd: 1.5,
      resumeGatherId: null,
      flash: 0,
      selected: false,
    };
    this.units.push(u);
    this.unitById.set(u.id, u);
    this.players[team].pop++;
    return u;
  }

  removeUnit(u) {
    const i = this.units.indexOf(u);
    if (i >= 0) this.units.splice(i, 1);
    this.unitById.delete(u.id);
    this.updateFog();
    this.players[u.team].pop = Math.max(0, this.players[u.team].pop - 1);
    for (const other of this.units) {
      if (other.targetKind === 'unit' && other.targetId === u.id) {
        other.task = other.task === 'attack' ? (other.moveDest ? 'move' : 'idle') : other.task;
        other.targetId = null;
        other.targetKind = null;
        other.path = null;
      }
    }
  }

  createBuilding(type, team, tx, ty, complete) {
    const s = BUILDING_STATS[type];
    const b = {
      __kind: 'building',
      id: this.nextId++,
      type,
      team,
      tx,
      ty,
      w: s.w,
      h: s.h,
      x: tx * TILE + (s.w * TILE) / 2,
      y: ty * TILE + (s.h * TILE) / 2,
      maxHp: s.hp,
      hp: complete ? s.hp : Math.max(1, Math.round(s.hp * 0.12)),
      complete: !!complete,
      buildTime: BUILD_TIME[type] || 10,
      progress: complete ? BUILD_TIME[type] || 10 : 0,
      queue: [],
      research: null,
      foodNodeId: null,
      selected: false,
      flash: 0,
      builtAt: complete ? this.time : null,
    };
    this.buildings.push(b);
    this.buildingById.set(b.id, b);
    this.nav.setRect(tx, ty, s.w, s.h, true);
    return b;
  }

  removeBuilding(b) {
    const i = this.buildings.indexOf(b);
    if (i >= 0) this.buildings.splice(i, 1);
    this.buildingById.delete(b.id);
    this.updateFog();
    this.nav.setRect(b.tx, b.ty, b.w, b.h, false);
    if (b.foodNodeId) {
      const node = this.resourceById.get(b.foodNodeId);
      if (node) this.removeResource(node);
    }
    for (const u of this.units) {
      if (u.targetKind === 'building' && u.targetId === b.id) {
        u.task = 'idle';
        u.targetId = null;
        u.targetKind = null;
        u.path = null;
      }
    }
    this.recomputePop(b.team);
  }

  completeBuilding(b) {
    if (b.complete) return;
    b.complete = true;
    b.progress = b.buildTime;
    b.hp = Math.max(b.hp, Math.round(b.maxHp * 0.35));
    b.hp = b.maxHp;
    b.builtAt = this.time;
    if (b.type === 'farm') {
      const node = this.createResource('farm', b.x, b.y, { allowBlocked: true });
      if (node) {
        node.buildingId = b.id;
        b.foodNodeId = node.id;
        this.emit('farm-ready', { x: b.x, y: b.y, team: b.team });
      }
    }
    this.recomputePop(b.team);
    if (b.team === 0) this.stats.built++;
    this.emit('complete', { x: b.x, y: b.y, team: b.team });
    this.addFloater(b.x, b.y - b.h * TILE * 0.5 - 10, `${BUILDING_STATS[b.type].name} complete`, b.team === 0 ? '#bfe3a8' : '#f0b4a8');
  }

  spawnBase(team) {
    const pos = BASE_POS[team];
    const s = BUILDING_STATS.towncenter;
    const tx = clamp(Math.round(pos.x / TILE - s.w / 2), 1, COLS - s.w - 1);
    const ty = clamp(Math.round(pos.y / TILE - s.h / 2), 1, ROWS - s.h - 1);
    // Clear anything sitting under the footprint, then wall it off.
    for (let y = ty - 1; y < ty + s.h + 1; y++) {
      for (let x = tx - 1; x < tx + s.w + 1; x++) {
        if (!this.nav.inBounds(x, y)) continue;
        const key = y * COLS + x;
        if (this.resourceTiles.has(key)) {
          const node = this.resources.find((n) => n.tile === key);
          if (node) this.removeResource(node);
        }
      }
    }
    const tc = this.createBuilding('towncenter', team, tx, ty, true);
    for (let i = 0; i < 3; i++) {
      const ang = (i / 3) * Math.PI * 2 + (team ? 1.3 : -0.5);
      const px = tc.x + Math.cos(ang) * (s.w * TILE * 0.5 + 36);
      const py = tc.y + Math.sin(ang) * (s.h * TILE * 0.5 + 36);
      const spot = this.freeSpotAt(px, py);
      this.createUnit('villager', team, spot.x, spot.y);
    }
  }

  freeSpotAt(x, y) {
    const c0 = Math.floor(x / TILE);
    const r0 = Math.floor(y / TILE);
    for (let ring = 0; ring <= 7; ring++) {
      for (let dy = -ring; dy <= ring; dy++) {
        for (let dx = -ring; dx <= ring; dx++) {
          if (ring > 0 && Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue;
          const c = c0 + dx;
          const r = r0 + dy;
          if (this.nav.isBlocked(c, r)) continue;
          return { x: c * TILE + TILE / 2, y: r * TILE + TILE / 2 };
        }
      }
    }
    return { x, y };
  }

  freeSpotNearBuilding(b) {
    const hw = (b.w * TILE) / 2;
    const hh = (b.h * TILE) / 2;
    for (let ring = 0; ring < 4; ring++) {
      const pad = 22 + ring * TILE;
      const spots = [
        { x: b.x, y: b.y + hh + pad },
        { x: b.x, y: b.y - hh - pad },
        { x: b.x - hw - pad, y: b.y },
        { x: b.x + hw + pad, y: b.y },
      ];
      for (const s of spots) {
        const c = Math.floor(s.x / TILE);
        const r = Math.floor(s.y / TILE);
        if (!this.nav.isBlocked(c, r)) return { x: c * TILE + TILE / 2, y: r * TILE + TILE / 2 };
      }
    }
    return this.freeSpotAt(b.x, b.y + hh + TILE * 2);
  }

  // ---------------------------------------------------------------- economy

  recomputePop(team) {
    let pop = 0;
    for (const u of this.units) if (u.team === team) pop++;
    let cap = 0;
    for (const b of this.buildings) {
      if (b.team !== team || !b.complete) continue;
      if (b.type === 'towncenter') cap += POP_CAP_TC;
      if (b.type === 'house') cap += POP_CAP_HOUSE;
    }
    this.players[team].pop = pop;
    this.players[team].maxPop = Math.min(POP_CAP_MAX, cap);
  }

  canAfford(team, cost) {
    const res = this.players[team].res;
    for (const k in cost) if ((res[k] || 0) < cost[k]) return false;
    return true;
  }

  spend(team, cost) {
    const res = this.players[team].res;
    for (const k in cost) res[k] -= cost[k];
  }

  refund(team, cost) {
    const res = this.players[team].res;
    for (const k in cost) res[k] += cost[k];
  }

  countQueued(team, type) {
    let n = 0;
    for (const b of this.buildings) {
      if (b.team !== team) continue;
      for (const item of b.queue) if (!type || item.type === type) n++;
    }
    return n;
  }

  popHeadroom(team) {
    const p = this.players[team];
    return p.maxPop - p.pop - this.countQueued(team, null);
  }

  // ---------------------------------------------------------------- placement

  buildRadiusDistance(team, tx, ty, w, h) {
    let best = Infinity;
    for (const b of this.buildings) {
      if (b.team !== team) continue;
      const dx = Math.max(b.tx - (tx + w), tx - (b.tx + b.w), 0);
      const dy = Math.max(b.ty - (ty + h), ty - (b.ty + b.h), 0);
      best = Math.min(best, Math.hypot(dx, dy));
    }
    return best;
  }

  buildingUnlocked(team, type) {
    const s = BUILDING_STATS[type];
    if (!s) return false;
    return this.players[team].age >= (s.age || 0);
  }

  unitUnlocked(team, type) {
    const st = UNIT_STATS[type];
    if (!st) return false;
    return this.players[team].age >= (st.age || 0);
  }

  lockedReason(type) {
    const s = BUILDING_STATS[type];
    const age = s ? s.age || 0 : 0;
    return `Requires the ${AGES[age].name}`;
  }

  canPlace(type, team, tx, ty) {
    const s = BUILDING_STATS[type];
    if (!s) return { ok: false, reason: 'Unknown building' };
    if (!this.buildingUnlocked(team, type)) return { ok: false, reason: this.lockedReason(type) };
    if (tx < 0 || ty < 0 || tx + s.w > COLS || ty + s.h > ROWS) {
      return { ok: false, reason: 'Outside the map' };
    }
    for (let y = ty; y < ty + s.h; y++) {
      for (let x = tx; x < tx + s.w; x++) {
        if (this.nav.isBlocked(x, y)) return { ok: false, reason: 'Ground is blocked' };
        if (this.resourceTiles.has(y * COLS + x)) return { ok: false, reason: 'Resource in the way' };
      }
    }
    if (this.buildRadiusDistance(team, tx, ty, s.w, s.h) > BUILD_RADIUS_TILES) {
      return { ok: false, reason: 'Too far from your settlement' };
    }
    return { ok: true, reason: '' };
  }

  placeBuilding(type, team, tx, ty, builders = []) {
    const check = this.canPlace(type, team, tx, ty);
    if (!check.ok) return { ok: false, reason: check.reason };
    if (!this.canAfford(team, COSTS[type])) return { ok: false, reason: 'Not enough resources' };
    this.spend(team, COSTS[type]);
    const b = this.createBuilding(type, team, tx, ty, false);
    if (builders.length) this.commandBuild(builders, b);
    this.emit('place', { x: b.x, y: b.y, team });
    return { ok: true, building: b };
  }

  // ---------------------------------------------------------------- commands

  commandMove(units, x, y, formation) {
    const n = units.length;
    const offsets = formationOffsets(formation || this.formation || 'box', n);
    units.forEach((u, i) => {
      const off = offsets[i] || { x: 0, y: 0 };
      const gx = clamp(x + off.x, 14, WORLD_W - 14);
      const gy = clamp(y + off.y, 14, WORLD_H - 14);
      u.task = 'move';
      u.targetKind = null;
      u.targetId = null;
      u.moveDest = { x: gx, y: gy };
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
    });
  }

  commandGather(units, node) {
    for (const u of units) {
      const st = UNIT_STATS[u.type];
      if (st.gather <= 0) {
        u.task = 'move';
        u.moveDest = { x: node.x, y: node.y };
        u.path = null;
        u.repathCd = 0;
        continue;
      }
      u.task = 'gather';
      u.targetKind = 'resource';
      u.targetId = node.id;
      u.lastResourceId = node.id;
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
    }
  }

  commandAttack(units, target) {
    for (const u of units) {
      u.task = 'attack';
      u.targetKind = target.__kind;
      u.targetId = target.id;
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
      u.moveDest = null;
    }
  }

  commandBuild(units, b) {
    let any = false;
    for (const u of units) {
      if (UNIT_STATS[u.type].build <= 0) continue;
      u.task = 'build';
      u.targetKind = 'building';
      u.targetId = b.id;
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
      any = true;
    }
    return any;
  }

  commandStop(units) {
    for (const u of units) {
      u.task = 'idle';
      u.targetKind = null;
      u.targetId = null;
      u.moveDest = null;
      u.path = null;
      u.pathGoal = null;
    }
  }

  commandAttackMove(units, x, y, formation) {
    this.commandMove(units, x, y, formation);
  }

  // Re-arrange a group around its current centre of mass.
  reformUnits(units, formation) {
    if (units.length < 2) return false;
    let cx = 0;
    let cy = 0;
    for (const u of units) {
      cx += u.x;
      cy += u.y;
    }
    cx /= units.length;
    cy /= units.length;
    this.commandMove(units, cx, cy, formation);
    return true;
  }

  queueTrain(b, type) {
    if (!b.complete) return { ok: false, reason: 'Still under construction' };
    const cost = COSTS[type];
    const time = TRAIN_TIME[type];
    if (!cost || !time) return { ok: false, reason: 'Cannot train that' };
    const trains = BUILDING_STATS[b.type].trains || [];
    if (!trains.includes(type)) return { ok: false, reason: `${BUILDING_STATS[b.type].name} cannot train that` };
    if (!this.unitUnlocked(b.team, type)) {
      return { ok: false, reason: `Requires the ${AGES[UNIT_STATS[type].age || 0].name}` };
    }
    if (this.popHeadroom(b.team) <= 0) return { ok: false, reason: 'Population limit reached' };
    if (!this.canAfford(b.team, cost)) return { ok: false, reason: 'Not enough resources' };
    if (b.queue.length >= 5) return { ok: false, reason: 'Queue is full' };
    this.spend(b.team, cost);
    b.queue.push({ type, time, elapsed: 0 });
    this.emit('queue', { x: b.x, y: b.y, team: b.team });
    return { ok: true };
  }

  queueResearch(b) {
    if (!b.complete) return { ok: false, reason: 'Still under construction' };
    if (!BUILDING_STATS[b.type].research) return { ok: false, reason: 'Cannot research here' };
    const p = this.players[b.team];
    if (p.age >= MAX_AGE) return { ok: false, reason: 'Already at the final age' };
    if (b.research) return { ok: false, reason: 'Already advancing' };
    const next = AGES[p.age + 1];
    if (!this.canAfford(b.team, next.cost)) return { ok: false, reason: 'Not enough resources' };
    this.spend(b.team, next.cost);
    b.research = { to: p.age + 1, elapsed: 0, time: next.time };
    this.emit('research-start', { x: b.x, y: b.y, team: b.team });
    return { ok: true, age: next };
  }

  cancelResearch(b) {
    if (!b.research) return false;
    const age = AGES[b.research.to];
    this.refund(b.team, age.cost);
    b.research = null;
    return true;
  }

  cancelTrain(b) {
    if (!b.queue.length) return false;
    const item = b.queue.pop();
    this.refund(b.team, COSTS[item.type]);
    return true;
  }

  // ---------------------------------------------------------------- targeting

  resolveTarget(u) {
    if (u.targetKind === 'unit') {
      const t = this.unitById.get(u.targetId);
      return t && t.hp > 0 ? t : null;
    }
    if (u.targetKind === 'building') {
      const t = this.buildingById.get(u.targetId);
      return t && t.hp > 0 ? t : null;
    }
    return null;
  }

  findAggroTarget(u, radius) {
    let best = null;
    let bestD = radius * radius;
    for (const other of this.units) {
      if (other.team === u.team) continue;
      const d2 = (other.x - u.x) ** 2 + (other.y - u.y) ** 2;
      if (d2 < bestD) {
        bestD = d2;
        best = other;
      }
    }
    if (best) return best;
    for (const b of this.buildings) {
      if (b.team === u.team) continue;
      const d2 = (b.x - u.x) ** 2 + (b.y - u.y) ** 2;
      const reach = radius + Math.max(b.w, b.h) * TILE * 0.5;
      if (d2 < reach * reach && d2 < bestD + reach * reach) {
        if (bestD > reach * reach || d2 < bestD) {
          bestD = d2;
          best = b;
        }
      }
    }
    return best;
  }

  findDropOff(team, x, y) {
    let best = null;
    let bestD = Infinity;
    for (const b of this.buildings) {
      if (b.team !== team || b.type !== 'towncenter' || !b.complete) continue;
      const d = (b.x - x) ** 2 + (b.y - y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = b;
      }
    }
    return best;
  }

  findNearestResource(x, y, kinds) {
    let best = null;
    let bestD = Infinity;
    for (const n of this.resources) {
      if (n.amount <= 0) continue;
      if (kinds && !kinds.includes(RESOURCE_FROM[n.kind])) continue;
      const d = (n.x - x) ** 2 + (n.y - y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = n;
      }
    }
    return best;
  }

  unitAt(x, y) {
    let best = null;
    let bestD = Infinity;
    for (const u of this.units) {
      const d = Math.hypot(u.x - x, u.y - y);
      if (d <= u.radius + 7 && d < bestD) {
        bestD = d;
        best = u;
      }
    }
    return best;
  }

  buildingAt(x, y) {
    for (let i = this.buildings.length - 1; i >= 0; i--) {
      const b = this.buildings[i];
      const hw = (b.w * TILE) / 2;
      const hh = (b.h * TILE) / 2;
      if (x >= b.x - hw && x <= b.x + hw && y >= b.y - hh && y <= b.y + hh) return b;
    }
    return null;
  }

  resourceAt(x, y) {
    let best = null;
    let bestD = Infinity;
    for (const n of this.resources) {
      const d = Math.hypot(n.x - x, n.y - y);
      if (d <= n.radius + 8 && d < bestD) {
        bestD = d;
        best = n;
      }
    }
    return best;
  }

  // ---------------------------------------------------------------- movement

  setPath(u, tx, ty) {
    const res = findPath(this.nav, u.x, u.y, tx, ty);
    if (res.points && res.points.length) {
      u.path = res.points;
      u.pathIndex = 0;
      u.destX = tx;
      u.destY = ty;
      return true;
    }
    u.path = null;
    return false;
  }

  stepMove(u, dt, speed) {
    if (!u.path || u.pathIndex >= u.path.length) {
      u.walking = false;
      return true;
    }
    u.walking = true;
    let budget = speed * dt;
    while (budget > 0 && u.pathIndex < u.path.length) {
      const node = u.path[u.pathIndex];
      const dx = node.x - u.x;
      const dy = node.y - u.y;
      const d = Math.hypot(dx, dy);
      if (d <= 0.0001) {
        u.pathIndex++;
        continue;
      }
      if (dx !== 0) u.facing = dx > 0 ? 1 : -1;
      if (d <= budget) {
        u.x = node.x;
        u.y = node.y;
        budget -= d;
        u.pathIndex++;
      } else {
        u.x += (dx / d) * budget;
        u.y += (dy / d) * budget;
        budget = 0;
      }
    }
    if (u.pathIndex >= u.path.length) {
      u.walking = false;
      return true;
    }
    return false;
  }

  approachPoint(u, gx, gy, arriveDist, dt, speed) {
    const d = Math.hypot(gx - u.x, gy - u.y);
    if (d <= arriveDist) {
      u.path = null;
      u.pathIndex = 0;
      u.walking = false;
      return true;
    }
    const needRepath =
      !u.path ||
      u.pathIndex >= u.path.length ||
      !u.pathGoal ||
      Math.hypot(u.pathGoal.x - gx, u.pathGoal.y - gy) > TILE * 1.5;
    if (needRepath && u.repathCd <= 0) {
      this.setPath(u, gx, gy);
      u.pathGoal = { x: gx, y: gy };
      u.repathCd = 0.35;
    }
    this.stepMove(u, dt, speed);
    return Math.hypot(gx - u.x, gy - u.y) <= arriveDist;
  }

  closestPointOnBuilding(b, x, y, pad) {
    const hw = (b.w * TILE) / 2 + pad;
    const hh = (b.h * TILE) / 2 + pad;
    const cx = clamp(x, b.x - hw, b.x + hw);
    const cy = clamp(y, b.y - hh, b.y + hh);
    return { x: cx, y: cy };
  }

  // ---------------------------------------------------------------- unit tasks

  updateUnit(u, dt) {
    const st = UNIT_STATS[u.type];
    u.attackCd = Math.max(0, u.attackCd - dt);
    u.repathCd = Math.max(0, u.repathCd - dt);
    u.flash = Math.max(0, u.flash - dt * 3);
    u.animPhase += dt * (u.walking ? 11 : 3);
    u.building = false;

    switch (u.task) {
      case 'move':
        this.taskMove(u, dt, st);
        break;
      case 'gather':
        this.taskGather(u, dt, st);
        break;
      case 'return':
        this.taskReturn(u, dt, st);
        break;
      case 'build':
        this.taskBuild(u, dt, st);
        break;
      case 'attack':
        this.taskAttack(u, dt, st);
        break;
      default:
        this.taskIdle(u, dt, st);
        break;
    }

    u.fleeCd = Math.max(0, (u.fleeCd || 0) - dt);
    if (this.considerFleeing(u)) return;
    this.updateStuck(u, dt);
    this.keepOutOfWalls(u, dt);
  }

  // Nearest hostile soldier inside `radius`, if any.
  threatNear(u, radius) {
    let best = null;
    let bestD = radius * radius;
    for (const other of this.units) {
      if (other.team === u.team) continue;
      if (UNIT_STATS[other.type].dmg <= 0) continue;
      const d = (other.x - u.x) ** 2 + (other.y - u.y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = other;
      }
    }
    return best;
  }

  // Villagers head for the town centre when raiders get close, then go back to work.
  considerFleeing(u) {
    if (u.type !== 'villager' || u.task === 'build') return false;
    if (u.fleeCd > 0) return false;
    const threat = this.threatNear(u, 130);
    if (!threat) return false;
    if (u.task === 'gather' || u.task === 'return') u.resumeGatherId = u.lastResourceId || u.targetId;
    const tc = this.findDropOff(u.team, u.x, u.y);
    if (!tc) return false;
    const dx = u.x - threat.x;
    const dy = u.y - threat.y;
    const d = Math.hypot(dx, dy) || 1;
    const runTo = { x: u.x + (dx / d) * 120, y: u.y + (dy / d) * 120 };
    const towardTc = { x: tc.x, y: tc.y };
    // Prefer the town centre when it is the closer shelter.
    const useTc = Math.hypot(towardTc.x - u.x, towardTc.y - u.y) < Math.hypot(runTo.x - u.x, runTo.y - u.y) + 60;
    const goal = useTc ? towardTc : runTo;
    u.task = 'move';
    u.moveDest = { x: clamp(goal.x, 20, WORLD_W - 20), y: clamp(goal.y, 20, WORLD_H - 20) };
    u.path = null;
    u.pathGoal = null;
    u.repathCd = 0;
    u.fleeCd = 3.5;
    this.emit('flee', { x: u.x, y: u.y, team: u.team });
    return true;
  }

  taskIdle(u, dt, st) {
    u.walking = false;
    if (u.resumeGatherId) {
      const node = this.resourceById.get(u.resumeGatherId);
      u.resumeGatherId = null;
      if (node && node.amount > 0 && !this.threatNear(u, 150)) {
        this.commandGather([u], node);
        return;
      }
    }
    if (u.carry > 0 && u.type === 'villager' && st.gather > 0) {
      // A villager left holding resources should finish the delivery run.
      const prev = u.lastResourceId && this.resourceById.get(u.lastResourceId);
      const node = prev && prev.amount > 0 ? prev : this.findNearestResource(u.x, u.y, null);
      if (!node || Math.hypot(node.x - u.x, node.y - u.y) > 240) this.startReturn(u);
    }
    if (st.aggro > 0) {
      const target = this.findAggroTarget(u, st.aggro);
      if (target) {
        u.task = 'attack';
        u.targetKind = target.__kind;
        u.targetId = target.id;
        u.path = null;
      }
    }
  }

  taskMove(u, dt, st) {
    const dest = u.moveDest;
    if (!dest) {
      u.task = 'idle';
      return;
    }
    if (st.aggro > 0) {
      const target = this.findAggroTarget(u, st.aggro);
      if (target) {
        u.task = 'attack';
        u.targetKind = target.__kind;
        u.targetId = target.id;
        u.path = null;
        u.pathGoal = null;
        return;
      }
    }
    const arrived = this.approachPoint(u, dest.x, dest.y, 6, dt, st.speed);
    if (arrived) {
      u.task = 'idle';
      u.moveDest = null;
      u.path = null;
    }
  }

  taskGather(u, dt, st) {
    const node = this.resourceById.get(u.targetId);
    if (!node || node.amount <= 0) {
      u.task = 'idle';
      u.targetId = null;
      u.targetKind = null;
      u.path = null;
      return;
    }
    if (u.carry >= st.carry) {
      this.startReturn(u);
      return;
    }
    const d = Math.hypot(node.x - u.x, node.y - u.y);
    const stop = node.radius + u.radius + 3;
    let inRange = d <= stop + 2;
    if (!inRange) {
      const dirX = (u.x - node.x) / (d || 1);
      const dirY = (u.y - node.y) / (d || 1);
      inRange = this.approachPoint(
        u,
        node.x + dirX * stop,
        node.y + dirY * stop,
        3,
        dt,
        st.speed,
      );
    } else {
      u.path = null;
      u.walking = false;
    }
    if (!inRange) return;

    let amt = st.gather * dt;
    amt = Math.min(amt, node.amount, st.carry - u.carry);
    if (amt > 0) {
      node.amount -= amt;
      const kind = RESOURCE_FROM[node.kind];
      u.carryKind = kind;
      u.carry += amt;
      if (u.team === 0) this.stats.gathered[kind] += amt;
      node.workedAt = this.time;
      u.gatherSfx = (u.gatherSfx || 0) + dt;
      if (u.gatherSfx > 1.1) {
        u.gatherSfx = 0;
        this.emit('gather', { x: u.x, y: u.y, team: u.team, resource: kind });
        const col = node.kind === 'tree' ? '#8fbf5a'
          : node.kind === 'gold' ? '#f0d76a'
            : node.kind === 'farm' ? '#a8d06a' : '#e2725f';
        this.addParticles(node.x, node.y - 6, col, 3, 34);
      }
    }
    if (node.amount <= 0) {
      const x = node.x;
      const y = node.y;
      this.removeResource(node);
      this.emit('depleted', { x, y });
      u.task = 'idle';
      u.targetId = null;
      u.targetKind = null;
      return;
    }
    if (!Number.isFinite(node.max)) return; // renewable source: keep gathering
    if (u.carry >= st.carry) this.startReturn(u);
  }

  startReturn(u) {
    const tc = this.findDropOff(u.team, u.x, u.y);
    if (!tc) {
      u.task = 'idle';
      return;
    }
    u.task = 'return';
    u.targetKind = 'building';
    u.targetId = tc.id;
    u.path = null;
    u.pathGoal = null;
    u.repathCd = 0;
  }

  taskReturn(u, dt, st) {
    let drop = this.buildingById.get(u.targetId);
    u.resumeGatherId = null;
    if (!drop || !drop.complete || drop.type !== 'towncenter') {
      const alt = this.findDropOff(u.team, u.x, u.y);
      if (!alt) {
        u.task = 'idle';
        return;
      }
      drop = alt;
      u.targetId = alt.id;
      u.path = null;
    }
    const cp = this.closestPointOnBuilding(drop, u.x, u.y, u.radius + 8);
    const inRange = this.approachPoint(u, cp.x, cp.y, 3, dt, st.speed);
    if (!inRange) return;

    if (u.carry > 0 && u.carryKind) {
      const amount = Math.floor(u.carry);
      if (amount > 0) {
        this.players[u.team].res[u.carryKind] += amount;
        if (u.team === 0) {
          this.addFloater(
            u.x,
            u.y - 18,
            `+${amount} ${RESOURCE_LABEL[u.carryKind]}`,
            u.carryKind === 'food' ? '#e5c07b' : u.carryKind === 'wood' ? '#c8a06a' : '#e8d05a',
          );
        }
        this.emit('deposit', { x: u.x, y: u.y, team: u.team, resource: u.carryKind });
      }
      u.carry = 0;
      u.carryKind = null;
    }
    const prev = u.lastResourceId ? this.resourceById.get(u.lastResourceId) : null;
    if (prev && prev.amount > 0) {
      u.task = 'gather';
      u.targetKind = 'resource';
      u.targetId = prev.id;
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
    } else {
      const next = this.findNearestResource(u.x, u.y, null);
      if (next && Math.hypot(next.x - u.x, next.y - u.y) < 260 && u.autoGather !== false) {
        u.task = 'gather';
        u.targetKind = 'resource';
        u.targetId = next.id;
        u.lastResourceId = next.id;
        u.path = null;
        u.pathGoal = null;
        u.repathCd = 0;
      } else {
        u.task = 'idle';
        u.targetKind = null;
        u.targetId = null;
      }
    }
  }

  taskBuild(u, dt, st) {
    const b = this.buildingById.get(u.targetId);
    if (!b || b.complete) {
      u.task = 'idle';
      u.targetId = null;
      u.targetKind = null;
      u.path = null;
      return;
    }
    const cp = this.closestPointOnBuilding(b, u.x, u.y, u.radius + 10);
    const inRange = this.approachPoint(u, cp.x, cp.y, 3, dt, st.speed);
    if (!inRange) return;
    u.building = true;
    u.walking = false;
    b.progress += st.build * dt;
    u.hammerSfx = (u.hammerSfx || 0) + dt;
    if (u.hammerSfx > 0.85) {
      u.hammerSfx = 0;
      this.emit('hammer', { x: b.x, y: b.y, team: u.team });
    }
    if (b.progress >= b.buildTime) this.completeBuilding(b);
  }

  taskAttack(u, dt, st) {
    const target = this.resolveTarget(u);
    if (!target) {
      u.targetId = null;
      u.targetKind = null;
      u.path = null;
      u.pathGoal = null;
      if (u.moveDest) u.task = 'move';
      else u.task = 'idle';
      return;
    }
    let gx;
    let gy;
    let arrive;
    if (target.__kind === 'building') {
      const pad = st.range * 0.5 + u.radius + 6;
      const cp = this.closestPointOnBuilding(target, u.x, u.y, pad);
      gx = cp.x;
      gy = cp.y;
      arrive = 2.5;
    } else {
      const dx = u.x - target.x;
      const dy = u.y - target.y;
      const d = Math.hypot(dx, dy) || 1;
      const stop = target.radius + u.radius + st.range * 0.5 + 2;
      gx = target.x + (dx / d) * stop;
      gy = target.y + (dy / d) * stop;
      arrive = 3;
    }
    const inRange = this.approachPoint(u, gx, gy, arrive, dt, st.speed);
    if (inRange && u.attackCd <= 0) {
      u.attackCd = st.atkCd;
      const dx = target.x - u.x;
      if (dx !== 0) u.facing = dx > 0 ? 1 : -1;
      if (st.ranged) {
        const mult = target.__kind === 'building' && st.vsBuilding ? st.vsBuilding : 1;
        this.spawnProjectile(u.x, u.y - 13, target, st.dmg * mult, u.team, 'arrow', st.projectileSpeed || 430);
        this.emit('bowshot', { x: u.x, y: u.y, team: u.team });
      } else {
        this.dealDamage(u, target);
      }
    }
  }

  applyDamage(target, amount, attackerTeam) {
    target.hp -= amount;
    target.flash = 1;
    this.emit('hit', { x: target.x, y: target.y, team: target.team, big: target.__kind === 'building' });
    this.addParticles(
      target.x,
      target.y - (target.__kind === 'building' ? 6 : 8),
      target.team === 0 ? '#ffd9a0' : '#ffb0a0',
      4,
      60,
    );
    if (target.hp > 0) return;
    if (target.__kind === 'unit') {
      if (attackerTeam === 0) this.stats.kills++;
      if (target.team === 0) this.stats.losses++;
      this.addParticles(target.x, target.y, '#d8d0c0', 10, 90);
      this.emit('death', { x: target.x, y: target.y, team: target.team });
      this.removeUnit(target);
    } else {
      this.addParticles(target.x, target.y, '#cbb894', 22, 130);
      this.emit('collapse', { x: target.x, y: target.y, team: target.team });
      this.removeBuilding(target);
    }
  }

  dealDamage(attacker, target) {
    const st = UNIT_STATS[attacker.type];
    const mult = target.__kind === 'building' && st.vsBuilding ? st.vsBuilding : 1;
    this.applyDamage(target, st.dmg * mult, attacker.team);
  }

  // Arrows travel to the target and only land damage on arrival.
  spawnProjectile(x, y, target, dmg, team, sprite = 'arrow', speed = 430) {
    this.arrows.push({
      x,
      y,
      targetId: target.id,
      targetKind: target.__kind,
      dmg,
      team,
      sprite,
      speed,
      angle: 0,
      life: 3,
      max: 0.2,
    });
  }

  updateProjectiles(dt) {
    for (let i = this.arrows.length - 1; i >= 0; i--) {
      const a = this.arrows[i];
      const t = a.targetKind === 'unit'
        ? this.unitById.get(a.targetId)
        : this.buildingById.get(a.targetId);
      const tx = t ? t.x : a.x;
      const ty = t ? t.y - (t.__kind === 'building' ? 4 : 8) : a.y;
      const dx = tx - a.x;
      const dy = ty - a.y;
      const d = Math.hypot(dx, dy) || 1;
      a.angle = Math.atan2(dy, dx);
      const step = a.speed * dt;
      if (d <= step) {
        if (t && t.hp > 0) this.applyDamage(t, a.dmg, a.team);
        this.arrows.splice(i, 1);
        continue;
      }
      a.x += (dx / d) * step;
      a.y += (dy / d) * step;
      a.life -= dt;
      if (a.life <= 0) this.arrows.splice(i, 1);
    }
  }

  // Completed town centres loose arrows at the nearest hostile unit.
  updateBuildingAttacks(dt) {
    for (const b of this.buildings) {
      const st = BUILDING_STATS[b.type];
      if (!b.complete || !st.attack) continue;
      b.attackCd = Math.max(0, (b.attackCd || 0) - dt);
      if (b.attackCd > 0) continue;
      let target = null;
      let bestD = st.range * st.range;
      for (const u of this.units) {
        if (u.team === b.team) continue;
        const d = (u.x - b.x) ** 2 + (u.y - b.y) ** 2;
        if (d < bestD) {
          bestD = d;
          target = u;
        }
      }
      if (!target) continue;
      b.attackCd = st.atkCd;
      b.aimPulse = 1;
      // Crown Age reinforces towers.
      let dmg = st.attack;
      if (b.type === 'watchtower' && this.players[b.team].age >= 2) dmg *= 1.6;
      this.spawnProjectile(
        b.x + ((b.id % 5) - 2),
        b.y - (b.h * TILE) / 2 - 12,
        target,
        dmg,
        b.team,
        'arrow',
        430,
      );
      this.emit('arrow', { x: b.x, y: b.y, team: b.team });
    }
  }

  // ---------------------------------------------------------------- upkeep

  updateStuck(u, dt) {
    u.stuckTimer += dt;
    if (u.stuckTimer < 0.7) return;
    const moved = Math.hypot(u.x - u.lastX, u.y - u.lastY);
    const wantsToMove = u.task === 'move' || u.task === 'gather' || u.task === 'attack' || u.task === 'build' || u.task === 'return';
    if (moved < 2.5 && wantsToMove) {
      u.path = null;
      u.pathGoal = null;
      u.repathCd = 0;
      // Deterministic nudge (keeps runs reproducible for verification).
      const ang = (u.id * 2.399963229728653 + this.time * 1.7) % (Math.PI * 2);
      u.x = clamp(u.x + Math.cos(ang) * 3, 12, WORLD_W - 12);
      u.y = clamp(u.y + Math.sin(ang) * 3, 12, WORLD_H - 12);
    }
    u.lastX = u.x;
    u.lastY = u.y;
    u.stuckTimer = 0;
  }

  keepOutOfWalls(u, dt) {
    const c = Math.floor(u.x / TILE);
    const r = Math.floor(u.y / TILE);
    if (!this.nav.isBlocked(c, r)) return;
    for (let ring = 1; ring <= 4; ring++) {
      for (let dy = -ring; dy <= ring; dy++) {
        for (let dx = -ring; dx <= ring; dx++) {
          if (Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue;
          const nc = c + dx;
          const nr = r + dy;
          if (this.nav.isBlocked(nc, nr)) continue;
          const tx = nc * TILE + TILE / 2;
          const ty = nr * TILE + TILE / 2;
          const d = Math.hypot(tx - u.x, ty - u.y) || 1;
          const step = Math.min(90 * dt, d);
          u.x += ((tx - u.x) / d) * step;
          u.y += ((ty - u.y) / d) * step;
          return;
        }
      }
    }
  }

  separateUnits() {
    const units = this.units;
    for (let i = 0; i < units.length; i++) {
      const a = units[i];
      for (let j = i + 1; j < units.length; j++) {
        const b = units[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const minD = a.radius + b.radius;
        const d2 = dx * dx + dy * dy;
        if (d2 >= minD * minD) continue;
        if (d2 < 0.0001) {
          a.x -= 0.6;
          b.x += 0.6;
          continue;
        }
        const d = Math.sqrt(d2);
        const push = (minD - d) / 2;
        const nx = dx / d;
        const ny = dy / d;
        a.x -= nx * push;
        a.y -= ny * push;
        b.x += nx * push;
        b.y += ny * push;
      }
    }
  }

  updateEffects(dt) {
    for (let i = this.floaters.length - 1; i >= 0; i--) {
      const f = this.floaters[i];
      f.life -= dt;
      f.y -= dt * 16;
      if (f.life <= 0) this.floaters.splice(i, 1);
    }
    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i];
      r.life -= dt;
      if (r.life <= 0) this.rings.splice(i, 1);
    }
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.life -= dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vx *= 0.94;
      p.vy *= 0.94;
      if (p.life <= 0) this.particles.splice(i, 1);
    }
  }

  /**
   * Transient ring drawn where the player clicked, so a click always has a
   * visible answer even when nothing changes.
   */
  spawnRing(x, y, radius, color = '#ffffff', dur = 0.5, width = 2.2) {
    this.rings.push({
      x,
      y,
      r0: radius * 0.62,
      r1: radius * 1.5,
      life: dur,
      max: dur,
      color,
      width,
    });
    if (this.rings.length > 24) this.rings.shift();
  }

  // Ring sized to whatever was under the cursor, or a small ground ring.
  ringFor(target, x, y) {
    if (!target) {
      this.spawnRing(x, y, 12, 'rgba(240,230,200,0.85)', 0.4, 1.8);
      return;
    }
    if (target.__kind === 'building') {
      const r = (Math.max(target.w, target.h) * TILE) / 2 + 4;
      this.spawnRing(target.x, target.y + target.h * TILE * 0.22, r, '#ffe9a8', 0.55, 2.6);
      return;
    }
    const r = (target.radius || 10) + 7;
    this.spawnRing(target.x, target.y + 4, r, target.team === undefined || target.team === 0 ? '#c8ffa0' : '#ffb3a6', 0.5, 2.2);
  }

  addFloater(x, y, text, color) {
    this.floaters.push({ x, y, text, color: color || '#ffffff', life: 1.5, max: 1.5 });
    if (this.floaters.length > 40) this.floaters.shift();
  }

  addParticles(x, y, color, count, speed) {
    if (this.particles.length > 320) return;
    for (let i = 0; i < count; i++) {
      const a = (this.particleSeed = ((this.particleSeed || 1) * 16807) % 2147483647) / 2147483647 * Math.PI * 2;
      const s = speed * (0.4 + Math.random() * 0.8);
      this.particles.push({
        x,
        y,
        vx: Math.cos(a) * s,
        vy: Math.sin(a) * s,
        life: 0.35 + Math.random() * 0.4,
        max: 0.75,
        color,
        size: 1.5 + Math.random() * 2,
      });
    }
  }

  checkEnd() {
    if (this.state !== 'playing') return;
    let alive = [false, false];
    for (const b of this.buildings) {
      if (b.type === 'towncenter' && b.hp > 0) alive[b.team] = true;
    }
    if (!alive[1]) {
      this.state = 'won';
      this.endTime = this.time;
      this.emit('victory', {});
    } else if (!alive[0]) {
      this.state = 'lost';
      this.endTime = this.time;
      this.emit('defeat', {});
    }
  }

  // ---------------------------------------------------------------- main tick

  update(dt) {
    if (this.state !== 'playing') {
      this.updateEffects(dt);
      return;
    }
    dt = Math.min(dt, 0.05);
    this.time += dt;

    this.fogTimer -= dt;
    if (this.fogTimer <= 0) {
      this.fogTimer = FOG.refresh;
      this.updateFog();
    }

    // Buildings: finish construction, advance training queues.
    this.updateBuildingAttacks(dt);
    for (const b of this.buildings) {
      b.flash = Math.max(0, b.flash - dt * 3);
      b.aimPulse = Math.max(0, (b.aimPulse || 0) - dt * 4);
      if (!b.complete) {
        if (b.progress >= b.buildTime) this.completeBuilding(b);
        continue;
      }
      if (b.research) {
        b.research.elapsed += dt;
        if (b.research.elapsed >= b.research.time) {
          const p = this.players[b.team];
          p.age = Math.max(p.age, b.research.to);
          b.research = null;
          this.emit('age-up', { x: b.x, y: b.y, team: b.team, age: p.age });
          this.addFloater(b.x, b.y - b.h * TILE * 0.5 - 26, `${AGES[p.age].name}!`, b.team === 0 ? '#ffe9a8' : '#ffcdbf');
        }
        continue;
      }
      if (b.queue.length) {
        const item = b.queue[0];
        item.elapsed += dt;
        if (item.elapsed >= item.time) {
          b.queue.shift();
          const spot = this.freeSpotNearBuilding(b);
          const u = this.createUnit(item.type, b.team, spot.x, spot.y);
          u.moveDest = null;
          if (b.team === 0) this.stats.trained++;
          this.emit('trained', { x: u.x, y: u.y, team: b.team, unitType: item.type });
        }
      }
    }

    for (const u of this.units) this.updateUnit(u, dt);
    this.updateProjectiles(dt);
    this.separateUnits();
    for (const u of this.units) {
      u.x = clamp(u.x, 12, WORLD_W - 12);
      u.y = clamp(u.y, 12, WORLD_H - 12);
    }

    updateAI(this, dt, 1);
    this.updateEffects(dt);
    this.checkEnd();
  }

  drainEvents() {
    if (!this.events.length) return [];
    const out = this.events;
    this.events = [];
    return out;
  }
}

export { TEAM_COLORS };
