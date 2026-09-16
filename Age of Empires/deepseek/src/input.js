// Camera, selection, placement and command handling.
import {
  TILE,
  COLS,
  ROWS,
  WORLD_W,
  WORLD_H,
  BUILDING_STATS,
  COSTS,
  TEAM,
} from './config.js';

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

export class Controls {
  constructor({ canvas, renderer, sound, hud }) {
    this.canvas = canvas;
    this.renderer = renderer;
    this.sound = sound;
    this.hud = hud;
    this.game = null;
    this.camera = { x: 0, y: 0, zoom: 1, viewW: 800, viewH: 600 };
    this.pointer = { x: 0, y: 0, inside: false };
    this.keys = new Set();
    this.drag = null;
    this.panDrag = null;
    this.dragBox = null;
    this.placing = null;
    this.selUnits = [];
    this.selBuilding = null;
    this.paused = false;
    this.muted = false;
    this.formation = 'box';
    this.bind();
  }

  setGame(game) {
    this.game = game;
    this.clearSelection();
    this.placing = null;
    this.camera.zoom = 1;
    this.centerOnHome();
  }

  // ------------------------------------------------------------- coordinates

  viewSize() {
    const r = this.canvas.getBoundingClientRect();
    this.camera.viewW = r.width;
    this.camera.viewH = r.height;
    return r;
  }

  screenToWorld(clientX, clientY) {
    const r = this.canvas.getBoundingClientRect();
    return {
      x: this.camera.x + (clientX - r.left) / this.camera.zoom,
      y: this.camera.y + (clientY - r.top) / this.camera.zoom,
    };
  }

  clampCamera() {
    const r = this.viewSize();
    const w = r.width / this.camera.zoom;
    const h = r.height / this.camera.zoom;
    this.camera.x = w >= WORLD_W ? (WORLD_W - w) / 2 : clamp(this.camera.x, 0, WORLD_W - w);
    this.camera.y = h >= WORLD_H ? (WORLD_H - h) / 2 : clamp(this.camera.y, 0, WORLD_H - h);
  }

  centerOn(x, y) {
    const r = this.viewSize();
    this.camera.x = x - r.width / this.camera.zoom / 2;
    this.camera.y = y - r.height / this.camera.zoom / 2;
    this.clampCamera();
  }

  homeBuilding() {
    if (!this.game) return null;
    return (
      this.game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter') ||
      this.game.buildings.find((b) => b.team === TEAM.PLAYER)
    );
  }

  centerOnHome() {
    const home = this.homeBuilding();
    if (home) this.centerOn(home.x, home.y);
  }

  jumpTo(worldX, worldY) {
    this.centerOn(worldX, worldY);
  }

  // --------------------------------------------------------------- selection

  clearSelection() {
    for (const u of this.selUnits) u.selected = false;
    if (this.selBuilding) this.selBuilding.selected = false;
    this.selUnits = [];
    this.selBuilding = null;
    this.hud && this.hud.onSelectionChanged();
  }

  setSelection(units, building) {
    for (const u of this.selUnits) u.selected = false;
    if (this.selBuilding) this.selBuilding.selected = false;
    this.selUnits = units || [];
    this.selBuilding = building || null;
    for (const u of this.selUnits) u.selected = true;
    if (this.selBuilding) this.selBuilding.selected = true;
    this.sound && this.selUnits.length + (this.selBuilding ? 1 : 0) > 0 && this.sound.play('select');
    this.hud && this.hud.onSelectionChanged();
  }

  pruneSelection() {
    const alive = this.selUnits.filter((u) => this.game.unitById.get(u.id));
    const bAlive = this.selBuilding && this.game.buildingById.get(this.selBuilding.id);
    if (alive.length !== this.selUnits.length || (!bAlive && this.selBuilding)) {
      this.setSelection(alive, bAlive ? this.selBuilding : null);
    }
  }

  selectedUnits() {
    return this.selUnits.filter((u) => u.team === TEAM.PLAYER);
  }

  ownSelectedUnits() {
    return this.selectedUnits();
  }

  isSelected(e) {
    return !!e.selected;
  }

  // ------------------------------------------------------------------ events

  bind() {
    const c = this.canvas;
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    c.addEventListener('mousedown', (e) => this.onMouseDown(e));
    window.addEventListener('mousemove', (e) => this.onMouseMove(e));
    window.addEventListener('mouseup', (e) => this.onMouseUp(e));
    c.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });
    window.addEventListener('keydown', (e) => this.onKeyDown(e));
    window.addEventListener('keyup', (e) => this.keys.delete(e.key.toLowerCase()));
    window.addEventListener('blur', () => this.keys.clear());
    c.addEventListener('mouseleave', () => {
      this.pointer.inside = false;
    });
  }

  modKey(e) {
    return { shift: e.shiftKey, ctrl: e.ctrlKey || e.metaKey };
  }

  onMouseDown(e) {
    if (!this.game) return;
    const rect = this.canvas.getBoundingClientRect();
    const insideHud =
      e.clientY - rect.top < this.hudTop ||
      e.clientY - rect.top > rect.height - this.hudBottom;
    if (insideHud) return;
    if (e.button === 1) {
      this.panDrag = { x: e.clientX, y: e.clientY };
      e.preventDefault();
      return;
    }
    if (e.button === 2) {
      const w = this.screenToWorld(e.clientX, e.clientY);
      this.rightClick(w.x, w.y);
      return;
    }
    if (e.button !== 0) return;
    if (this.placing) {
      this.tryPlace(e);
      return;
    }
    this.drag = { sx: e.clientX, sy: e.clientY, moved: false, shift: e.shiftKey };
  }

  onMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    this.pointer.x = e.clientX;
    this.pointer.y = e.clientY;
    this.pointer.inside =
      e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom;
    if (this.panDrag) {
      this.camera.x -= (e.clientX - this.panDrag.x) / this.camera.zoom;
      this.camera.y -= (e.clientY - this.panDrag.y) / this.camera.zoom;
      this.panDrag = { x: e.clientX, y: e.clientY };
      this.clampCamera();
      return;
    }
    if (this.drag) {
      const dx = e.clientX - this.drag.sx;
      const dy = e.clientY - this.drag.sy;
      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) this.drag.moved = true;
      if (this.drag.moved) {
        this.dragBox = {
          x: Math.min(this.drag.sx, e.clientX),
          y: Math.min(this.drag.sy, e.clientY),
          w: Math.abs(dx),
          h: Math.abs(dy),
        };
      }
    }
  }

  onMouseUp(e) {
    if (this.panDrag && e.button === 1) {
      this.panDrag = null;
      return;
    }
    if (e.button !== 0 || !this.drag || !this.game) return;
    const drag = this.drag;
    const box = this.dragBox;
    this.drag = null;
    this.dragBox = null;
    if (drag.moved && box) this.boxSelect(box, drag.shift);
    else this.clickSelect(e.clientX, e.clientY, drag.shift);
  }

  onWheel(e) {
    e.preventDefault();
    if (!this.game) return;
    const before = this.screenToWorld(e.clientX, e.clientY);
    const factor = e.deltaY < 0 ? 1.14 : 1 / 1.14;
    this.camera.zoom = clamp(this.camera.zoom * factor, 0.6, 1.9);
    const after = this.screenToWorld(e.clientX, e.clientY);
    this.camera.x += before.x - after.x;
    this.camera.y += before.y - after.y;
    this.clampCamera();
  }

  onKeyDown(e) {
    if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
    const k = e.key.toLowerCase();
    this.keys.add(k);
    if (k === 'escape') {
      if (this.placing) this.cancelPlacing();
      else {
        this.clearSelection();
        this.hud && this.hud.closeOverlays();
      }
    }
    if (k === 'h') this.centerOnHome();
    if (k === 'p') this.togglePause();
    if (k === 'm') this.toggleMute();
    if (k === 'r') this.hud && this.hud.requestRestart();
    if (k === '?') this.hud && this.hud.toggleHelp();
    if (k === 'x') {
      const units = this.ownSelectedUnits();
      if (units.length) {
        this.game.commandStop(units);
        this.sound.play('command');
      }
    }
    if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright', ' '].includes(k)) e.preventDefault();
  }

  togglePause() {
    this.paused = !this.paused;
    this.hud && this.hud.onPauseChanged();
  }

  toggleMute() {
    this.muted = !this.muted;
    this.sound && this.sound.setMuted(this.muted);
    this.hud && this.hud.onMuteChanged();
  }

  // ----------------------------------------------------------------- camera

  update(dt) {
    if (!this.game) return;
    const r = this.viewSize();
    this.hudTop = this.hud ? this.hud.topHeight() : 0;
    this.hudBottom = this.hud ? this.hud.bottomHeight() : 0;

    const k = this.keys;
    let dx = 0;
    let dy = 0;
    if (k.has('a') || k.has('arrowleft')) dx -= 1;
    if (k.has('d') || k.has('arrowright')) dx += 1;
    if (k.has('w') || k.has('arrowup')) dy -= 1;
    if (k.has('s') || k.has('arrowdown')) dy += 1;

    // Edge scrolling only when the pointer is free of the HUD chrome.
    if (this.pointer.inside && !this.drag && !this.panDrag) {
      const px = this.pointer.x - r.left;
      const py = this.pointer.y - r.top;
      const margin = 22;
      const inHud = py < this.hudTop || py > r.height - this.hudBottom;
      if (!inHud) {
        if (px < margin) dx -= 1;
        if (px > r.width - margin) dx += 1;
        if (py < margin) dy -= 1;
        if (py > r.height - margin) dy += 1;
      }
    }

    if (dx || dy) {
      const len = Math.hypot(dx, dy) || 1;
      const speed = 620 / this.camera.zoom;
      this.camera.x += (dx / len) * speed * dt;
      this.camera.y += (dy / len) * speed * dt;
      this.clampCamera();
    }

    if (this.placing) {
      const w = this.screenToWorld(this.pointer.x, this.pointer.y);
      const s = BUILDING_STATS[this.placing.type];
      const tx = Math.round(w.x / TILE - s.w / 2);
      const ty = Math.round(w.y / TILE - s.h / 2);
      this.placing.tx = tx;
      this.placing.ty = ty;
      const check = this.game.canPlace(this.placing.type, TEAM.PLAYER, tx, ty);
      const afford = this.game.canAfford(TEAM.PLAYER, COSTS[this.placing.type]);
      this.placing.valid = check.ok && afford;
      this.placing.reason = check.ok ? (afford ? '' : 'Not enough resources') : check.reason;
    }
    this.pruneSelection();
  }

  // ------------------------------------------------------------- selection

  clickSelect(clientX, clientY, additive) {
    const w = this.screenToWorld(clientX, clientY);
    const unit = this.game.unitAt(w.x, w.y);
    const building = unit ? null : this.game.buildingAt(w.x, w.y);
    const resource = unit || building ? null : this.game.resourceAt(w.x, w.y);
    // Always answer the click, even when it lands on scenery.
    this.game.ringFor(unit || building || resource, w.x, w.y);
    if (!unit && !building) {
      if (!additive) this.clearSelection();
      return;
    }
    const target = unit || building;
    if (additive) {
      if (unit) {
        const next = this.selUnits.includes(unit)
          ? this.selUnits.filter((u) => u !== unit)
          : [...this.selUnits, unit];
        this.setSelection(next, this.selBuilding);
      } else {
        this.setSelection(this.selUnits, building);
      }
    } else {
      this.setSelection(unit ? [unit] : [], unit ? null : building);
    }
  }

  boxSelect(box, shift) {
    const a = this.screenToWorld(box.x, box.y);
    const b = this.screenToWorld(box.x + box.w, box.y + box.h);
    const x1 = Math.min(a.x, b.x);
    const x2 = Math.max(a.x, b.x);
    const y1 = Math.min(a.y, b.y);
    const y2 = Math.max(a.y, b.y);
    const picked = this.game.units.filter(
      (u) => u.team === TEAM.PLAYER && u.x >= x1 && u.x <= x2 && u.y >= y1 && u.y <= y2,
    );
    if (picked.length) {
      this.setSelection(shift ? [...new Set([...this.selUnits, ...picked])] : picked, null);
    } else if (!shift) {
      this.clearSelection();
    }
  }

  // --------------------------------------------------------------- commands

  rightClick(wx, wy) {
    const units = this.ownSelectedUnits();
    if (!units.length) return;
    const enemyUnit = this.game.units.find(
      (u) => u.team !== TEAM.PLAYER && Math.hypot(u.x - wx, u.y - wy) <= u.radius + 8,
    );
    if (enemyUnit) {
      this.game.commandAttack(units, enemyUnit);
      this.game.spawnRing(enemyUnit.x, enemyUnit.y + 4, (enemyUnit.radius || 10) + 8, '#ff9d8a', 0.45, 2.2);
      this.sound.play('command');
      return;
    }
    const building = this.game.buildingAt(wx, wy);
    if (building && building.team !== TEAM.PLAYER) {
      this.game.commandAttack(units, building);
      this.game.spawnRing(building.x, building.y, (Math.max(building.w, building.h) * TILE) / 2 + 6, '#ff9d8a', 0.5, 2.4);
      this.sound.play('command');
      return;
    }
    if (building && !building.complete) {
      const builders = units.filter((u) => u.type === 'villager');
      if (builders.length) {
        this.game.commandBuild(builders, building);
        this.sound.play('command');
        return;
      }
    }
    // A completed farm is a field: clicking anywhere on it means "go work it".
    if (building && building.team === TEAM.PLAYER && building.complete && building.foodNodeId) {
      const field = this.game.resourceById.get(building.foodNodeId);
      if (field) {
        this.game.commandGather(units, field);
        this.game.spawnRing(field.x, field.y + 4, field.radius + 8, '#c8ffa0', 0.5, 2.2);
        this.sound.play('command');
        return;
      }
    }
    const node = this.game.resourceAt(wx, wy);
    if (node) {
      this.game.commandGather(units, node);
      this.game.spawnRing(node.x, node.y + 4, node.radius + 8, '#c8ffa0', 0.5, 2.2);
      this.sound.play('command');
      return;
    }
    if (building) {
      this.game.commandMove(units, building.x, building.y + building.h * TILE * 0.6, this.formation);
      this.game.spawnRing(building.x, building.y + building.h * TILE * 0.5, 22, '#c8ffa0', 0.45, 2);
      this.sound.play('command');
      return;
    }
    this.game.commandMove(units, wx, wy, this.formation);
    this.game.spawnRing(wx, wy, 15, '#c8ffa0', 0.45, 2);
    this.sound.play('command');
  }

  // -------------------------------------------------------------- placement

  startPlacing(type) {
    const villagers = this.ownSelectedUnits().filter((u) => u.type === 'villager');
    if (!villagers.length) {
      this.hud.toast('Select a villager first.', 'warn');
      this.sound.play('error');
      return;
    }
    if (!this.game.canAfford(TEAM.PLAYER, COSTS[type])) {
      const need = Object.entries(COSTS[type]).map(([k, v]) => `${v} ${k}`).join(' + ');
      this.hud.toast(`You need ${need}.`, 'warn');
      this.sound.play('error');
      return;
    }
    this.placing = { type, tx: 0, ty: 0, valid: false, reason: '' };
    this.hud.onPlacingChanged();
  }

  cancelPlacing() {
    this.placing = null;
    this.hud.onPlacingChanged();
  }

  tryPlace(e) {
    const p = this.placing;
    if (!p) return;
    if (!p.valid) {
      this.hud.toast(p.reason || 'Cannot build there.', 'warn');
      this.sound.play('error');
      return;
    }
    const builders = this.ownSelectedUnits().filter((u) => u.type === 'villager');
    const result = this.game.placeBuilding(p.type, TEAM.PLAYER, p.tx, p.ty, builders);
    if (!result.ok) {
      this.hud.toast(result.reason, 'warn');
      this.sound.play('error');
      return;
    }
    const s2 = BUILDING_STATS[p.type];
    this.game.spawnRing(p.tx * TILE + (s2.w * TILE) / 2, p.ty * TILE + (s2.h * TILE) / 2, (Math.max(s2.w, s2.h) * TILE) / 2 + 6, '#ffe9a8', 0.6, 2.6);
    this.hud.toast(`${BUILDING_STATS[p.type].name} under construction`, 'good');
    if (!e.shiftKey) this.cancelPlacing();
  }
}
