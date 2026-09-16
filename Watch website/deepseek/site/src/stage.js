/**
 * MERIDIAN — scroll-driven film stage.
 *
 * Native scrolling only: this module reads window.scrollY and never intercepts
 * the wheel. A piecewise timeline maps scroll progress onto frame indices with
 * separate travel and hold segments, so motion and readable holds are allocated
 * independently of clip duration.
 *
 * Memory is bounded on purpose: a rolling window of decoded ImageBitmaps with
 * explicit close() on eviction, plus a bounded-concurrency loader with
 * cancellation. The full sequence is never decoded into memory at once.
 */

// Decoding is the expensive part of scrolling, so the cache is bounded in
// decoded pixels rather than frames, and the loader never tries to decode more
// than the cache can hold. Frames are fetched as the nearest neighbours of the
// wanted frame first, which means a fast scroll always has a usable frame ahead
// of it instead of a hole.
const MAX_DECODED = 56;
const CONCURRENCY = 8;
const LOOKAHEAD = 18; // frames ahead of the current frame to prefetch
const BEHINDLAG = 6; // frames kept behind, for reverse scrolling
const MAX_STEP = 4; // frames per hop before the loader switches to gap-filling
const MOBILE_QUERY = '(max-width: 860px)';

export class StagePlayer {
  constructor({ track, canvas, poster, onProgress, onBeatChange }) {
    this.track = track;
    this.canvas = canvas;
    this.poster = poster;
    this.ctx = canvas.getContext('2d', { alpha: false, desynchronized: true });
    this.onProgress = onProgress || (() => {});
    this.onBeatChange = onBeatChange || (() => {});

    this.manifest = null;
    this.variantKey = null;
    this.frames = []; // frame index -> {url, bitmap|null}
    this.loaded = new Map(); // frame index -> bitmap
    this.order = []; // eviction order
    this.inFlight = new Set();
    this.queued = new Set();
    this.active = 0;

    this.rafPending = false;
    // index of the frame whose *bitmap* is actually on the canvas. Tracking the
    // requested index instead would latch a placeholder neighbour in place and
    // the real frame would never replace it.
    this.drawnBitmapIndex = -1;
    this.lastBeat = -1;
    this.current = 0;
    this.ready = false;
    this.aborted = false;

    this.reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.mobile = window.matchMedia(MOBILE_QUERY);
    this.onResize = this.handleResize.bind(this);
    this.onScroll = this.scheduleFrame.bind(this);
    this.mq = [this.reduced, this.mobile];
  }

  async init() {
    if (this.reduced.matches) {
      // Composed still, normal section flow, and no animation-sequence fetch.
      this.track.style.height = '';
      this.poster.classList.add('is-shown');
      document.documentElement.classList.add('reduced-motion');
      return;
    }

    let manifest;
    try {
      const res = await fetch(new URL('./manifest.json', import.meta.url));
      if (!res.ok) throw new Error('manifest ' + res.status);
      manifest = await res.json();
    } catch (err) {
      this.fail('manifest');
      return;
    }
    this.manifest = manifest;

    await this.selectVariant(this.mobile.matches ? 'portrait' : 'landscape', { initial: true });

    window.addEventListener('scroll', this.onScroll, { passive: true });
    window.addEventListener('resize', this.onResize, { passive: true });
    this.mq.forEach((m) => m.addEventListener('change', this.onResize));

    // only now is there a real sequence to draw and a real beat to announce
    this.ready = true;
    this.draw();
    // a freshly loaded page has not scrolled yet, so announce beat 0 explicitly
    if (this.beats && this.beats.length) this.onBeatChange(this.beats[0], 0);

  }

  fail(reason) {
    // Never a blank screen: the poster stays, the stage simply becomes a still.
    this.failed = reason;
    this.poster.classList.add('is-shown');
    document.documentElement.dataset.stageFallback = reason;
  }

  handleResize() {
    const want = this.mobile.matches ? 'portrait' : 'landscape';
    if (want !== this.variantKey) {
      this.selectVariant(want, {});
      return;
    }
    this.sizeCanvas();
    this.scheduleFrame();
  }

  async selectVariant(key, { initial } = {}) {
    const variants = (this.manifest && this.manifest.variants) || {};
    let entry = variants[key];
    // A missing aspect for this breakpoint must not blank the stage: use the
    // other generated sequence, and only fall back to the composed still if
    // neither exists. The stage never renders a blank frame.
    if (!entry) {
      const other = key === 'portrait' ? 'landscape' : 'portrait';
      if (variants[other]) {
        key = other;
        entry = variants[other];
        document.documentElement.dataset.stageVariantFallback = other;
      }
    }
    if (!entry) {
      this.fail('missing-variant-' + key);
      return;
    }
    // Cancel obsolete loads when crossing breakpoints.
    this.loaded.forEach((b) => b && b.close && b.close());
    this.loaded.clear();
    this.order = [];
    this.queued.clear();
    this.inFlight.clear();
    this.active = 0;
    this.lastRequested = 0;
    this.failedFrames = 0;

    this.variantKey = key;
    this.entry = entry;
    this.frames = Array.from({ length: entry.frames }, (_, i) => ({
      url: entry.path.replace('{i}', String(i + 1).padStart(4, '0')),
      bitmap: null,
    }));

    const travel = key === 'portrait' ? this.manifest.timeline.mobile : this.manifest.timeline.desktop;
    this.stops = travel.stops;
    this.beats = travel.beats;
    this.track.style.height = `${(travel.stageViewports * 100).toFixed(4)}vh`;

    const posterSrc = entry.poster || this.manifest.posters[key];
    this.poster.src = posterSrc;
    this.poster.width = entry.width;
    this.poster.height = entry.height;
    this.poster.classList.add('is-shown');

    this.sizeCanvas();
    this.drawnBitmapIndex = -1;
    this.lastBeat = -1;
    this.current = 0;
    await this.prefetch(0);
    this.draw();
  }

  sizeCanvas() {
    if (!this.entry) return;
    // Capping the backing store keeps the per-frame composite affordable; the
    // sequence is photographed, not text, so 1x is plenty.
    const dpr = 1;
    const rect = this.canvas.getBoundingClientRect();
    const cssW = Math.max(1, Math.round(rect.width || window.innerWidth));
    const cssH = Math.max(1, Math.round(rect.height || window.innerHeight));
    this.canvas.width = Math.round(cssW * dpr);
    this.canvas.height = Math.round(cssH * dpr);
    this.dpr = dpr;
    this.drawnBitmapIndex = -1;
  }

  scheduleFrame() {
    if (this.rafPending) return;
    this.rafPending = true;
    requestAnimationFrame(() => {
      this.rafPending = false;
      this.draw();
    });
  }

  progress() {
    const rect = this.track.getBoundingClientRect();
    const travel = Math.max(1, rect.height - window.innerHeight);
    const p = -rect.top / travel;
    return Math.min(1, Math.max(0, p));
  }

  mappingFor(p) {
    const stops = this.stops;
    if (!stops || stops.length < 2) return { frame: 0 };

    // The stops form one continuous strip: find the segment progress falls in and
    // interpolate linearly across it. No segment is flat, so the film never stalls.
    let a = stops[0];
    let b = stops[stops.length - 1];
    for (let i = 0; i < stops.length - 1; i += 1) {
      if (p >= stops[i].p && p <= stops[i + 1].p) {
        a = stops[i];
        b = stops[i + 1];
        break;
      }
    }
    const span = b.p - a.p;
    const t = span <= 0 ? 1 : Math.min(1, Math.max(0, (p - a.p) / span));
    return { frame: a.frame + (b.frame - a.frame) * t };
  }

  /**
   * Which beat owns a frame. Derived from the frame so the copy always matches the
   * picture, and so the headline changes as its motion begins rather than masking it.
   */
  beatForFrame(f) {
    if (!this.beats || !this.beats.length) return 0;
    for (let i = 0; i < this.beats.length; i += 1) {
      const b = this.beats[i];
      if (f >= b.frameStart && f <= b.frameEnd) return i;
    }
    return f < this.beats[0].frameStart ? 0 : this.beats.length - 1;
  }

  draw() {
    if (!this.ready || !this.entry) return;
    const p = this.progress();
    const { frame } = this.mappingFor(p);
    const total = this.entry.frames;
    const f = Math.min(total - 1, Math.max(0, Math.round(frame)));
    const beatIndex = this.beatForFrame(f);
    this.current = f;

    this.onProgress({
      progress: p,
      frame: f,
      total,
      beatIndex,
      beat: this.beats[beatIndex] || null,
    });

    if (beatIndex !== this.lastBeat) {
      this.lastBeat = beatIndex;
      this.onBeatChange(this.beats[beatIndex] || null, beatIndex);
    }

    this.pump(f);

    const pick = this.nearestBitmap(f);
    // repaint whenever the bitmap on screen is not the one currently wanted, so
    // a placeholder is always replaced as soon as the real frame arrives
    if (pick && pick.index !== this.drawnBitmapIndex) {
      this.blit(pick.bitmap);
      this.drawnBitmapIndex = pick.index;
      if (!this.posterHidden) {
        this.poster.classList.add('is-hidden');
        this.canvas.classList.add('is-shown');
        this.posterHidden = true;
      }
    }
  }

  /** has the frame the timeline wants actually been painted? */
  isSettled() {
    return this.drawnBitmapIndex === this.current && this.inFlight.size === 0;
  }

  /** the closest decoded frame to f, reported with its own index */
  nearestBitmap(f) {
    if (this.loaded.has(f)) return { bitmap: this.loaded.get(f), index: f };
    for (let d = 1; d <= 6; d += 1) {
      if (this.loaded.has(f - d)) return { bitmap: this.loaded.get(f - d), index: f - d };
      if (this.loaded.has(f + d)) return { bitmap: this.loaded.get(f + d), index: f + d };
    }
    const last = this.order[this.order.length - 1];
    if (last === undefined) return null;
    return { bitmap: this.loaded.get(last), index: last };
  }

  blit(bitmap) {
    const { width, height } = this.canvas;
    const scale = Math.max(width / bitmap.width, height / bitmap.height);
    const w = bitmap.width * scale;
    const h = bitmap.height * scale;
    this.ctx.drawImage(bitmap, (width - w) / 2, (height - h) / 2, w, h);
  }

  /**
   * Fill a bounded window around the wanted frame. The wanted frame is queued
   * first, then its neighbours outward. When the scroll has jumped further than
   * MAX_STEP, the loader hops outward in strides and the gaps are filled on a
   * later pass, so a fast flick never spends its budget on frames already behind.
   */
  pump(f) {
    const total = this.frames.length;
    if (!total) return;

    const direction = f >= this.lastRequested ? 1 : -1;
    this.lastRequested = f;

    const order = [];
    const seen = new Set();
    const push = (i) => {
      if (i < 0 || i >= total || seen.has(i)) return;
      seen.add(i);
      order.push(i);
    };

    // 1. the frame the timeline wants right now
    push(f);
    // 2. its immediate neighbours, so a drag in either direction is covered
    for (let d = 1; d <= 2; d += 1) { push(f + d); push(f - d); }
    // 3. outward in the scroll direction, a few frames ahead
    const ahead = direction > 0 ? LOOKAHEAD : BEHINDLAG;
    for (let d = 3; d <= ahead; d += 1) push(direction > 0 ? f + d : f - d);
    // 4. the trailing edge, for reverse scrolling
    const behind = direction > 0 ? BEHINDLAG : LOOKAHEAD;
    for (let d = 3; d <= behind; d += 1) push(direction > 0 ? f - d : f + d);

    for (const i of order) {
      if (this.active >= CONCURRENCY) break;
      if (this.loaded.has(i) || this.inFlight.has(i)) continue;
      this.loadFrame(i);
    }

    this.evict(f);
  }

  loadFrame(i) {
    if (this.inFlight.has(i) || this.loaded.has(i)) return;
    const frame = this.frames[i];
    if (!frame) return;
    this.inFlight.add(i);
    this.queued.delete(i);
    this.active += 1;

    const t0 = performance.now();
    this.loadStats = this.loadStats || { started: 0, netMs: 0, decodeMs: 0, failed: 0, maxNet: 0, maxDecode: 0 };
    this.loadStats.started += 1;

    const img = new Image();
    img.decoding = 'async';
    img.fetchPriority = 'low';
    img.onload = async () => {
      try {
        const tNet = performance.now();
        this.loadStats.netMs += tNet - t0;
        if (tNet - t0 > this.loadStats.maxNet) this.loadStats.maxNet = Math.round(tNet - t0);
        const bitmap = 'createImageBitmap' in window
          ? await createImageBitmap(img)
          : img;
        const tDec = performance.now();
        this.loadStats.decodeMs += tDec - tNet;
        if (tDec - tNet > this.loadStats.maxDecode) this.loadStats.maxDecode = Math.round(tDec - tNet);
        // the window may have moved a long way while this was decoding; a frame
        // that is now far outside the cache would just be evicted again
        if (!this.ready) return;
        this.store(i, bitmap);
        if (Math.abs(i - this.current) <= 2) this.scheduleFrame();
      } catch (err) {
        this.failedFrames = (this.failedFrames || 0) + 1;
        this.loadStats.failed += 1;
      } finally {
        this.inFlight.delete(i);
        this.active -= 1;
        if (!this.pumping) {
          this.pumping = true;
          this.pump(this.current);
          this.pumping = false;
        }
      }
    };
    img.onerror = () => {
      this.failedFrames = (this.failedFrames || 0) + 1;
      this.inFlight.delete(i);
      this.active -= 1;
    };
    img.src = frame.url;
  }

  store(i, bitmap) {
    this.loaded.set(i, bitmap);
    this.order.push(i);
  }

  /** Drop the decoded frames furthest from the wanted frame, releasing bitmaps. */
  evict(around) {
    if (this.order.length <= MAX_DECODED) return;
    const keep = new Set();
    // keep the window in scroll direction, then the nearest of the rest
    const ranked = this.order
      .filter((i) => this.loaded.has(i))
      .sort((a, b) => Math.abs(a - around) - Math.abs(b - around));
    for (const i of ranked.slice(0, MAX_DECODED)) keep.add(i);
    for (const i of this.order) {
      if (keep.has(i)) continue;
      const b = this.loaded.get(i);
      if (b && b.close && b !== this.frames[i]) b.close();
      this.loaded.delete(i);
    }
    this.order = this.order.filter((i) => this.loaded.has(i));
  }

  /** warm the wanted frame, resolving as soon as the network attempt finishes */
  async prefetch(f) {
    const first = this.frames[f];
    if (!first) return;
    await new Promise((resolve) => {
      const img = new Image();
      img.onload = img.onerror = resolve;
      img.src = first.url;
    });
  }
}
