// Deterministic map generation: terrain, water, forests, berries, gold.
import { TILE, COLS, ROWS, BASE_POS } from './config.js';

const BASE_CLEAR = 200; // pixels kept free of blocking scenery around each base

function nearBase(x, y, pad = 0) {
  for (const b of BASE_POS) {
    if (Math.hypot(x - b.x, y - b.y) < BASE_CLEAR + pad) return true;
  }
  return false;
}

// Three ponds give the map shape and force paths around water.
// Coordinates are in tiles.
const PONDS = [
  { x: 38, y: 9, rx: 5, ry: 4 },
  { x: 42, y: 50, rx: 6, ry: 4 },
  { x: 64, y: 39, rx: 4, ry: 5 },
];

function smoothstep(t) {
  return t * t * (3 - 2 * t);
}

export function generateWorld(game, rng) {
  const n = COLS * ROWS;
  const terrain = new Uint8Array(n); // 0 grass, 1 water
  game.terrain = terrain;

  // Coarse value noise for grass shading and dry patches.
  const gw = 20;
  const gh = 15;
  const grid = new Float32Array((gw + 1) * (gh + 1));
  for (let i = 0; i < grid.length; i++) grid[i] = rng();
  const g = (xx, yy) => grid[Math.min(gh, yy) * (gw + 1) + Math.min(gw, xx)];

  const noise = new Float32Array(n);
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      const fx = (x / COLS) * gw;
      const fy = (y / ROWS) * gh;
      const x0 = Math.floor(fx);
      const y0 = Math.floor(fy);
      const tx = smoothstep(fx - x0);
      const ty = smoothstep(fy - y0);
      const a = g(x0, y0);
      const b = g(x0 + 1, y0);
      const c = g(x0, y0 + 1);
      const d = g(x0 + 1, y0 + 1);
      const top = a * (1 - tx) + b * tx;
      const bot = c * (1 - tx) + d * tx;
      noise[y * COLS + x] = top * (1 - ty) + bot * ty;
    }
  }
  game.noise = noise;

  // Ponds (skipped if they would swallow a base plaza).
  for (const p of PONDS) {
    const worldX = (p.x + 0.5) * TILE;
    const worldY = (p.y + 0.5) * TILE;
    if (nearBase(worldX, worldY, 120)) continue;
    for (let dy = -p.ry - 1; dy <= p.ry + 1; dy++) {
      for (let dx = -p.rx - 1; dx <= p.rx + 1; dx++) {
        const cx = p.x + dx;
        const cy = p.y + dy;
        if (cx < 0 || cy < 0 || cx >= COLS || cy >= ROWS) continue;
        const d = (dx / p.rx) ** 2 + (dy / p.ry) ** 2;
        const wobble = (noise[cy * COLS + cx] - 0.5) * 0.7;
        if (d + wobble < 1) {
          terrain[cy * COLS + cx] = 1;
          game.nav.set(cx, cy, true);
        }
      }
    }
  }

  // Guaranteed forest near each base so the opening always has wood.
  const homeForest = [
    { x: BASE_POS[0].x + 250, y: BASE_POS[0].y + 60, count: 12, spread: 3.4 },
    { x: BASE_POS[0].x + 60, y: BASE_POS[0].y - 200, count: 10, spread: 3.0 },
    { x: BASE_POS[1].x - 250, y: BASE_POS[1].y - 60, count: 12, spread: 3.4 },
    { x: BASE_POS[1].x + 40, y: BASE_POS[1].y + 210, count: 10, spread: 3.0 },
  ];
  for (const f of homeForest) cluster(game, rng, 'tree', f.x, f.y, f.count, f.spread, true);

  // Guaranteed berry + gold near each base.
  cluster(game, rng, 'berry', BASE_POS[0].x + 190, BASE_POS[0].y - 30, 7, 2.4, true);
  cluster(game, rng, 'gold', BASE_POS[0].x - 20, BASE_POS[0].y - 170, 6, 2.2, true);
  cluster(game, rng, 'berry', BASE_POS[1].x - 190, BASE_POS[1].y + 30, 7, 2.4, true);
  cluster(game, rng, 'gold', BASE_POS[1].x + 20, BASE_POS[1].y + 170, 6, 2.2, true);

  // Scattered wilderness.
  scatter(game, rng, 'tree', 44, 5, 11, 4.2);
  scatter(game, rng, 'gold', 7, 4, 6, 2.2);
  scatter(game, rng, 'berry', 7, 4, 6, 2.4);

  // Central contested gold, roughly equidistant from both bases.
  cluster(game, rng, 'gold', COLS / 2, ROWS / 2, 7, 2.3, true);
  cluster(game, rng, 'berry', COLS / 2 - 7, ROWS / 2 + 4, 6, 2.4, true);
}

function cluster(game, rng, kind, px, py, count, spreadTiles, allowNearBase = false) {
  const spread = spreadTiles * TILE;
  let placed = 0;
  for (let i = 0; i < count * 6 && placed < count; i++) {
    const ang = rng() * Math.PI * 2;
    const rad = Math.sqrt(rng()) * spread;
    const x = px + Math.cos(ang) * rad;
    const y = py + Math.sin(ang) * rad;
    if (!allowNearBase && nearBase(x, y, 40)) continue;
    if (game.createResource(kind, x, y)) placed++;
  }
}

function scatter(game, rng, kind, clusters, minCount, maxCount, spreadTiles) {
  for (let c = 0; c < clusters; c++) {
    const px = (0.08 + rng() * 0.84) * COLS * TILE;
    const py = (0.08 + rng() * 0.84) * ROWS * TILE;
    if (nearBase(px, py, 80)) continue;
    const count = minCount + Math.floor(rng() * (maxCount - minCount + 1));
    cluster(game, rng, kind, px, py, count, spreadTiles);
  }
}
