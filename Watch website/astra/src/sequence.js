// Bounded frame transport: 13 decoded images, 3 concurrent requests, no full-film preload.
export class FrameCache {
  constructor(source, onFrame, { radius = 6, concurrency = 3 } = {}) {
    this.source = source;
    this.onFrame = onFrame;
    this.radius = radius;
    this.concurrency = concurrency;
    this.cache = new Map();
    this.pending = new Map();
    this.failed = new Set();
    this.target = 0;
    this.destroyed = false;
  }
  url(index) {
    return this.source.pattern.replace(
      "{frame}",
      String(index + (this.source.startIndex ?? 1)).padStart(
        this.source.padding ?? 4,
        "0",
      ),
    );
  }
  seek(index) {
    if (this.destroyed || !this.source.frameCount || !this.source.pattern)
      return;
    this.target = Math.max(
      0,
      Math.min(this.source.frameCount - 1, Math.round(index)),
    );
    for (const [i, bitmap] of this.cache)
      if (Math.abs(i - this.target) > this.radius) {
        bitmap.close();
        this.cache.delete(i);
      }
    for (const [i, controller] of this.pending)
      if (Math.abs(i - this.target) > this.radius) controller.abort();
    if (this.cache.has(this.target))
      this.onFrame(this.cache.get(this.target), this.target);
    this.pump();
  }
  pump() {
    if (this.destroyed) return;
    const indices = [this.target];
    for (let d = 1; d <= this.radius; d++)
      indices.push(this.target + d, this.target - d);
    for (const index of indices) {
      if (this.pending.size >= this.concurrency) break;
      if (
        index < 0 ||
        index >= this.source.frameCount ||
        this.cache.has(index) ||
        this.pending.has(index) ||
        this.failed.has(index)
      )
        continue;
      const controller = new AbortController();
      this.pending.set(index, controller);
      fetch(this.url(index), { signal: controller.signal })
        .then((r) => {
          if (!r.ok) throw new Error(`Frame ${index}: ${r.status}`);
          return r.blob();
        })
        .then((blob) => createImageBitmap(blob))
        .then((bitmap) => {
          if (
            this.destroyed ||
            controller.signal.aborted ||
            Math.abs(index - this.target) > this.radius
          ) {
            bitmap.close();
            return;
          }
          this.cache.set(index, bitmap);
          if (index === this.target) this.onFrame(bitmap, index);
        })
        .catch((error) => {
          if (error.name !== "AbortError" && !controller.signal.aborted)
            this.failed.add(index);
        })
        .finally(() => {
          this.pending.delete(index);
          this.pump();
        });
    }
  }
  dispose() {
    this.destroyed = true;
    for (const controller of this.pending.values()) controller.abort();
    for (const bitmap of this.cache.values()) bitmap.close();
    this.pending.clear();
    this.cache.clear();
    this.failed.clear();
  }
}
export const storyDistances = (mobile) =>
  mobile ? [0.7, 0.65, 0.55, 0.8] : [1, 0.9, 0.85, 1.2];

export function timeline(
  progress,
  mobile,
  frameStops = [0, 0.28, 0.57, 0.72, 1],
) {
  const distances = storyDistances(mobile);
  const total = distances.reduce((a, b) => a + b, 0);
  const travel = Math.max(0, Math.min(1, progress)) * total;
  let start = 0,
    beat = 3,
    local = 1;
  for (let i = 0; i < distances.length; i++) {
    if (travel <= start + distances[i]) {
      beat = i;
      local = (travel - start) / distances[i];
      break;
    }
    start += distances[i];
  }
  // Reading holds belong only at the opening and final image. Intermediate beats
  // connect continuously, so a scene boundary never consumes a wheel gesture.
  const before = beat === 0 ? 0.12 : 0;
  const after = beat === 3 ? 0.12 : 0;
  const motion = Math.max(
    0,
    Math.min(1, (local - before) / (1 - before - after)),
  );
  const frames = frameStops;
  return {
    beat,
    frameProgress: frames[beat] + (frames[beat + 1] - frames[beat]) * motion,
  };
}
