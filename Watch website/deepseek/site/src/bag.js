/**
 * Bag state: persisted locally, with explicit reset. Pure demo — nothing is
 * transmitted anywhere and no order is ever placed.
 */

const KEY = 'meridian.bag.v1';

export function money(n) {
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const clean = {};
    for (const [id, qty] of Object.entries(parsed)) {
      const n = Math.max(1, Math.min(9, Math.round(Number(qty))));
      if (Number.isFinite(n)) clean[id] = n;
    }
    return clean;
  } catch (err) {
    return {};
  }
}

function write(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch (err) {
    /* private mode / quota — the bag still works for this session */
  }
}

export class Bag {
  constructor(catalog, { onChange } = {}) {
    this.catalog = new Map(catalog.map((p) => [p.id, p]));
    this.state = read();
    this.onChange = onChange || (() => {});
  }

  lines() {
    return Object.entries(this.state)
      .filter(([id]) => this.catalog.has(id))
      .map(([id, qty]) => ({ product: this.catalog.get(id), qty, line: qty * this.catalog.get(id).price }));
  }

  count() {
    return this.lines().reduce((n, l) => n + l.qty, 0);
  }

  subtotal() {
    return this.lines().reduce((n, l) => n + l.line, 0);
  }

  add(id, qty = 1) {
    if (!this.catalog.has(id)) return;
    const next = Math.min(9, (this.state[id] || 0) + qty);
    this.state[id] = next;
    this.commit();
    return next;
  }

  setQty(id, qty) {
    if (qty <= 0) return this.remove(id);
    this.state[id] = Math.min(9, qty);
    this.commit();
  }

  remove(id) {
    delete this.state[id];
    this.commit();
  }

  reset() {
    this.state = {};
    try {
      localStorage.removeItem(KEY);
    } catch (err) {
      /* ignore */
    }
    this.commit(true);
  }

  commit(force) {
    write(this.state);
    this.onChange(this, { force });
  }
}
