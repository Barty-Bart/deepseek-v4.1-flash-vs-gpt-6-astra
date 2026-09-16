// Canvas renderer. Draws the world, entities, effects and the minimap.
import {
  TILE,
  COLS,
  ROWS,
  WORLD_W,
  WORLD_H,
  TEAM_COLORS,
  BUILDING_STATS,
  UNIT_STATS,
  RESOURCE_FROM,
  FOG,
} from './config.js';

const PALETTE = {
  grassDark: '#3f6b2e',
  grassMid: '#598a3c',
  grassLight: '#77a84e',
  dry: '#9c9553',
  waterDeep: '#2f5c85',
  waterShallow: '#4d80a8',
  dirt: '#8a7550',
  trunk: '#5a4127',
  canopyDark: '#2f5527',
  canopyMid: '#3f7033',
  canopyLight: '#4f8a3d',
  rock: '#8d8a82',
  rockDark: '#6c6a63',
  gold: '#e0b93d',
  berry: '#c0392b',
  stone: '#c3b596',
  stoneDark: '#a2937a',
  wood: '#8a6a41',
  roofFlat: '#8a5a3b',
  grout: 'rgba(40,30,20,0.25)',
  ui: '#f0e2c4',
};

const RES_LABEL = { tree: 'Wood', berry: 'Food', gold: 'Gold' };

function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

// ------------------------------------------------------------------ terrain

function buildTerrain(game) {
  // Two stages: paint a low-resolution colour field from the continuous noise,
  // then scale it up smoothly so terrain reads as organic ground rather than tiles.
  const RES = 4; // samples per tile
  const lw = COLS * RES;
  const lh = ROWS * RES;
  const low = makeCanvas(lw, lh);
  const lg = low.getContext('2d');
  const img = lg.createImageData(lw, lh);

  const tileNoise = (c, r) => game.noise[Math.min(ROWS - 1, Math.max(0, r)) * COLS + Math.min(COLS - 1, Math.max(0, c))];
  const sample = (x, y) => {
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const tx = smoothstep(x - x0);
    const ty = smoothstep(y - y0);
    const a = tileNoise(x0, y0);
    const b = tileNoise(x0 + 1, y0);
    const c = tileNoise(x0, y0 + 1);
    const d = tileNoise(x0 + 1, y0 + 1);
    const top = a + (b - a) * tx;
    const bot = c + (d - c) * tx;
    return top + (bot - top) * ty;
  };

  const hexToRgb = (hex) => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
  const maskAt = (c, r) => game.terrain[Math.min(ROWS - 1, Math.max(0, r)) * COLS + Math.min(COLS - 1, Math.max(0, c))];
  const sampleMask = (x, y) => {
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const tx = smoothstep(x - x0);
    const ty = smoothstep(y - y0);
    const a = maskAt(x0, y0);
    const b = maskAt(x0 + 1, y0);
    const c = maskAt(x0, y0 + 1);
    const d = maskAt(x0 + 1, y0 + 1);
    const top = a + (b - a) * tx;
    const bot = c + (d - c) * tx;
    return top + (bot - top) * ty;
  };

  const DARK = hexToRgb(PALETTE.grassDark);
  const MID = hexToRgb(PALETTE.grassMid);
  const LIGHT = hexToRgb(PALETTE.grassLight);
  const DRY = hexToRgb(PALETTE.dry);
  const WATER_DEEP = hexToRgb(PALETTE.waterDeep);
  const WATER_SHALLOW = hexToRgb(PALETTE.waterShallow);
  const FOAM = hexToRgb('#dff0e6');
  const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

  for (let py = 0; py < lh; py++) {
    for (let px = 0; px < lw; px++) {
      const raw = sample(px / RES, py / RES);
      // Widen the contrast: value noise clusters around 0.5 and reads as flat green.
      const n = Math.min(1, Math.max(0, (raw - 0.5) * 1.95 + 0.5));
      // Detail octave adds small-scale variation without hard bucket edges.
      const fine = sample(px / (RES * 0.3), py / (RES * 0.3)) * 0.5 + 0.5;
      const v = Math.min(1, Math.max(0, n * 0.84 + fine * 0.16));
      let col = v < 0.5 ? mix(DARK, MID, smoothstep(v / 0.5)) : mix(MID, LIGHT, smoothstep((v - 0.5) / 0.5));
      const dry = Math.max(0, 0.46 - v) / 0.46;
      if (dry > 0) col = mix(col, DRY, Math.min(1, dry * 1.15));
      // Blend water in at sub-tile resolution so shorelines are not stair-stepped.
      const wm = Math.min(1, Math.max(0, sampleMask(px / RES, py / RES) * 1.8));
      if (wm > 0.001) {
        const depth = smoothstep(Math.min(1, wm * 1.6));
        const water = mix(WATER_SHALLOW, WATER_DEEP, depth);
        col = mix(col, water, smoothstep(wm));
        // Bright band hugging the shoreline, following the smooth mask.
        const edge = Math.max(0, 1 - Math.abs(wm - 0.75) / 0.2);
        if (edge > 0) col = mix(col, FOAM, edge * 0.45);
      }
      const i = (py * lw + px) * 4;
      img.data[i] = col[0];
      img.data[i + 1] = col[1];
      img.data[i + 2] = col[2];
      img.data[i + 3] = 255;
    }
  }
  lg.putImageData(img, 0, 0);

  const c = makeCanvas(WORLD_W, WORLD_H);
  const g = c.getContext('2d');
  g.imageSmoothingEnabled = true;
  g.imageSmoothingQuality = 'high';
  g.drawImage(low, 0, 0, lw, lh, 0, 0, WORLD_W, WORLD_H);

  // Fine ground detail: grass tufts, pebbles.
  let seed = 1;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let r = 0; r < ROWS; r++) {
    for (let col = 0; col < COLS; col++) {
      const i = r * COLS + col;
      if (game.terrain[i] === 1) continue;
      const n = game.noise[i];
      const x = col * TILE;
      const y = r * TILE;
      const tufts = n > 0.5 ? 3 : 1;
      for (let k = 0; k < tufts; k++) {
        const tx = x + rnd() * TILE;
        const ty = y + rnd() * TILE;
        g.strokeStyle = n > 0.5 ? 'rgba(40,70,28,0.30)' : 'rgba(90,80,40,0.30)';
        g.lineWidth = 1;
        g.beginPath();
        g.moveTo(tx, ty);
        g.lineTo(tx + (rnd() - 0.5) * 3, ty - 2 - rnd() * 3);
        g.stroke();
      }
      if (n < 0.34 && rnd() < 0.16) {
        g.fillStyle = 'rgba(120,110,90,0.45)';
        g.beginPath();
        g.arc(x + rnd() * TILE, y + rnd() * TILE, 1.4, 0, Math.PI * 2);
        g.fill();
      }
    }
  }

  return c;
}

function smoothstep(t) {
  const x = Math.min(1, Math.max(0, t));
  return x * x * (3 - 2 * x);
}

// ------------------------------------------------------------------ helpers

// One pre-rendered radial-gradient sprite, blitted and stretched. Cheap enough
// for hundreds of objects and far softer than a flat ellipse.
let SHADOW_SPRITE = null;
function shadowSprite() {
  if (SHADOW_SPRITE) return SHADOW_SPRITE;
  const c = makeCanvas(64, 64);
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(10,16,8,0.60)');
  grad.addColorStop(0.45, 'rgba(10,16,8,0.40)');
  grad.addColorStop(0.75, 'rgba(10,16,8,0.14)');
  grad.addColorStop(1, 'rgba(10,16,8,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  SHADOW_SPRITE = c;
  return c;
}

// Contact shadow, offset towards the lower right to read as light from upper left.
function withShadow(ctx, x, y, rx, ry) {
  const spr = shadowSprite();
  ctx.drawImage(spr, x - rx + rx * 0.16, y - ry + ry * 0.34, rx * 2, ry * 2);
}

// A tighter, darker shadow right under the object where it meets the ground.
function contactShadow(ctx, x, y, rx, ry) {
  const spr = shadowSprite();
  ctx.globalAlpha = 0.75;
  ctx.drawImage(spr, x - rx, y - ry * 0.5, rx * 2, ry * 1.6);
  ctx.globalAlpha = 1;
}

// Light rim along the top-left edges of a shape, which sells the volume.
function rimLight(ctx, x, y, w, h, radius = 3) {
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.16)';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(x + radius, y + 0.8);
  ctx.lineTo(x + w - radius, y + 0.8);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x + 0.8, y + radius);
  ctx.lineTo(x + 0.8, y + h - radius);
  ctx.stroke();
  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

function drawHealthBar(ctx, x, y, w, frac, color) {
  const h = 3.5;
  ctx.fillStyle = 'rgba(12,14,10,0.75)';
  ctx.fillRect(x - w / 2 - 1, y - 1, w + 2, h + 2);
  ctx.fillStyle = color;
  ctx.fillRect(x - w / 2, y, w * Math.max(0, frac), h);
}

// ------------------------------------------------------------------ pieces

// Shared 3/4 building helpers -------------------------------------------------

// A vertical wall face: lighter at the top, darker towards the ground.
function wallFace(ctx, x, y, w, h, light, dark) {
  const g = ctx.createLinearGradient(x, y, x, y + h);
  g.addColorStop(0, light);
  g.addColorStop(1, dark);
  ctx.fillStyle = g;
  roundRect(ctx, x, y, w, h, 2.5);
  ctx.fill();
  ctx.strokeStyle = 'rgba(48,36,22,0.35)';
  ctx.lineWidth = 1;
  ctx.stroke();
  // stone courses
  ctx.strokeStyle = 'rgba(48,36,22,0.16)';
  const rows = Math.max(2, Math.round(h / 9));
  for (let i = 1; i < rows; i++) {
    const yy = y + (h * i) / rows;
    ctx.beginPath();
    ctx.moveTo(x + 1, yy);
    ctx.lineTo(x + w - 1, yy);
    ctx.stroke();
  }
}

// A pitched roof seen from a fixed 3/4 angle: two shaded planes and a ridge.
function gableRoof(ctx, x, y, w, rh, light, dark) {
  const cx = x + w / 2;
  ctx.fillStyle = light;
  ctx.beginPath();
  ctx.moveTo(x - 3, y + rh);
  ctx.lineTo(cx, y);
  ctx.lineTo(cx, y + rh);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = dark;
  ctx.beginPath();
  ctx.moveTo(cx, y);
  ctx.lineTo(x + w + 3, y + rh);
  ctx.lineTo(cx, y + rh);
  ctx.closePath();
  ctx.fill();
  // tile lines
  ctx.strokeStyle = 'rgba(30,20,12,0.18)';
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) {
    const t = i / 4;
    ctx.beginPath();
    ctx.moveTo(x - 3 + (cx - x + 3) * t, y + rh);
    ctx.lineTo(x - 3, y + rh - rh * t);
    ctx.moveTo(x + w + 3 - (x + w + 3 - cx) * t, y + rh);
    ctx.lineTo(x + w + 3, y + rh - rh * t);
    ctx.stroke();
  }
  // ridge highlight and eave shadow
  ctx.strokeStyle = 'rgba(255,255,255,0.28)';
  ctx.lineWidth = 1.3;
  ctx.beginPath();
  ctx.moveTo(x - 3, y + rh);
  ctx.lineTo(cx, y);
  ctx.lineTo(x + w + 3, y + rh);
  ctx.stroke();
  ctx.fillStyle = 'rgba(25,18,10,0.30)';
  ctx.fillRect(x - 3, y + rh - 1.5, w + 6, 3);
}

function banner(ctx, x, y, team, wave) {
  ctx.strokeStyle = '#5a4127';
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(x, y + 8);
  ctx.lineTo(x, y - 20);
  ctx.stroke();
  ctx.fillStyle = team.main;
  ctx.beginPath();
  ctx.moveTo(x, y - 19);
  ctx.lineTo(x + 18 + wave, y - 14);
  ctx.lineTo(x, y - 8);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = 'rgba(0,0,0,0.25)';
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.fillStyle = team.light;
  ctx.beginPath();
  ctx.arc(x + 5, y - 14, 2.2, 0, Math.PI * 2);
  ctx.fill();
}

// Individual structures -------------------------------------------------------

function drawHouse(ctx, x, y, w, h, team) {
  const lift = 10;
  const top = y - lift;
  const rh = h * 0.44;
  contactShadow(ctx, x + w / 2, y + h - 2, (w + 10) / 2, 9);
  wallFace(ctx, x + 3, top + rh - 3, w - 6, h - rh + lift + 1, '#e2d6b4', '#b3a586');
  rimLight(ctx, x + 3, top + rh - 3, w - 6, h - rh + lift + 1);
  gableRoof(ctx, x + 1, top + 3, w - 2, rh, team.main, team.dark);
  // door and lit window
  ctx.fillStyle = '#4a3927';
  ctx.beginPath();
  ctx.moveTo(x + w / 2 - 6, y + h);
  ctx.lineTo(x + w / 2 - 6, y + h - 11);
  ctx.quadraticCurveTo(x + w / 2, y + h - 17, x + w / 2 + 6, y + h - 11);
  ctx.lineTo(x + w / 2 + 6, y + h);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#f2d18a';
  ctx.fillRect(x + w - 17, y + rh + 4, 8, 7);
  ctx.strokeStyle = 'rgba(60,45,25,0.6)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x + w - 17, y + rh + 4, 8, 7);
  // side shading so the volume reads
  ctx.fillStyle = 'rgba(40,30,18,0.18)';
  ctx.fillRect(x + w - 4, y + rh - 3, 4, h - rh + 1);
}

function drawTownCenter(ctx, x, y, w, h, team, b, time) {
  const lift = 9;
  const top = y - lift;
  const rh = h * 0.40;
  contactShadow(ctx, x + w / 2, y + h - 2, (w + 14) / 2, 11);
  wallFace(ctx, x + 4, top + rh + 6, w - 8, h - rh - 2 + lift, '#d8caa6', '#a89a7c');
  rimLight(ctx, x + 4, top + rh + 6, w - 8, h - rh - 2 + lift);
  // stone base course
  ctx.fillStyle = 'rgba(60,48,30,0.20)';
  ctx.fillRect(x + 4, y + h - 9, w - 8, 9);
  // side tower
  const tw = w * 0.26;
  wallFace(ctx, x + w - tw - 2, top + rh * 0.35 - 8, tw, h - rh * 0.35 - 2 + lift + 8, '#cabd9b', '#94886c');
  ctx.fillStyle = team.dark;
  for (let i = 0; i < 3; i++) ctx.fillRect(x + w - tw - 2 + i * (tw / 3) + 2, top + rh * 0.35 - 13, tw / 3 - 4, 7);
  // main roof
  gableRoof(ctx, x + 2, top + 6, w - 8, rh, team.main, team.dark);
  // arched door
  ctx.fillStyle = '#43331f';
  ctx.beginPath();
  ctx.moveTo(b.x - 12, y + h - 2);
  ctx.lineTo(b.x - 12, y + h - 20);
  ctx.quadraticCurveTo(b.x, y + h - 30, b.x + 12, y + h - 20);
  ctx.lineTo(b.x + 12, y + h - 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = '#2c2114';
  ctx.fillRect(b.x - 1, y + h - 26, 2, 24);
  // windows
  for (const wx of [x + 13, b.x - 4]) {
    ctx.fillStyle = '#f4d68f';
    ctx.fillRect(wx, y + rh + 12, 9, 8);
    ctx.strokeStyle = 'rgba(60,45,25,0.65)';
    ctx.lineWidth = 1;
    ctx.strokeRect(wx, y + rh + 12, 9, 8);
  }
  banner(ctx, b.x + 16, y + 6, team, b.aimPulse ? Math.sin(b.aimPulse * 12) * 2 : 0);
  if (b.research) {
    // A scholar's spark while the settlement advances.
    const pulse = 0.5 + 0.5 * Math.sin(time * 6);
    ctx.fillStyle = `rgba(255,232,150,${0.35 + 0.4 * pulse})`;
    ctx.beginPath();
    ctx.arc(b.x, y + rh + 26, 5 + pulse * 2, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawBarracks(ctx, x, y, w, h, team) {
  const lift = 8;
  const top = y - lift;
  contactShadow(ctx, x + w / 2, y + h - 2, (w + 12) / 2, 10);
  wallFace(ctx, x + 2, top + 10, w - 4, h - 12 + lift, '#b3a68a', '#7f745d');
  rimLight(ctx, x + 2, top + 10, w - 4, h - 12 + lift);
  // crenellated parapet
  ctx.fillStyle = '#6e6552';
  const merlons = 4;
  for (let i = 0; i < merlons; i++) {
    ctx.fillRect(x + 2 + (w - 4) / merlons * i + 2, top, (w - 4) / merlons - 5, 12);
  }
  ctx.fillStyle = 'rgba(0,0,0,0.18)';
  ctx.fillRect(x + 2, top + 10, w - 4, 4);
  // gate
  const gx = x + w * 0.42;
  ctx.fillStyle = '#3a2c1c';
  ctx.beginPath();
  ctx.moveTo(gx, y + h - 2);
  ctx.lineTo(gx, y + h - 22);
  ctx.quadraticCurveTo(gx + 9, y + h - 30, gx + 18, y + h - 22);
  ctx.lineTo(gx + 18, y + h - 2);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = 'rgba(210,200,175,0.5)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(gx + 9, y + h - 26);
  ctx.lineTo(gx + 9, y + h - 2);
  ctx.stroke();
  // crossed spears on the wall
  ctx.strokeStyle = '#ded9cc';
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(x + 9, top + 16);
  ctx.lineTo(x + 27, top + 36);
  ctx.moveTo(x + 27, top + 16);
  ctx.lineTo(x + 9, top + 36);
  ctx.stroke();
  // banner
  ctx.fillStyle = team.main;
  ctx.beginPath();
  ctx.moveTo(x + w - 22, top + 4);
  ctx.lineTo(x + w - 4, top + 4);
  ctx.lineTo(x + w - 13, top + 17);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = 'rgba(40,30,18,0.20)';
  ctx.fillRect(x + w - 6, top + 10, 6, h - 12 + lift);
}

function drawWatchTower(ctx, x, y, w, h, team, time) {
  const lift = 26; // towers stand taller than their footprint
  contactShadow(ctx, x + w / 2, y + h - 1, (w + 10) / 2, 9);
  const tx = x + 6;
  const tw = w - 12;
  const ty = y - lift;
  const th = h + lift;
  // shaft
  wallFace(ctx, tx, ty + 12, tw, th - 14, '#cdc2a3', '#8d8268');
  rimLight(ctx, tx, ty + 12, tw, th - 14);
  // corbel flare near the top
  ctx.fillStyle = '#b0a488';
  ctx.fillRect(tx - 3, ty + 8, tw + 6, 7);
  // crenellations
  ctx.fillStyle = '#8a7f65';
  const merlons = 3;
  for (let i = 0; i < merlons; i++) {
    ctx.fillRect(tx - 3 + ((tw + 6) / merlons) * i + 1.5, ty - 3, (tw + 6) / merlons - 4, 12);
  }
  ctx.fillStyle = 'rgba(0,0,0,0.22)';
  ctx.fillRect(tx - 3, ty + 15, tw + 6, 3);
  // arrow slits
  ctx.fillStyle = '#2f2a1e';
  ctx.fillRect(tx + tw / 2 - 1.5, ty + 26, 3, 11);
  ctx.fillRect(tx + tw / 2 - 1.5, ty + 44, 3, 11);
  // stone texture
  ctx.strokeStyle = 'rgba(48,36,22,0.14)';
  ctx.lineWidth = 1;
  for (let i = 1; i < 6; i++) {
    const yy = ty + 12 + ((th - 14) * i) / 6;
    ctx.beginPath();
    ctx.moveTo(tx + 1, yy);
    ctx.lineTo(tx + tw - 1, yy);
    ctx.stroke();
  }
  banner(ctx, tx + tw + 8, ty + 6, team, Math.sin(time * 2) * 1.4);
  void ctx;
}

function drawFarmPlot(ctx, x, y, w, h) {
  ctx.fillStyle = '#6f5a38';
  roundRect(ctx, x, y, w, h, 3);
  ctx.fill();
  ctx.fillStyle = '#836b42';
  roundRect(ctx, x + 2, y + 2, w - 4, h - 4, 2);
  ctx.fill();
  const furrows = [];
  for (let i = 0; i < 4; i++) furrows.push(y + 7 + ((h - 14) * i) / 3);
  for (const yy of furrows) {
    ctx.strokeStyle = '#6d5a35';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(x + 5, yy + 1.5);
    ctx.lineTo(x + w - 5, yy + 1.5);
    ctx.stroke();
    ctx.strokeStyle = '#7fae57';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(x + 5, yy);
    ctx.lineTo(x + w - 5, yy);
    ctx.stroke();
    ctx.strokeStyle = '#a5d178';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(x + 5, yy - 1.6);
    ctx.lineTo(x + w - 5, yy - 1.6);
    ctx.stroke();
  }
  // low fence
  ctx.strokeStyle = '#8a6a41';
  ctx.lineWidth = 2.4;
  roundRect(ctx, x + 1, y + 1, w - 2, h - 2, 3);
  ctx.stroke();
  ctx.fillStyle = '#8a6a41';
  for (const [px, py] of [[x + 1, y + 1], [x + w - 1, y + 1], [x + 1, y + h - 1], [x + w - 1, y + h - 1]]) {
    ctx.fillRect(px - 1.6, py - 1.6, 3.2, 3.2);
  }
}

function drawConstruction(ctx, x, y, w, h, frac, selected) {
  ctx.fillStyle = '#7b7160';
  roundRect(ctx, x, y, w, h, 3);
  ctx.fill();
  ctx.fillStyle = 'rgba(34,28,20,0.45)';
  roundRect(ctx, x + 4, y + 4, w - 8, h - 8, 2);
  ctx.fill();
  // stacked material
  ctx.fillStyle = '#8a7a5c';
  for (let i = 0; i < 3; i++) {
    ctx.fillRect(x + 6 + i * 3, y + h - 12 - i * 3, 7, 8);
  }
  // corner stakes with rope
  ctx.strokeStyle = '#6d5334';
  ctx.lineWidth = 2.4;
  for (const [px, py] of [[x + 2, y + 2], [x + w - 2, y + 2], [x + 2, y + h - 2], [x + w - 2, y + h - 2]]) {
    ctx.beginPath();
    ctx.moveTo(px, py + 4);
    ctx.lineTo(px, py - 9);
    ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(220,205,170,0.45)';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(x + 2, y - 6);
  ctx.lineTo(x + w - 2, y - 6);
  ctx.stroke();
  // progress
  ctx.fillStyle = 'rgba(14,12,9,0.75)';
  ctx.fillRect(x + 4, y + h - 11, w - 8, 6);
  ctx.fillStyle = '#e8b64c';
  ctx.fillRect(x + 4, y + h - 11, (w - 8) * frac, 6);
  ctx.strokeStyle = 'rgba(0,0,0,0.4)';
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 4, y + h - 11, w - 8, 6);
  if (selected) {
    ctx.strokeStyle = '#c8ffa0';
    ctx.lineWidth = 2;
    roundRect(ctx, x - 2, y - 2, w + 4, h + 4, 5);
    ctx.stroke();
  }
}

function drawCarry(ctx, kind, bob) {
  const y = -25 + bob * 0.4;
  if (kind === 'wood') {
    ctx.fillStyle = '#7d5a34';
    roundRect(ctx, -9, y, 18, 4.5, 2.2);
    ctx.fill();
    ctx.strokeStyle = '#4a3520';
    ctx.lineWidth = 0.9;
    ctx.stroke();
    ctx.fillStyle = '#9a7440';
    roundRect(ctx, -8, y + 4, 16, 4.5, 2.2);
    ctx.fill();
    ctx.stroke();
    return;
  }
  if (kind === 'gold') {
    ctx.fillStyle = '#f0d76a';
    ctx.strokeStyle = '#8a6a1f';
    ctx.lineWidth = 0.9;
    for (const [cx, cy] of [[-5, y + 5], [1, y + 5], [-2, y]]) {
      ctx.beginPath();
      ctx.ellipse(cx, cy, 4, 2.6, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    return;
  }
  ctx.strokeStyle = '#c9a12f';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(0, y + 9);
  ctx.lineTo(0, y - 1);
  ctx.stroke();
  ctx.fillStyle = '#e9c447';
  ctx.strokeStyle = '#8a6a1f';
  ctx.lineWidth = 0.8;
  for (const [cx, cy] of [[-4, y + 1], [-4, y + 5], [4, y + 1], [4, y + 5], [0, y - 2]]) {
    ctx.beginPath();
    ctx.ellipse(cx, cy, 3.4, 2.2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
}

function drawResource(ctx, node, time) {
  const frac = Number.isFinite(node.max) ? Math.max(0.25, node.amount / node.max) : 1;
  const j = node.jitter;
  const worked = time - (node.workedAt || -99) < 0.4;

  if (worked) {
    const pulse = 0.5 + 0.5 * Math.sin(time * 9);
    ctx.strokeStyle = `rgba(255,244,196,${0.30 + 0.30 * pulse})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.ellipse(node.x, node.y + 4, node.radius + 6, (node.radius + 6) * 0.6, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  if (node.kind === 'tree') {
    const s = 0.8 + 0.25 * frac + j * 0.1;
    withShadow(ctx, node.x, node.y + 8, 13 * s, 5.5 * s);
    ctx.fillStyle = PALETTE.trunk;
    ctx.fillRect(node.x - 2.5, node.y - 1, 5, 10);
    ctx.fillStyle = '#4a3520';
    ctx.fillRect(node.x - 2.5, node.y + 7, 5, 2);
    for (const b of [
      { x: -5 - j * 3, y: -8, r: 10 },
      { x: 6 + j * 2, y: -6, r: 9 },
      { x: 0, y: -16 - j * 2, r: 10.5 },
    ]) {
      ctx.fillStyle = j > 0.5 ? PALETTE.canopyMid : PALETTE.canopyDark;
      ctx.beginPath();
      ctx.arc(node.x + b.x * s, node.y + b.y * s, b.r * s, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = PALETTE.canopyLight;
    ctx.beginPath();
    ctx.arc(node.x - 3 * s, node.y - 15 * s, 6 * s, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.14)';
    ctx.beginPath();
    ctx.arc(node.x - 5 * s, node.y - 18 * s, 3.4 * s, 0, Math.PI * 2);
    ctx.fill();
    return;
  }

  if (node.kind === 'gold') {
    withShadow(ctx, node.x, node.y + 9, 13, 5.5);
    ctx.fillStyle = PALETTE.rockDark;
    ctx.beginPath();
    ctx.moveTo(node.x - 13, node.y + 9);
    ctx.lineTo(node.x - 9, node.y - 7);
    ctx.lineTo(node.x - 1, node.y - 14);
    ctx.lineTo(node.x + 9, node.y - 8);
    ctx.lineTo(node.x + 13, node.y + 9);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = PALETTE.rock;
    ctx.beginPath();
    ctx.moveTo(node.x - 10, node.y + 7);
    ctx.lineTo(node.x - 5, node.y - 3);
    ctx.lineTo(node.x + 2, node.y - 9);
    ctx.lineTo(node.x + 8, node.y + 5);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.18)';
    ctx.beginPath();
    ctx.moveTo(node.x - 5, node.y - 3);
    ctx.lineTo(node.x + 2, node.y - 9);
    ctx.lineTo(node.x + 4, node.y - 1);
    ctx.closePath();
    ctx.fill();
    for (let i = 0; i < 5; i++) {
      const a = (i / 5) * Math.PI * 2 + j * 3;
      ctx.fillStyle = i % 2 ? PALETTE.gold : '#f6e089';
      ctx.beginPath();
      ctx.ellipse(node.x + Math.cos(a) * 5.5, node.y + Math.sin(a) * 4.5 + 1, 2.4, 1.8, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(90,70,20,0.5)';
      ctx.lineWidth = 0.7;
      ctx.stroke();
    }
    return;
  }

  const s = 0.75 + 0.3 * frac;
  withShadow(ctx, node.x, node.y + 6, 12 * s, 4.5 * s);
  ctx.fillStyle = PALETTE.canopyDark;
  ctx.beginPath();
  ctx.ellipse(node.x, node.y + 1, 12 * s, 8.5 * s, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = PALETTE.canopyMid;
  ctx.beginPath();
  ctx.ellipse(node.x - 2, node.y - 1, 10 * s, 7 * s, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = PALETTE.canopyLight;
  ctx.beginPath();
  ctx.ellipse(node.x - 3.5, node.y - 3.5, 5.5 * s, 4 * s, 0, 0, Math.PI * 2);
  ctx.fill();
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 + j * 6;
    const bx = node.x + Math.cos(a) * 6.5 * s;
    const by = node.y + Math.sin(a) * 4.5 * s;
    ctx.fillStyle = '#a52f24';
    ctx.beginPath();
    ctx.arc(bx, by, 2.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.beginPath();
    ctx.arc(bx - 0.7, by - 0.7, 0.9, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawUnit(ctx, u, selected) {
  const team = TEAM_COLORS[u.team];
  const st = UNIT_STATS[u.type];
  const bob = Math.sin(u.animPhase) * (u.walking ? 1.1 : 0.35);
  const otherBob = Math.sin(u.animPhase + Math.PI) * (u.walking ? 1.1 : 0.35);

  withShadow(ctx, u.x, u.y + 8, st.radius + 3.5, 4);

  if (selected) {
    ctx.strokeStyle = u.team === 0 ? '#c8ffa0' : '#ffd0c0';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.ellipse(u.x, u.y + 8, st.radius + 6, (st.radius + 6) * 0.5, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.save();
  ctx.translate(u.x, u.y);
  ctx.scale(u.facing, 1);
  if (u.type === 'knight') ctx.scale(1.16, 1.16);

  if (u.type === 'villager') {
    ctx.fillStyle = '#6b5a42';
    ctx.fillRect(-4, 2 + otherBob, 3, 6);
    ctx.fillRect(1.5, 2 + bob, 3, 6);
    ctx.fillStyle = team.main;
    ctx.beginPath();
    ctx.ellipse(0, -1, 6, 9, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = team.dark;
    ctx.beginPath();
    ctx.ellipse(0, 3, 6, 5, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#e7d9b6';
    ctx.fillRect(-6, -1, 12, 2);
    ctx.fillStyle = '#e8c39a';
    ctx.beginPath();
    ctx.arc(0, -11 + bob * 0.4, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = team.light;
    ctx.beginPath();
    ctx.arc(0, -13 + bob * 0.4, 5.4, Math.PI, Math.PI * 2);
    ctx.fill();
    if (u.building) {
      const swing = Math.sin(u.animPhase * 2.2) * 0.8;
      ctx.save();
      ctx.translate(6, -6);
      ctx.rotate(-0.6 + swing);
      ctx.strokeStyle = '#7a5a33';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(0, -9);
      ctx.stroke();
      ctx.fillStyle = '#9a9a9a';
      ctx.fillRect(-3, -12, 6, 4);
      ctx.restore();
    }
    if (u.carry > 0) drawCarry(ctx, u.carryKind, bob);
    ctx.restore();
  } else if (u.type === 'archer') {
    ctx.fillStyle = '#5f5340';
    ctx.fillRect(-4, 2 + otherBob, 3, 6);
    ctx.fillRect(1, 2 + bob, 3, 6);
    ctx.save();
    ctx.rotate(-0.5);
    ctx.fillStyle = '#6b4a26';
    roundRect(ctx, -10, -13, 4.5, 12, 2);
    ctx.fill();
    ctx.restore();
    ctx.fillStyle = '#6f8f52';
    ctx.beginPath();
    ctx.ellipse(0, -3, 6, 9, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = team.dark;
    roundRect(ctx, -6.5, -2, 13, 8, 3);
    ctx.fill();
    ctx.strokeStyle = '#8a6a41';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.arc(8, -6, 8, -1.15, 1.15);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(240,235,215,0.75)';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(11.4, -13.4);
    ctx.lineTo(11.4, 1.4);
    ctx.stroke();
    ctx.fillStyle = '#e8c39a';
    ctx.beginPath();
    ctx.arc(0, -14 + bob * 0.4, 4.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#6f8f52';
    ctx.beginPath();
    ctx.arc(0, -15 + bob * 0.4, 5, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = team.main;
    ctx.fillRect(-5, -15.5 + bob * 0.4, 10, 2);
    ctx.restore();
  } else {
    ctx.fillStyle = '#5f5340';
    ctx.fillRect(-5, 2 + otherBob, 3.5, 7);
    ctx.fillRect(1.5, 2 + bob, 3.5, 7);
    ctx.fillStyle = team.main;
    roundRect(ctx, -7, -12, 14, 16, 4);
    ctx.fill();
    ctx.fillStyle = team.dark;
    roundRect(ctx, -7, -2, 14, 7, 3);
    ctx.fill();
    if (u.type === 'knight') {
      ctx.fillStyle = 'rgba(255,255,255,0.20)';
      roundRect(ctx, -6, -11, 5, 13, 2);
      ctx.fill();
    }
    ctx.fillStyle = '#cdb27a';
    roundRect(ctx, -11, -9, 5, 12, 2);
    ctx.fill();
    ctx.fillStyle = team.main;
    ctx.fillRect(-9.5, -6, 2.4, 6);
    ctx.fillStyle = '#e8c39a';
    ctx.beginPath();
    ctx.arc(0, -15 + bob * 0.4, 4.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = u.type === 'knight' ? '#dde2ea' : '#c9ced6';
    ctx.beginPath();
    ctx.arc(0, -16 + bob * 0.4, 5.2, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#9aa2ad';
    ctx.fillRect(-5.2, -16 + bob * 0.4, 10.4, 2);
    ctx.fillStyle = team.main;
    ctx.beginPath();
    ctx.arc(0, -21 + bob * 0.4, u.type === 'knight' ? 3 : 2.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#8a6a41';
    ctx.lineWidth = u.type === 'knight' ? 2.4 : 2;
    ctx.beginPath();
    ctx.moveTo(6, 6);
    ctx.lineTo(u.type === 'knight' ? 10 : 9, u.type === 'knight' ? -24 : -22);
    ctx.stroke();
    ctx.fillStyle = u.type === 'knight' ? '#e6ecf4' : '#d8dde3';
    ctx.beginPath();
    if (u.type === 'knight') {
      ctx.moveTo(8, -23);
      ctx.lineTo(14, -30);
      ctx.lineTo(11, -20);
    } else {
      ctx.moveTo(7.5, -22);
      ctx.lineTo(12.5, -25);
      ctx.lineTo(9.5, -19);
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  if (u.flash > 0) {
    ctx.fillStyle = `rgba(255,240,210,${u.flash * 0.5})`;
    ctx.beginPath();
    ctx.arc(u.x, u.y - 6, st.radius + 4, 0, Math.PI * 2);
    ctx.fill();
  }
  if (u.hp < u.maxHp) {
    drawHealthBar(ctx, u.x, u.y - st.radius - 17, 22, u.hp / u.maxHp,
      u.team === 0 ? '#63c74d' : '#d95c4c');
  }
}

function drawBuilding(ctx, b, selected, time) {
  const team = TEAM_COLORS[b.team];
  const w = b.w * TILE;
  const h = b.h * TILE;
  const x = b.x - w / 2;
  const y = b.y - h / 2;

  ctx.fillStyle = 'rgba(18,24,12,0.30)';
  roundRect(ctx, x + 4, y + 8, w, h, 6);
  ctx.fill();

  if (!b.complete) {
    drawConstruction(ctx, x, y, w, h, Math.max(0, Math.min(1, b.progress / b.buildTime)), selected);
    if (b.hp < b.maxHp) drawHealthBar(ctx, b.x, y - 10, w * 0.8, b.hp / b.maxHp, '#63c74d');
    return;
  }

  if (b.type === 'farm') drawFarmPlot(ctx, x, y, w, h);
  else if (b.type === 'house') drawHouse(ctx, x, y, w, h, team);
  else if (b.type === 'barracks') drawBarracks(ctx, x, y, w, h, team);
  else if (b.type === 'watchtower') drawWatchTower(ctx, b, x, y, w, h, team, time);
  else drawTownCenter(ctx, x, y, w, h, team, b, time);

  if (b.flash > 0) {
    ctx.fillStyle = `rgba(255,230,190,${b.flash * 0.35})`;
    roundRect(ctx, x, y, w, h, 4);
    ctx.fill();
  }
  if (selected) {
    ctx.strokeStyle = '#c8ffa0';
    ctx.lineWidth = 2;
    roundRect(ctx, x - 3, y - 3, w + 6, h + 6, 5);
    ctx.stroke();
  }
  if (b.hp < b.maxHp) {
    drawHealthBar(ctx, b.x, y - 10, Math.max(34, w * 0.75), b.hp / b.maxHp,
      b.team === 0 ? '#63c74d' : '#d95c4c');
  }
}

// ------------------------------------------------------------------ renderer

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.terrain = null;
    this.game = null;
    this.minimap = null;
    this.drawList = [];
    this.fogLow = null;
    this.fogImage = null;
    this.fogVersion = -1;
  }

  setGame(game) {
    this.game = game;
    this.terrain = buildTerrain(game);
    this.minimapBase = this.buildMinimap(game);
    this.waterTiles = [];
    for (let r = 0; r < ROWS; r++) {
      for (let col = 0; col < COLS; col++) {
        if (game.terrain[r * COLS + col] === 1) {
          this.waterTiles.push({ x: col * TILE + TILE / 2, y: r * TILE + TILE / 2 });
        }
      }
    }
    this.fogVersion = -1;
  }

  buildMinimap(game) {
    const scale = 3;
    const c = makeCanvas(COLS * scale, ROWS * scale);
    const g = c.getContext('2d');
    g.drawImage(this.terrain, 0, 0, c.width, c.height);
    for (const n of game.resources) {
      if (n.kind === 'farm') continue;
      g.fillStyle = n.kind === 'tree' ? '#33561f' : n.kind === 'gold' ? '#e0b93d' : '#c0392b';
      g.fillRect((n.x / TILE) * scale - 1, (n.y / TILE) * scale - 1, 2.5, 2.5);
    }
    this.minimapScale = scale;
    return c;
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    this.canvas.width = Math.round(w * dpr);
    this.canvas.height = Math.round(h * dpr);
    this.dpr = dpr;
    this.viewW = w;
    this.viewH = h;
  }

  // ------------------------------------------------------------ fog of war

  ensureFogCanvas() {
    if (!this.fogLow) {
      this.fogLow = makeCanvas(COLS, ROWS);
      this.fogImage = this.fogLow.getContext('2d').createImageData(COLS, ROWS);
    }
  }

  refreshFog(game) {
    this.ensureFogCanvas();
    if (this.fogVersion === game.fogVersion) return;
    this.fogVersion = game.fogVersion;
    const f = game.fog[0];
    const d = this.fogImage.data;
    for (let i = 0; i < f.explored.length; i++) {
      const o = i * 4;
      if (f.visible[i]) {
        d[o + 3] = 0;
        continue;
      }
      if (f.explored[i]) {
        d[o] = FOG.explored[0];
        d[o + 1] = FOG.explored[1];
        d[o + 2] = FOG.explored[2];
        d[o + 3] = FOG.exploredAlpha;
      } else {
        d[o] = FOG.unknown[0];
        d[o + 1] = FOG.unknown[1];
        d[o + 2] = FOG.unknown[2];
        d[o + 3] = FOG.unknownAlpha;
      }
    }
    this.fogLow.getContext('2d').putImageData(this.fogImage, 0, 0);
  }

  // ---------------------------------------------------------------- drawing

  draw(view) {
    const ctx = this.ctx;
    const game = this.game;
    const cam = view.camera;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#06080c';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    if (!game) return;

    ctx.setTransform(
      this.dpr * cam.zoom,
      0,
      0,
      this.dpr * cam.zoom,
      -cam.x * cam.zoom * this.dpr,
      -cam.y * cam.zoom * this.dpr,
    );

    const vx = cam.x;
    const vy = cam.y;
    const vw = this.viewW / cam.zoom;
    const vh = this.viewH / cam.zoom;
    const pad = 90;
    const vis = (x, y, r) =>
      x + r > vx - pad && x - r < vx + vw + pad && y + r > vy - pad && y - r < vy + vh + pad;

    // terrain: only the visible source rectangle is touched
    const sx = Math.max(0, Math.floor(vx));
    const sy = Math.max(0, Math.floor(vy));
    const sw = Math.min(WORLD_W - sx, Math.ceil(vw) + 2);
    const sh = Math.min(WORLD_H - sy, Math.ceil(vh) + 2);
    if (sw > 0 && sh > 0) ctx.drawImage(this.terrain, sx, sy, sw, sh, sx, sy, sw, sh);

    // water shimmer
    const t = game.time;
    ctx.save();
    ctx.globalAlpha = 0.16;
    ctx.strokeStyle = '#dff0ff';
    ctx.lineWidth = 2;
    for (const w of this.waterTiles) {
      if (!vis(w.x, w.y, TILE)) continue;
      const phase = Math.sin(t * 1.1 + (w.x + w.y) * 0.02);
      if (phase < 0.45) continue;
      const yy = w.y + Math.sin(t * 0.9 + w.x * 0.03) * 3;
      ctx.beginPath();
      ctx.moveTo(w.x - 9, yy);
      ctx.lineTo(w.x + 9, yy);
      ctx.stroke();
    }
    ctx.restore();

    // Depth-sorted world objects: everything is ordered by its ground contact
    // point so nearer things overlap what is behind them.
    const list = this.drawList;
    list.length = 0;
    for (const n of game.resources) {
      if (n.kind === 'farm') continue;
      if (!game.isExplored(0, n.x, n.y)) continue;
      if (!vis(n.x, n.y, 28)) continue;
      list.push({ y: n.y + 16, kind: 0, ref: n });
    }
    for (const b of game.buildings) {
      if (b.team !== 0 && !game.isVisible(0, b.x, b.y - b.h * TILE * 0.2)) continue;
      if (!vis(b.x, b.y, Math.max(b.w, b.h) * TILE * 0.8 + 60)) continue;
      list.push({ y: b.y + (b.h * TILE) / 2, kind: 1, ref: b });
    }
    for (const u of game.units) {
      if (u.team !== 0 && !game.isVisible(0, u.x, u.y)) continue;
      if (!vis(u.x, u.y, 34)) continue;
      list.push({ y: u.y + 8, kind: 2, ref: u });
    }
    list.sort((a, b) => a.y - b.y);
    for (const d of list) {
      if (d.kind === 0) drawResource(ctx, d.ref, t);
      else if (d.kind === 1) drawBuilding(ctx, d.ref, view.isSelected(d.ref), t);
      else drawUnit(ctx, d.ref, view.isSelected(d.ref));
    }

    // arrows in flight
    for (const a of game.arrows) {
      ctx.save();
      ctx.translate(a.x, a.y);
      ctx.rotate(a.angle);
      ctx.strokeStyle = '#6b4a26';
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(-9, 0);
      ctx.lineTo(5, 0);
      ctx.stroke();
      ctx.fillStyle = '#e8eef6';
      ctx.beginPath();
      ctx.moveTo(9, 0);
      ctx.lineTo(4, -2.6);
      ctx.lineTo(4, 2.6);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#d8d2c0';
      ctx.beginPath();
      ctx.moveTo(-9, 0);
      ctx.lineTo(-6, -2.2);
      ctx.lineTo(-6, 2.2);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    // particles
    for (const p of game.particles) {
      ctx.globalAlpha = Math.max(0, p.life / p.max);
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x - p.size / 2, p.y - p.size / 2, p.size, p.size);
    }
    ctx.globalAlpha = 1;

    // fog of war sits on top of the world, under the interface
    this.refreshFog(game);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(this.fogLow, 0, 0, COLS, ROWS, 0, 0, WORLD_W, WORLD_H);

    // click rings
    for (const r of game.rings) {
      const k = 1 - r.life / r.max;
      const ease = 1 - (1 - k) * (1 - k);
      const rad = r.r0 + (r.r1 - r.r0) * ease;
      ctx.globalAlpha = Math.max(0, 1 - k) * 0.95;
      ctx.strokeStyle = r.color;
      ctx.lineWidth = r.width;
      ctx.beginPath();
      ctx.ellipse(r.x, r.y, rad, rad * 0.6, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = Math.max(0, 1 - k) * 0.35;
      ctx.beginPath();
      ctx.ellipse(r.x, r.y, rad * 0.66, rad * 0.4, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // placement ghost
    if (view.placing) {
      const { type, tx, ty, valid } = view.placing;
      const s = BUILDING_STATS[type];
      const gx = tx * TILE;
      const gy = ty * TILE;
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = valid ? '#6fd36f' : '#e05a4a';
      ctx.fillRect(gx, gy, s.w * TILE, s.h * TILE);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = valid ? '#bfffb0' : '#ffb0a0';
      ctx.lineWidth = 2;
      ctx.strokeRect(gx + 1, gy + 1, s.w * TILE - 2, s.h * TILE - 2);
      // corner ticks
      ctx.lineWidth = 3;
      const c = 10;
      const corners = [
        [gx, gy, 1, 1], [gx + s.w * TILE, gy, -1, 1],
        [gx, gy + s.h * TILE, 1, -1], [gx + s.w * TILE, gy + s.h * TILE, -1, -1],
      ];
      for (const [px, py, dx, dy] of corners) {
        ctx.beginPath();
        ctx.moveTo(px + dx * c, py);
        ctx.lineTo(px, py);
        ctx.lineTo(px, py + dy * c);
        ctx.stroke();
      }
    }

    // floaters
    ctx.textAlign = 'center';
    ctx.font = 'bold 13px Georgia, serif';
    for (const f of game.floaters) {
      ctx.globalAlpha = Math.max(0, Math.min(1, f.life / f.max));
      ctx.fillStyle = 'rgba(0,0,0,0.6)';
      ctx.fillText(f.text, f.x + 1, f.y + 1);
      ctx.fillStyle = f.color;
      ctx.fillText(f.text, f.x, f.y);
    }
    ctx.globalAlpha = 1;

    // selection marquee in screen space
    if (view.dragBox && view.dragBox.w > 2) {
      const b = view.dragBox;
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.strokeStyle = '#c8ffa0';
      ctx.lineWidth = 1.5;
      ctx.fillStyle = 'rgba(180,255,150,0.10)';
      ctx.fillRect(b.x, b.y, b.w, b.h);
      ctx.strokeRect(b.x + 0.5, b.y + 0.5, b.w, b.h);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  // Draws the base map, the fog the player has cleared, and live blips.
  drawMinimap(target, game, camera) {
    const c = this.minimapBase;
    if (!c || !target) return;
    const g = target.getContext('2d');
    if (target.width !== c.width || target.height !== c.height) {
      target.width = c.width;
      target.height = c.height;
    }
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.imageSmoothingEnabled = false;
    g.drawImage(c, 0, 0);
    const s = this.minimapScale;

    for (const b of game.buildings) {
      if (b.team !== 0 && !game.isVisible(0, b.x, b.y)) continue;
      if (b.team === 0 && !game.isExplored(0, b.x, b.y)) continue;
      g.fillStyle = b.team === 0 ? '#6f9bff' : '#ff7a68';
      g.fillRect(b.tx * s - 1, b.ty * s - 1, b.w * s + 1, b.h * s + 1);
    }
    for (const n of game.resources) {
      if (n.kind !== 'farm') continue;
      if (!game.isExplored(0, n.x, n.y)) continue;
      g.fillStyle = '#c9a94a';
      g.fillRect((n.x / TILE) * s - 1, (n.y / TILE) * s - 1, 3, 3);
    }
    for (const u of game.units) {
      if (u.team !== 0 && !game.isVisible(0, u.x, u.y)) continue;
      g.fillStyle = u.team === 0 ? '#dff0ff' : '#ffd6cf';
      g.fillRect((u.x / TILE) * s - 1, (u.y / TILE) * s - 1, 2, 2);
    }

    // fog over the minimap, same masks as the world
    this.refreshFog(game);
    g.imageSmoothingEnabled = true;
    g.drawImage(this.fogLow, 0, 0, COLS, ROWS, 0, 0, c.width, c.height);
    g.imageSmoothingEnabled = false;

    const vw = (camera.viewW / camera.zoom / TILE) * s;
    const vh = (camera.viewH / camera.zoom / TILE) * s;
    g.strokeStyle = 'rgba(255,255,255,0.85)';
    g.lineWidth = 1;
    g.strokeRect((camera.x / TILE) * s, (camera.y / TILE) * s, vw, vh);
  }

  rebuild() {
    if (this.game) {
      this.setGame(this.game);
    }
  }
}

export { RES_LABEL, RESOURCE_FROM };
