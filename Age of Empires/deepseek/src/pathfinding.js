// Grid navigation + A* pathfinding. Buildings, trees and gold mines block tiles,
// so units route around them instead of walking through.
import { TILE } from './config.js';

// 8-directional movement. Diagonal steps cost sqrt(2).
const DIRS = [
  [1, 0, 1],
  [-1, 0, 1],
  [0, 1, 1],
  [0, -1, 1],
  [1, 1, Math.SQRT2],
  [1, -1, Math.SQRT2],
  [-1, 1, Math.SQRT2],
  [-1, -1, Math.SQRT2],
];

export class NavGrid {
  constructor(cols, rows) {
    this.cols = cols;
    this.rows = rows;
    this.blocked = new Uint8Array(cols * rows);
  }

  idx(c, r) {
    return r * this.cols + c;
  }

  inBounds(c, r) {
    return c >= 0 && r >= 0 && c < this.cols && r < this.rows;
  }

  isBlocked(c, r) {
    if (!this.inBounds(c, r)) return true;
    return this.blocked[r * this.cols + c] === 1;
  }

  set(c, r, v) {
    if (!this.inBounds(c, r)) return;
    this.blocked[r * this.cols + c] = v ? 1 : 0;
  }

  setRect(c, r, w, h, v) {
    for (let y = r; y < r + h; y++) {
      for (let x = c; x < c + w; x++) this.set(x, y, v);
    }
  }

  // True when a straight line between two world points crosses no blocked tile.
  lineClear(x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const dist = Math.hypot(dx, dy);
    const steps = Math.max(1, Math.ceil(dist / (TILE * 0.4)));
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const c = Math.floor((x1 + dx * t) / TILE);
      const r = Math.floor((y1 + dy * t) / TILE);
      if (this.isBlocked(c, r)) return false;
    }
    return true;
  }
}

class MinHeap {
  constructor() {
    this.items = [];
  }

  get size() {
    return this.items.length;
  }

  push(f, v) {
    const it = this.items;
    it.push({ f, v });
    let i = it.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (it[p].f <= it[i].f) break;
      const tmp = it[p];
      it[p] = it[i];
      it[i] = tmp;
      i = p;
    }
  }

  pop() {
    const it = this.items;
    const top = it[0];
    const last = it.pop();
    if (it.length) {
      it[0] = last;
      let i = 0;
      const n = it.length;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < n && it[l].f < it[m].f) m = l;
        if (r < n && it[r].f < it[m].f) m = r;
        if (m === i) break;
        const tmp = it[m];
        it[m] = it[i];
        it[i] = tmp;
        i = m;
      }
    }
    return top;
  }
}

// Ring search for an unblocked cell near (c, r). Returns null when nothing found.
function nearestOpen(grid, c, r, maxRing = 6) {
  if (!grid.isBlocked(c, r)) return { c, r };
  for (let ring = 1; ring <= maxRing; ring++) {
    let best = null;
    let bestD = Infinity;
    for (let dy = -ring; dy <= ring; dy++) {
      for (let dx = -ring; dx <= ring; dx++) {
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== ring) continue;
        const nc = c + dx;
        const nr = r + dy;
        if (grid.isBlocked(nc, nr)) continue;
        const d = dx * dx + dy * dy;
        if (d < bestD) {
          bestD = d;
          best = { c: nc, r: nr };
        }
      }
    }
    if (best) return best;
  }
  return null;
}

/**
 * A* on the tile grid, then string-pulled into a short waypoint list.
 * Returns { points, ok, target } where points are world-space {x, y}.
 */
export function findPath(grid, sx, sy, tx, ty, maxNodes = 4000) {
  const startCell = nearestOpen(grid, Math.floor(sx / TILE), Math.floor(sy / TILE));
  if (!startCell) return { points: null, ok: false };
  const goalCell = nearestOpen(grid, Math.floor(tx / TILE), Math.floor(ty / TILE));
  if (!goalCell) return { points: null, ok: false };

  const { cols, rows } = grid;
  const start = startCell.r * cols + startCell.c;
  const goal = goalCell.r * cols + goalCell.c;

  if (start === goal) {
    return {
      points: [{ x: tx, y: ty }],
      ok: true,
      exact: !grid.isBlocked(goalCell.c, goalCell.r),
    };
  }

  const gScore = new Float32Array(cols * rows).fill(Infinity);
  const cameFrom = new Int32Array(cols * rows).fill(-1);
  const closed = new Uint8Array(cols * rows);
  const open = new MinHeap();

  const h = (c, r) => {
    const dx = Math.abs(c - goalCell.c);
    const dy = Math.abs(r - goalCell.r);
    // Octile distance: admissible for 8-way movement.
    return (dx + dy) + (Math.SQRT2 - 2) * Math.min(dx, dy);
  };

  gScore[start] = 0;
  open.push(h(startCell.c, startCell.r), start);
  let expanded = 0;
  let found = false;

  while (open.size) {
    const node = open.pop();
    const cur = node.v;
    if (closed[cur]) continue;
    closed[cur] = 1;
    if (cur === goal) {
      found = true;
      break;
    }
    if (++expanded > maxNodes) break;

    const c = cur % cols;
    const r = (cur - c) / cols;
    for (const [dx, dy, cost] of DIRS) {
      const nc = c + dx;
      const nr = r + dy;
      if (grid.isBlocked(nc, nr)) continue;
      // No cutting corners between two blocked diagonals.
      if (dx !== 0 && dy !== 0) {
        if (grid.isBlocked(c + dx, r) || grid.isBlocked(c, r + dy)) continue;
      }
      const ni = nr * cols + nc;
      if (closed[ni]) continue;
      const ng = gScore[cur] + cost;
      if (ng < gScore[ni]) {
        gScore[ni] = ng;
        cameFrom[ni] = cur;
        open.push(ng + h(nc, nr), ni);
      }
    }
  }

  let endIndex = goal;
  if (!found) {
    // Unreachable goal: walk to the closest explored cell instead of giving up.
    let best = -1;
    let bestH = Infinity;
    for (let i = 0; i < gScore.length; i++) {
      if (!closed[i] || gScore[i] === Infinity) continue;
      const c = i % cols;
      const r = (i - c) / cols;
      const hv = h(c, r);
      if (hv < bestH) {
        bestH = hv;
        best = i;
      }
    }
    if (best < 0) return { points: null, ok: false };
    endIndex = best;
  }

  const cells = [];
  let cur = endIndex;
  let guard = 0;
  while (cur !== -1 && guard++ < cols * rows) {
    const c = cur % cols;
    const r = (cur - c) / cols;
    cells.push({ c, r });
    if (cur === start) break;
    cur = cameFrom[cur];
  }
  cells.reverse();

  const pts = cells.map((cell) => ({
    x: cell.c * TILE + TILE / 2,
    y: cell.r * TILE + TILE / 2,
  }));

  // Final approach: aim at the real target if it sits in an open tile.
  const endOpen = !grid.isBlocked(goalCell.c, goalCell.r);
  if (endOpen && (found || goalCell.c === cells[cells.length - 1].c)) {
    pts[pts.length - 1] = { x: tx, y: ty };
  } else if (pts.length) {
    const last = pts[pts.length - 1];
    if (Math.hypot(last.x - tx, last.y - ty) > TILE * 2.5) {
      // Target is deep inside blocked space; stop at the nearest reachable tile.
    }
  }

  // String pulling: drop waypoints when a straight line to a later one is clear.
  const smoothed = [];
  let i = 1; // cell index 0 is the unit's own tile; skip it.
  smoothed.push(pts[0]);
  while (i < pts.length - 1) {
    let j = pts.length - 1;
    let advanced = false;
    while (j > i) {
      const a = pts[i - 1];
      const b = pts[j];
      if (grid.lineClear(a.x, a.y, b.x, b.y)) {
        smoothed.push(b);
        i = j + 1;
        advanced = true;
        break;
      }
      j--;
    }
    if (!advanced) {
      smoothed.push(pts[i]);
      i++;
    }
  }
  if (i === pts.length - 1) smoothed.push(pts[pts.length - 1]);

  // Drop the leading waypoint when the unit is already standing on it.
  while (smoothed.length > 1 && Math.hypot(smoothed[0].x - sx, smoothed[0].y - sy) < TILE * 0.6) {
    smoothed.shift();
  }

  return { points: smoothed, ok: found };
}
