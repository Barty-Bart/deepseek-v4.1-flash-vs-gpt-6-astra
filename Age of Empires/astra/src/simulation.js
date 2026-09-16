import { MAP_SIZE, BUILDINGS, UNITS, AGES, seededRandom } from "./data.js";

import { Visibility } from "./visibility.js";

const key = (x, y) => y * MAP_SIZE + x;
const center = (e) => ({ x: e.x + (e.w || 0) / 2, y: e.y + (e.h || 0) / 2 });
export const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
export function distanceTo(unit, target) {
  if (!target.w) return distance(unit, target);
  return Math.hypot(
    unit.x - Math.max(target.x, Math.min(unit.x, target.x + target.w)),
    unit.y - Math.max(target.y, Math.min(unit.y, target.y + target.h)),
  );
}
export class Game {
  constructor(seed = 73421) {
    this.seed = seed;
    this.random = seededRandom(seed);
    this.nextId = 1;
    this.time = 0;
    this.status = "ready";
    this.paused = false;
    this.units = [];
    this.buildings = [];
    this.resources = [];
    this.effects = [];
    this.events = [];
    this.listeners = [];
    this.terrain = new Uint8Array(MAP_SIZE * MAP_SIZE);
    this.blocked = new Uint8Array(MAP_SIZE * MAP_SIZE);
    this.teams = {
      player: { food: 240, wood: 260, gold: 130 },
      enemy: { food: 240, wood: 300, gold: 150 },
    };
    this.ages = { player: 1, enemy: 1 };
    this.projectiles = [];
    this.fog = new Visibility(this);
    this.fogTimer = 0;
    this.stats = { gathered: 0, built: 0, trained: 0, kills: 0, lost: 0 };
    this.goals = { gather: false, house: false, barracks: false, army: false };
    this.ai = { nextThink: 3, nextRaid: 115, raids: 0, lastAlert: -30 };
    this.generateMap();
    this.fog.update();
  }
  emit(type, data = {}) {
    const e = { type, ...data };
    this.events.push(e);
    if (this.events.length > 100) this.events.shift();
    for (const fn of this.listeners) fn(e);
  }
  unitStats(u) {
    const bonus = this.ages[u.team] - 1,
      base = UNITS[u.type];
    return {
      ...base,
      hp: base.hp + (u.type === "soldier" ? 20 * bonus : 0),
      damage: base.damage + (u.type === "soldier" ? 3 * bonus : 0),
    };
  }
  buildingMaxHp(type, team) {
    return (
      BUILDINGS[type].hp + (type === "tower" ? 200 * (this.ages[team] - 1) : 0)
    );
  }
  towerStats(b) {
    const bonus = this.ages[b.team] - 1;
    return { damage: 12 + 6 * bonus, range: 7 + bonus, cooldown: 1.4 };
  }
  visionRadius(e) {
    if (e.kind === "unit") return e.type === "soldier" ? 6.5 : 5;
    if (!e.complete) return 2.5;
    return e.type === "town"
      ? 8
      : e.type === "tower"
        ? 10 + this.ages[e.team] - 1
        : e.type === "barracks"
          ? 5
          : 4;
  }
  advance(b) {
    if (!b || b.type !== "town" || !b.complete || b.hp <= 0)
      return { ok: false, reason: "Advance at a completed town centre." };
    if (b.research)
      return { ok: false, reason: "Your civilization is already advancing." };
    const next = this.ages[b.team] + 1,
      def = AGES[next];
    if (!def)
      return {
        ok: false,
        reason: "Your civilization has reached the Citadel Age.",
      };
    if (!this.afford(b.team, def.cost))
      return {
        ok: false,
        reason:
          "Advancement needs " +
          Object.entries(def.cost)
            .map(([r, n]) => `${n} ${r}`)
            .join(" and ") +
          ".",
      };
    this.pay(b.team, def.cost);
    b.research = { age: next, progress: 0 };
    return { ok: true };
  }
  cancelAdvance(b) {
    if (!b?.research) return;
    this.pay(b.team, AGES[b.research.age].cost, -1);
    b.research = null;
  }
  completeAdvance(team, age) {
    this.ages[team] = age;
    for (const u of this.units.filter((u) => u.team === team)) {
      const hp = this.unitStats(u).hp;
      u.hp += hp - u.maxHp;
      u.maxHp = hp;
    }
    for (const b of this.buildings.filter((b) => b.team === team)) {
      const hp = this.buildingMaxHp(b.type, team);
      b.hp += (hp - b.maxHp) * (b.complete ? 1 : 0.12 + 0.88 * b.progress);
      b.maxHp = hp;
      b.age = age;
    }
    this.fog.update();
    this.emit("age-advanced", { team, age });
  }
  updateTower(b, dt) {
    b.cooldown = Math.max(0, b.cooldown - dt);
    const stats = this.towerStats(b),
      source = center(b);
    const inRange = (u) =>
      u &&
      u.hp > 0 &&
      u.team !== b.team &&
      distance(source, u) <= stats.range &&
      (b.team !== "player" || this.fog.canSee(u));
    let target = this.get(b.targetId);
    if (!inRange(target))
      target = this.units
        .filter(inRange)
        .sort((a, c) => distance(source, a) - distance(source, c))[0];
    b.targetId = target?.id || null;
    if (!target || b.cooldown > 0) return;
    b.cooldown = stats.cooldown;
    const duration = Math.max(0.18, distance(source, target) / 12);
    this.projectiles.push({
      x: source.x,
      y: source.y,
      toX: target.x,
      toY: target.y,
      team: b.team,
      targetId: target.id,
      sourceId: b.id,
      damage: stats.damage,
      duration,
      remaining: duration,
    });
    this.emit("arrow", { x: source.x, y: source.y });
  }
  updateProjectiles(dt) {
    for (const arrow of this.projectiles) {
      arrow.remaining -= dt;
      if (arrow.remaining > 0) continue;
      const target = this.get(arrow.targetId);
      if (!target || target.hp <= 0) continue;
      target.hp -= arrow.damage;
      target.hitFlash = 0.2;
      this.effects.push({ kind: "hit", x: target.x, y: target.y, life: 0.23 });
      this.emit("hit", { x: target.x, y: target.y, team: arrow.team });
      if (target.team === "player" && this.time - this.ai.lastAlert > 18) {
        this.ai.lastAlert = this.time;
        this.emit("attack-alert", { target });
      }
      const tower = this.get(arrow.sourceId);
      if (
        tower &&
        (target.type === "soldier" || target.order.kind === "idle") &&
        target.order.kind !== "attack"
      )
        this.commandAttack(target, tower);
    }
    this.projectiles = this.projectiles.filter((p) => p.remaining > 0);
  }
  generateMap() {
    for (let y = 0; y < MAP_SIZE; y++)
      for (let x = 0; x < MAP_SIZE; x++) {
        const pond =
          ((x - 30) / 4.4) ** 2 + ((y - 32) / 3.7) ** 2 < 1 ||
          ((x - 9) / 3.3) ** 2 + ((y - 9) / 2.8) ** 2 < 1;
        if (pond) this.terrain[key(x, y)] = 1;
      }
    this.addBuilding("town", "player", 12, 30, true);
    this.addBuilding("town", "enemy", 33, 9, true);
    this.addBuilding("house", "enemy", 38, 11, true);
    this.addBuilding("barracks", "enemy", 32, 15, true);
    const patches = [
      [7, 28, 22, "wood"],
      [8, 37, 22, "wood"],
      [19, 36, 19, "wood"],
      [19, 20, 19, "wood"],
      [29, 6, 19, "wood"],
      [40, 18, 22, "wood"],
      [40, 6, 16, "wood"],
      [5, 18, 15, "wood"],
      [26, 43, 15, "wood"],
      [41, 39, 22, "wood"],
      [22, 8, 16, "wood"],
      [34, 23, 12, "wood"],
      [6, 42, 16, "wood"],
    ];
    for (const [cx, cy, n, type] of patches)
      for (let i = 0; i < n; i++) {
        const x = Math.round(cx + (this.random() - 0.5) * 7),
          y = Math.round(cy + (this.random() - 0.5) * 6);
        if (this.canResource(x, y))
          this.addResource(type, x, y, 200 + Math.floor(this.random() * 80));
      }
    // Keep the opening workers and their berry patch easy to see and click.
    this.resources = this.resources.filter(
      (r) =>
        !(
          r.type === "wood" &&
          r.x >= 14 &&
          r.x <= 18 &&
          r.y >= 30 &&
          r.y <= 35
        ),
    );
    for (const [cx, cy, type] of [
      [17, 32, "food"],
      [30, 11, "food"],
      [18, 26, "gold"],
      [37, 7, "gold"],
      [26, 23, "gold"],
      [13, 19, "food"],
      [38, 29, "food"],
    ]) {
      for (const [dx, dy] of [
        [0, 0],
        [1, 0],
        [0, 1],
        [1, 1],
        [-1, 1],
      ])
        if (this.canResource(cx + dx, cy + dy))
          this.addResource(type, cx + dx, cy + dy, type === "gold" ? 650 : 300);
    }
    this.rebuildBlocked();
    [
      [15.5, 32.5],
      [15.5, 33.5],
      [13.5, 34.5],
    ].forEach(([x, y]) => this.addUnit("villager", "player", x, y));
    [
      [32.5, 12.5],
      [35.5, 13.5],
      [36.5, 10.5],
      [32.5, 9.5],
    ].forEach(([x, y]) => this.addUnit("villager", "enemy", x, y));
    this.addUnit("soldier", "enemy", 35.5, 16.5);
    this.units
      .filter((u) => u.team === "enemy" && u.type === "villager")
      .forEach((u, i) =>
        this.assignGather(u, ["food", "wood", "gold", "food"][i]),
      );
  }
  canResource(x, y) {
    return (
      x > 1 &&
      y > 1 &&
      x < MAP_SIZE - 2 &&
      y < MAP_SIZE - 2 &&
      !this.terrain[key(x, y)] &&
      !this.buildings.some(
        (b) =>
          x >= b.x - 1 &&
          x < b.x + b.w + 1 &&
          y >= b.y - 1 &&
          y < b.y + b.h + 1,
      ) &&
      !this.resources.some((r) => r.x === x && r.y === y)
    );
  }
  addResource(type, x, y, amount) {
    const r = {
      id: this.nextId++,
      kind: "resource",
      type,
      x,
      y,
      w: 1,
      h: 1,
      amount,
      variant: Math.floor(this.random() * 5),
    };
    this.resources.push(r);
    return r;
  }
  addBuilding(type, team, x, y, complete = false) {
    const def = BUILDINGS[type];
    const hp = this.buildingMaxHp(type, team);
    const b = {
      id: this.nextId++,
      kind: "building",
      type,
      team,
      x,
      y,
      w: def.w,
      h: def.h,
      hp: complete ? hp : hp * 0.12,
      maxHp: hp,
      age: this.ages[team],
      research: null,
      cooldown: 0,
      targetId: null,
      progress: complete ? 1 : 0,
      complete,
      queue: [],
      rally: null,
      amount: type === "farm" ? 2400 : 0,
      hitFlash: 0,
    };
    this.buildings.push(b);
    this.rebuildBlocked();
    return b;
  }
  addUnit(type, team, x, y) {
    if (!this.walkable(Math.floor(x), Math.floor(y))) {
      const open = this.nearestOpen(x, y);
      if (open) {
        x = open.x + 0.5;
        y = open.y + 0.5;
      }
    }
    const def = this.unitStats({ type, team });
    const u = {
      id: this.nextId++,
      kind: "unit",
      type,
      team,
      x,
      y,
      hp: def.hp,
      maxHp: def.hp,
      order: { kind: "idle" },
      path: [],
      carry: 0,
      carryType: null,
      gatherTarget: null,
      cooldown: 0,
      repath: 0,
      scan: 0,
      hitFlash: 0,
      angle: 0,
      anim: this.random() * 6,
      work: 0,
    };
    this.units.push(u);
    return u;
  }
  get(id) {
    return (
      this.units.find((e) => e.id === id) ||
      this.buildings.find((e) => e.id === id) ||
      this.resources.find((e) => e.id === id)
    );
  }
  town(team) {
    return this.buildings.find(
      (b) => b.type === "town" && b.team === team && b.hp > 0,
    );
  }
  pop(team) {
    return this.units.filter((u) => u.team === team && u.hp > 0).length;
  }
  cap(team) {
    return Math.min(
      60,
      this.buildings
        .filter((b) => b.team === team && b.complete && b.hp > 0)
        .reduce((n, b) => n + (BUILDINGS[b.type].pop || 0), 0),
    );
  }
  queued(team) {
    return this.buildings
      .filter((b) => b.team === team)
      .reduce((n, b) => n + b.queue.length, 0);
  }
  afford(team, cost) {
    return Object.entries(cost).every(([k, v]) => this.teams[team][k] >= v);
  }
  pay(team, cost, mult = 1) {
    for (const [k, v] of Object.entries(cost)) this.teams[team][k] -= v * mult;
  }
  rebuildBlocked() {
    this.blocked.set(this.terrain);
    for (const e of [
      ...this.buildings.filter((b) => b.hp > 0),
      ...this.resources.filter((r) => r.amount > 0),
    ])
      for (let y = e.y; y < e.y + e.h; y++)
        for (let x = e.x; x < e.x + e.w; x++)
          if (x >= 0 && y >= 0 && x < MAP_SIZE && y < MAP_SIZE)
            this.blocked[key(x, y)] = 1;
  }
  walkable(x, y) {
    return (
      x >= 0 &&
      y >= 0 &&
      x < MAP_SIZE &&
      y < MAP_SIZE &&
      !this.blocked[key(x, y)]
    );
  }
  accessTiles(e) {
    const x = Math.floor(e.x),
      y = Math.floor(e.y),
      w = e.w || 1,
      h = e.h || 1,
      result = [];
    for (let yy = y - 1; yy <= y + h; yy++)
      for (let xx = x - 1; xx <= x + w; xx++)
        if (
          (xx < x || xx >= x + w || yy < y || yy >= y + h) &&
          this.walkable(xx, yy)
        )
          result.push({ x: xx, y: yy });
    return result;
  }
  nearestOpen(x, y) {
    x = Math.floor(x);
    y = Math.floor(y);
    for (let r = 0; r < 12; r++) {
      const points = [];
      for (let yy = y - r; yy <= y + r; yy++)
        for (let xx = x - r; xx <= x + r; xx++)
          if (this.walkable(xx, yy)) points.push({ x: xx, y: yy });
      if (points.length)
        return points.sort(
          (a, b) => distance(a, { x, y }) - distance(b, { x, y }),
        )[0];
    }
    return null;
  }
  findPath(unit, goals) {
    if (!goals?.length) return null;
    const sx = Math.floor(unit.x),
      sy = Math.floor(unit.y),
      start = key(sx, sy),
      goalSet = new Set(goals.map((p) => key(p.x, p.y)));
    if (goalSet.has(start))
      return distance(unit, { x: sx + 0.5, y: sy + 0.5 }) > 0.08
        ? [{ x: sx + 0.5, y: sy + 0.5 }]
        : [];
    const heuristic = (x, y) =>
      Math.min(
        ...goals.map((p) => {
          const dx = Math.abs(x - p.x),
            dy = Math.abs(y - p.y);
          return Math.max(dx, dy) + 0.4142 * Math.min(dx, dy);
        }),
      );
    const size = MAP_SIZE * MAP_SIZE,
      score = new Float32Array(size).fill(Infinity),
      from = new Int32Array(size).fill(-1),
      closed = new Uint8Array(size);
    score[start] = 0;
    const open = [{ k: start, f: heuristic(sx, sy) }];
    let loops = 0;
    while (open.length && loops++ < size) {
      let best = 0;
      for (let i = 1; i < open.length; i++)
        if (open[i].f < open[best].f) best = i;
      const current = open.splice(best, 1)[0].k;
      if (closed[current]) continue;
      if (goalSet.has(current)) {
        const path = [];
        let k = current;
        while (k !== start && k !== -1) {
          path.push({
            x: (k % MAP_SIZE) + 0.5,
            y: Math.floor(k / MAP_SIZE) + 0.5,
          });
          k = from[k];
        }
        return path.reverse();
      }
      closed[current] = 1;
      const x = current % MAP_SIZE,
        y = Math.floor(current / MAP_SIZE);
      for (const [dx, dy] of [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
        [1, 1],
        [-1, 1],
        [1, -1],
        [-1, -1],
      ]) {
        const xx = x + dx,
          yy = y + dy;
        if (
          !this.walkable(xx, yy) ||
          (dx && dy && (!this.walkable(x + dx, y) || !this.walkable(x, y + dy)))
        )
          continue;
        const k = key(xx, yy);
        if (closed[k]) continue;
        const next = score[current] + (dx && dy ? 1.4142 : 1);
        if (next < score[k]) {
          score[k] = next;
          from[k] = current;
          open.push({ k, f: next + heuristic(xx, yy) });
        }
      }
    }
    return null;
  }
  routeTo(u, target) {
    const goals = target.w
      ? this.accessTiles(target)
      : [this.nearestOpen(target.x, target.y)].filter(Boolean);
    const path = this.findPath(u, goals);
    u.path = path || [];
    u.repath = 1;
    return path !== null;
  }
  moveUnit(u, dt) {
    if (!u.path.length) return true;
    const p = u.path[0];
    if (!this.walkable(Math.floor(p.x), Math.floor(p.y))) {
      u.path = [];
      u.repath = 0;
      return false;
    }
    const dx = p.x - u.x,
      dy = p.y - u.y,
      d = Math.hypot(dx, dy),
      step = UNITS[u.type].speed * dt;
    u.angle = Math.atan2(dy, dx);
    u.anim += dt * 8;
    if (d <= step) {
      u.x = p.x;
      u.y = p.y;
      u.path.shift();
    } else {
      u.x += (dx / d) * step;
      u.y += (dy / d) * step;
    }
    return !u.path.length;
  }
  placement(type, x, y, team = "player") {
    const d = BUILDINGS[type];
    if (!d || type === "town")
      return { ok: false, reason: "Choose a building." };
    if (!this.afford(team, d.cost))
      return { ok: false, reason: "Not enough resources." };
    if (x < 1 || y < 1 || x + d.w >= MAP_SIZE || y + d.h >= MAP_SIZE)
      return { ok: false, reason: "Build inside the borderlands." };
    for (let yy = y; yy < y + d.h; yy++)
      for (let xx = x; xx < x + d.w; xx++)
        if (team === "player" && this.fog.state(xx, yy) !== 2)
          return {
            ok: false,
            reason: "Explore this site with a unit before building here.",
          };
        else if (!this.walkable(xx, yy))
          return {
            ok: false,
            reason: "Keep buildings clear of trees, water and other buildings.",
          };
    if (
      this.units.some(
        (u) =>
          u.hp > 0 && u.x >= x && u.x < x + d.w && u.y >= y && u.y < y + d.h,
      )
    )
      return {
        ok: false,
        reason: "A unit is standing here. Choose an empty space.",
      };
    if (!this.accessTiles({ x, y, w: d.w, h: d.h }).length)
      return { ok: false, reason: "Villagers need a clear approach." };
    return { ok: true };
  }
  construct(type, x, y, workers, team = "player") {
    const valid = this.placement(type, x, y, team);
    if (!valid.ok) return valid;
    workers = workers.filter(
      (u) => u?.team === team && u.type === "villager" && u.hp > 0,
    );
    if (!workers.length)
      return { ok: false, reason: "Select a villager to build." };
    const d = BUILDINGS[type],
      site = { x, y, w: d.w, h: d.h };
    if (!workers.some((u) => this.findPath(u, this.accessTiles(site)) !== null))
      return { ok: false, reason: "Your villagers cannot reach this site." };
    this.pay(team, d.cost);
    const b = this.addBuilding(type, team, x, y);
    for (const u of workers) this.commandBuild(u, b);
    if (team === "player") this.emit("build", { building: b });
    return { ok: true, building: b };
  }
  commandBuild(u, b) {
    u.order = { kind: "build", targetId: b.id };
    u.path = [];
    this.routeTo(u, b);
  }
  train(b, type) {
    if (!b || !b.complete || b.hp <= 0 || BUILDINGS[b.type].trains !== type)
      return { ok: false, reason: "This building cannot train that unit." };
    const d = UNITS[type];
    if (b.queue.length >= 5)
      return { ok: false, reason: "The training queue is full." };
    if (this.pop(b.team) + this.queued(b.team) >= this.cap(b.team))
      return {
        ok: false,
        reason: "Population limit reached. Build another house.",
      };
    if (!this.afford(b.team, d.cost))
      return { ok: false, reason: "Not enough resources." };
    this.pay(b.team, d.cost);
    b.queue.push({ type, progress: 0 });
    return { ok: true };
  }
  cancelTrain(b, index) {
    if (!b?.queue[index]) return;
    const item = b.queue.splice(index, 1)[0];
    this.pay(b.team, UNITS[item.type].cost, -1);
  }
  commandMove(units, x, y) {
    const spacing = 0.85,
      cols = Math.ceil(Math.sqrt(units.length));
    units.forEach((u, i) => {
      const tx = x + ((i % cols) - (cols - 1) / 2) * spacing,
        ty = y + (Math.floor(i / cols) - (cols - 1) / 2) * spacing;
      const goal = this.nearestOpen(tx, ty);
      if (!goal) return;
      u.order = { kind: "move", x: goal.x + 0.5, y: goal.y + 0.5 };
      this.routeTo(u, u.order);
    });
  }
  commandAttack(u, target) {
    u.order = {
      kind: "attack",
      targetId: target.id,
      strategic: target.kind === "building" ? target.id : null,
      lastKnown: center(target),
    };
    this.routeTo(u, target);
  }
  commandGather(u, target) {
    if (u.type !== "villager") return;
    const type = target.kind === "building" ? "food" : target.type;
    u.gatherTarget = target.id;
    if (u.carry > 0 && u.carryType !== type) {
      u.order = { kind: "return" };
      const t = this.town(u.team);
      if (t) this.routeTo(u, t);
      return;
    }
    u.order = { kind: "gather", targetId: target.id, resourceType: type };
    u.path = [];
    this.routeTo(u, target);
  }
  assignGather(u, type) {
    const pool = [
      ...this.resources.filter((r) => r.type === type && r.amount > 0),
      ...this.buildings.filter(
        (b) =>
          b.type === "farm" &&
          b.team === u.team &&
          b.complete &&
          b.amount > 0 &&
          type === "food",
      ),
    ];
    pool.sort((a, b) => distance(u, center(a)) - distance(u, center(b)));
    for (const r of pool) {
      if (this.findPath(u, this.accessTiles(r)) !== null) {
        this.commandGather(u, r);
        return true;
      }
    }
    u.order = { kind: "idle" };
    return false;
  }
  start() {
    this.status = "playing";
    this.paused = false;
  }
  tick(dt) {
    if (this.status !== "playing" || this.paused) return;
    this.time += dt;
    this.fogTimer -= dt;
    if (this.fogTimer <= 0) {
      this.fog.update();
      this.fogTimer = 0.15;
    }
    this.updateProjectiles(dt);
    this.effects = this.effects.filter((e) => (e.life -= dt) > 0);
    for (const b of this.buildings) {
      b.hitFlash = Math.max(0, b.hitFlash - dt);
      if (b.hp <= 0 || !b.complete) continue;
      if (b.type === "tower") this.updateTower(b, dt);
      if (b.research) {
        b.research.progress += dt / AGES[b.research.age].time;
        if (b.research.progress >= 1) {
          const age = b.research.age;
          b.research = null;
          this.completeAdvance(b.team, age);
        }
        continue;
      }
      if (!b.queue.length) continue;
      if (this.pop(b.team) >= this.cap(b.team)) continue;
      const q = b.queue[0];
      q.progress += dt / UNITS[q.type].time;
      if (q.progress >= 1) {
        const spawnScore = (p) =>
          distance(p, { x: b.x + b.w / 2, y: b.y + b.h + 1 }) +
          this.units.filter(
            (u) => distance(u, { x: p.x + 0.5, y: p.y + 0.5 }) < 0.8,
          ).length *
            4;
        const spawn = this.accessTiles(b).sort(
          (a, c) => spawnScore(a) - spawnScore(c),
        )[0];
        if (spawn) {
          const u = this.addUnit(q.type, b.team, spawn.x + 0.5, spawn.y + 0.5);
          b.queue.shift();
          if (b.rally) this.commandMove([u], b.rally.x, b.rally.y);
          if (b.team === "player") {
            this.stats.trained++;
            this.emit("trained", { unit: u });
          } else if (u.type === "villager") {
            const workers = this.units.filter(
              (v) => v.team === "enemy" && v.type === "villager",
            );
            this.assignGather(
              u,
              workers.length % 3 === 0
                ? "wood"
                : workers.length % 3 === 1
                  ? "gold"
                  : "food",
            );
          }
        }
      }
    }
    for (const u of this.units) if (u.hp > 0) this.updateUnit(u, dt);
    this.separateUnits(dt);
    this.cleanDead();
    if (this.status === "playing" && this.time >= this.ai.nextThink) {
      this.ai.nextThink = this.time + 3;
      this.updateAI();
    }
    this.goals.army =
      this.goals.army ||
      this.units.filter((u) => u.team === "player" && u.type === "soldier")
        .length >= 4;
  }
  separateUnits(dt) {
    // Gentle separation keeps armies readable without making units hard pathfinding obstacles.
    const push = (u, dx, dy) => {
      const x = u.x + dx,
        y = u.y + dy,
        tx = Math.floor(x),
        ty = Math.floor(y),
        sx = Math.floor(u.x),
        sy = Math.floor(u.y);
      if (
        this.walkable(tx, ty) &&
        (tx === sx ||
          ty === sy ||
          (this.walkable(tx, sy) && this.walkable(sx, ty)))
      ) {
        u.x = x;
        u.y = y;
      }
    };
    for (let i = 0; i < this.units.length; i++)
      for (let j = i + 1; j < this.units.length; j++) {
        const a = this.units[i],
          b = this.units[j];
        // Workers must retain their approach to a resource or construction site.
        if (a.type !== "soldier" || b.type !== "soldier") continue;
        let dx = a.x - b.x,
          dy = a.y - b.y,
          d = Math.hypot(dx, dy);
        if (d >= 0.56 || a.hp <= 0 || b.hp <= 0) continue;
        const overlap = 0.56 - d;
        if (d < 0.001) {
          const angle = (a.id * 2.399 + b.id) * 1.7;
          dx = Math.cos(angle);
          dy = Math.sin(angle);
          d = 1;
        }
        const amount = overlap * 0.5 * Math.min(1, dt * 10);
        push(a, (dx / d) * amount, (dy / d) * amount);
        push(b, (-dx / d) * amount, (-dy / d) * amount);
      }
  }
  updateUnit(u, dt) {
    u.cooldown -= dt;
    u.repath -= dt;
    u.scan -= dt;
    u.hitFlash = Math.max(0, u.hitFlash - dt);
    if (u.type === "soldier" && u.scan <= 0) {
      u.scan = 0.6;
      const nearby = this.units
        .filter(
          (e) =>
            e.team !== u.team &&
            e.hp > 0 &&
            distance(u, e) < UNITS[u.type].sight,
        )
        .sort((a, b) => distance(u, a) - distance(u, b))[0];
      if (
        nearby &&
        (u.order.kind !== "attack" ||
          this.get(u.order.targetId)?.kind === "building" ||
          !this.get(u.order.targetId))
      ) {
        const resume = u.order.kind === "move" ? { ...u.order } : null;
        const strategic = u.order.strategic || null;
        u.order = { kind: "attack", targetId: nearby.id, resume, strategic };
        u.path = [];
        u.repath = 0;
      } else if (u.order.kind === "idle") {
        const b = this.buildings.find(
          (e) =>
            e.team !== u.team &&
            e.hp > 0 &&
            distanceTo(u, e) < UNITS[u.type].sight,
        );
        if (b) this.commandAttack(u, b);
      }
    }
    const o = u.order;
    if (o.kind === "idle") return;
    if (o.kind === "move") {
      if (!u.path.length && distance(u, o) > 0.7 && u.repath <= 0)
        this.routeTo(u, o);
      if (this.moveUnit(u, dt) && distance(u, o) < 0.8)
        u.order = { kind: "idle" };
      return;
    }
    if (o.kind === "gather") {
      const target = this.get(o.targetId);
      if (!target || target.amount <= 0) {
        this.assignGather(u, o.resourceType);
        return;
      }
      if (distanceTo(u, target) > 0.85) {
        if (!u.path.length && u.repath <= 0) this.routeTo(u, target);
        this.moveUnit(u, dt);
        return;
      }
      u.path = [];
      u.work += dt;
      u.anim += dt * 4;
      const rate =
        (o.resourceType === "gold"
          ? 2.1
          : o.resourceType === "wood"
            ? 2.5
            : 2.9) *
        (1 + (this.ages[u.team] - 1) * 0.15);
      const qty = Math.min(rate * dt, target.amount, 14 - u.carry);
      u.carry += qty;
      u.carryType = o.resourceType;
      target.amount -= qty;
      if (target.amount <= 0) {
        this.rebuildBlocked();
      }
      if (u.carry >= 13.99 || target.amount <= 0) {
        u.order = { kind: "return" };
        const town = this.town(u.team);
        if (town) this.routeTo(u, town);
      }
      return;
    }
    if (o.kind === "return") {
      const town = this.town(u.team);
      if (!town) {
        u.order = { kind: "idle" };
        return;
      }
      if (distanceTo(u, town) > 0.85) {
        if (!u.path.length && u.repath <= 0) this.routeTo(u, town);
        this.moveUnit(u, dt);
        return;
      }
      if (u.carry > 0) {
        this.teams[u.team][u.carryType] += u.carry;
        if (u.team === "player") {
          this.stats.gathered += u.carry;
          this.goals.gather = true;
        }
        this.effects.push({
          kind: "delivery",
          x: u.x,
          y: u.y,
          text: `+${Math.round(u.carry)}`,
          color: u.carryType === "gold" ? "#e8bd59" : "#f6ecd0",
          life: 1.4,
        });
      }
      const type = u.carryType;
      u.carry = 0;
      u.carryType = null;
      const target = this.get(u.gatherTarget);
      if (target && target.amount > 0) this.commandGather(u, target);
      else if (type) this.assignGather(u, type);
      else u.order = { kind: "idle" };
      return;
    }
    if (o.kind === "build") {
      const b = this.get(o.targetId);
      if (!b || b.hp <= 0) {
        u.order = { kind: "idle" };
        return;
      }
      if (b.complete) {
        if (b.type === "farm") this.commandGather(u, b);
        else u.order = { kind: "idle" };
        return;
      }
      if (distanceTo(u, b) > 0.9) {
        if (!u.path.length && u.repath <= 0) this.routeTo(u, b);
        this.moveUnit(u, dt);
        return;
      }
      u.path = [];
      u.anim += dt * 5;
      const progress = dt / BUILDINGS[b.type].time;
      b.progress = Math.min(1, b.progress + progress);
      b.hp = Math.min(b.maxHp, b.hp + progress * b.maxHp * 0.88);
      if (b.progress >= 1) {
        b.complete = true;
        if (b.team === "player") {
          this.stats.built++;
          if (b.type === "house") this.goals.house = true;
          if (b.type === "barracks") this.goals.barracks = true;
          this.emit("complete", { building: b });
        }
      }
      return;
    }
    if (o.kind === "attack") {
      const target = this.get(o.targetId);
      if (!target || target.hp <= 0) {
        const strategic = this.get(o.strategic);
        if (strategic && strategic.hp > 0) this.commandAttack(u, strategic);
        else if (o.resume) {
          u.order = o.resume;
          this.routeTo(u, o.resume);
        } else u.order = { kind: "idle" };
        return;
      }
      const d = distanceTo(u, target),
        def = this.unitStats(u);
      if (u.team === "player" && !this.fog.canSee(target)) {
        const lastKnown = o.lastKnown || center(target);
        this.commandMove([u], lastKnown.x, lastKnown.y);
        return;
      }
      o.lastKnown = center(target);
      if (d > def.range) {
        if (u.repath <= 0) this.routeTo(u, target);
        this.moveUnit(u, dt);
        return;
      }
      u.path = [];
      const p = center(target);
      u.angle = Math.atan2(p.y - u.y, p.x - u.x);
      if (u.cooldown <= 0) {
        u.cooldown = def.cooldown;
        target.hp -= def.damage;
        target.hitFlash = 0.2;
        u.anim += 2;
        this.effects.push({
          kind: "hit",
          x: (u.x + p.x) / 2,
          y: (u.y + p.y) / 2,
          life: 0.23,
        });
        this.emit("hit", { x: u.x, y: u.y, team: u.team });
        if (target.team === "player" && this.time - this.ai.lastAlert > 18) {
          this.ai.lastAlert = this.time;
          this.emit("attack-alert", { target });
        }
        if (
          target.kind === "unit" &&
          target.order.kind !== "attack" &&
          (target.type === "soldier" || target.order.kind === "idle")
        )
          this.commandAttack(target, u);
      }
    }
  }
  cleanDead() {
    let dirty = false;
    for (const u of this.units.filter((u) => u.hp <= 0)) {
      if (u.team === "enemy") this.stats.kills++;
      else this.stats.lost++;
      this.effects.push({
        kind: "fallen",
        x: u.x,
        y: u.y,
        team: u.team,
        life: 12,
      });
    }
    this.units = this.units.filter((u) => u.hp > 0);
    for (const b of this.buildings.filter((b) => b.hp <= 0)) {
      dirty = true;
      this.effects.push({
        kind: "rubble",
        x: b.x + b.w / 2,
        y: b.y + b.h / 2,
        life: 500,
        w: b.w,
      });
      this.emit("destroyed", { building: b });
      if (b.type === "town" && this.status === "playing") {
        this.status = b.team === "enemy" ? "victory" : "defeat";
        this.emit(this.status);
      }
    }
    this.buildings = this.buildings.filter((b) => b.hp > 0);
    if (dirty) this.rebuildBlocked();
  }
  updateAI() {
    const team = "enemy",
      workers = this.units.filter(
        (u) => u.team === team && u.type === "villager",
      ),
      town = this.town(team);
    if (!town) return;
    if (this.time > 240 && this.ages.enemy === 1 && !town.research)
      this.advance(town);
    if (this.time > 430 && this.ages.enemy === 2 && !town.research)
      this.advance(town);
    if (
      this.time > 210 &&
      !this.buildings.some((b) => b.team === team && b.type === "tower") &&
      workers.length
    ) {
      const worker = workers.find((u) => u.order.kind !== "build");
      if (worker)
        for (const [x, y] of [
          [30, 14],
          [36, 17],
          [31, 18],
        ])
          if (this.construct("tower", x, y, [worker], team).ok) break;
    }
    workers
      .filter((u) => u.order.kind === "idle")
      .forEach((u, i) =>
        this.assignGather(u, ["food", "wood", "food", "gold"][i % 4]),
      );
    if (workers.length < 8 && !town.queue.length) this.train(town, "villager");
    const army = this.units.filter(
      (u) => u.team === team && u.type === "soldier",
    );
    const barracks = this.buildings.filter(
      (b) => b.team === team && b.type === "barracks" && b.complete,
    );
    if (
      this.time > 42 &&
      army.length < Math.min(14, 4 + Math.floor(this.time / 65))
    )
      for (const b of barracks)
        if (b.queue.length < 2) this.train(b, "soldier");
    const needHouse = this.pop(team) + this.queued(team) >= this.cap(team) - 2;
    if (
      needHouse &&
      !this.buildings.some((b) => b.team === team && !b.complete) &&
      workers.length
    ) {
      for (const [x, y] of [
        [38, 15],
        [29, 15],
        [36, 19],
        [40, 10],
        [29, 18],
        [36, 5],
        [41, 14],
      ])
        if (this.construct("house", x, y, [workers[0]], team).ok) break;
    }
    if (
      this.time > 180 &&
      this.buildings.filter((b) => b.team === team && b.type === "farm")
        .length < 2 &&
      workers.length
    ) {
      for (const [x, y] of [
        [30, 8],
        [36, 14],
        [29, 5],
        [38, 4],
      ])
        if (
          this.construct("farm", x, y, [workers[workers.length - 1]], team).ok
        )
          break;
    }
    if (this.time >= this.ai.nextRaid) {
      const idle = army.filter(
        (u) => u.order.kind === "idle" || u.order.kind === "move",
      );
      if (idle.length >= 3) {
        const target = this.town("player");
        if (target) {
          idle
            .slice(0, Math.min(8, 3 + this.ai.raids * 2))
            .forEach((u) => this.commandAttack(u, target));
          this.ai.raids++;
          this.ai.nextRaid = this.time + 80;
          this.emit("raid", { count: idle.length });
        }
      } else this.ai.nextRaid = this.time + 12;
    }
  }
}
