import { MAP_SIZE } from "./data.js";

// Terrain is permanent knowledge. Moving units are never remembered; resources
// and rival buildings retain only their last observed state until revisited.
export class Visibility {
  constructor(game) {
    this.game = game;
    this.visible = new Uint8Array(MAP_SIZE * MAP_SIZE);
    this.explored = new Uint8Array(MAP_SIZE * MAP_SIZE);
    this.memory = new Map();
    this.revision = 0;
    this.discoveredEnemy = false;
    this.lastSighting = -30;
    this.seenSoldiers = new Set();
  }
  state(x, y) {
    x = Math.floor(x);
    y = Math.floor(y);
    if (x < 0 || y < 0 || x >= MAP_SIZE || y >= MAP_SIZE) return 0;
    const i = y * MAP_SIZE + x;
    return this.visible[i] ? 2 : this.explored[i] ? 1 : 0;
  }
  canSee(e) {
    if (!e) return false;
    if (e.team === "player") return true;
    if (!e.w) return this.state(e.x, e.y) === 2;
    for (let y = e.y; y < e.y + e.h; y++)
      for (let x = e.x; x < e.x + e.w; x++)
        if (this.state(x, y) === 2) return true;
    return false;
  }
  update() {
    const next = new Uint8Array(this.visible.length);
    for (const e of [...this.game.units, ...this.game.buildings]) {
      if (e.team !== "player" || e.hp <= 0) continue;
      const x = e.x + (e.w || 0) / 2,
        y = e.y + (e.h || 0) / 2;
      const radius = this.game.visionRadius(e);
      for (
        let yy = Math.max(0, Math.floor(y - radius));
        yy <= Math.min(MAP_SIZE - 1, Math.ceil(y + radius));
        yy++
      )
        for (
          let xx = Math.max(0, Math.floor(x - radius));
          xx <= Math.min(MAP_SIZE - 1, Math.ceil(x + radius));
          xx++
        )
          if ((xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= radius * radius)
            next[yy * MAP_SIZE + xx] = 1;
    }
    let changed = false;
    for (let i = 0; i < next.length; i++) {
      if (this.visible[i] !== next[i]) changed = true;
      this.visible[i] = next[i];
      if (next[i]) this.explored[i] = 1;
    }
    if (changed) this.revision++;
    const soldiers = this.game.units.filter(
      (u) =>
        u.team === "enemy" &&
        u.type === "soldier" &&
        u.hp > 0 &&
        this.canSee(u),
    );
    if (
      soldiers.some((u) => !this.seenSoldiers.has(u.id)) &&
      this.game.time - this.lastSighting > 20
    ) {
      this.lastSighting = this.game.time;
      this.game.emit("enemy-sighted");
    }
    this.seenSoldiers = new Set(soldiers.map((u) => u.id));
    // A remembered structure disappears only after its old position is scouted.
    for (const [id, remembered] of this.memory)
      if (this.canSee(remembered)) this.memory.delete(id);
    for (const e of [...this.game.resources, ...this.game.buildings]) {
      if (
        e.team === "player" ||
        !this.canSee(e) ||
        e.hp <= 0 ||
        (e.kind === "resource" && e.amount <= 0)
      )
        continue;
      this.memory.set(e.id, {
        ...e,
        queue: [],
        research: null,
        hitFlash: 0,
        remembered: true,
      });
      if (e.type === "town" && e.team === "enemy" && !this.discoveredEnemy) {
        this.discoveredEnemy = true;
        this.game.emit("discovered", { building: e });
      }
    }
  }
  knownEntities() {
    const current = [
      ...this.game.resources.filter((r) => r.amount > 0),
      ...this.game.buildings,
      ...this.game.units,
    ].filter((e) => this.canSee(e));
    const ids = new Set(current.map((e) => e.id));
    return [
      ...current,
      ...[...this.memory.values()].filter((e) => !ids.has(e.id)),
    ];
  }
  exploredPercent() {
    return Math.round(
      (this.explored.reduce((n, v) => n + v, 0) / this.explored.length) * 100,
    );
  }
}
