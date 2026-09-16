/**
 * Scroll performance probe: drives a synthetic scroll through the pinned stage and
 * reports frame pacing plus loader counters from inside the page.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9346;
const job = JSON.parse(readFileSync(process.argv[2] || 'tools/perf.json', 'utf8'));
mkdirSync('build', { recursive: true });

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-color-profile=srgb',
  `--remote-debugging-port=${PORT}`, '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=build/chrome-perf', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function endpoint() {
  for (let i = 0; i < 80; i += 1) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('no chrome page');
}

const ws = new WebSocket(await endpoint());
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0;
const pending = new Map();
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
  }
};
const send = (method, params = {}) => new Promise((resolve, reject) => {
  id += 1; pending.set(id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params }));
});

async function run(view) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: view.width, height: view.height, deviceScaleFactor: 1, mobile: Boolean(view.mobile),
    screenWidth: view.width, screenHeight: view.height, positionX: 0, positionY: 0,
  });
  await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
  await sleep(view.settle ?? 3500);

  const result = await send('Runtime.evaluate', {
    expression: `new Promise((resolve) => {
      const sp = window.__stage;
      if (!sp) { resolve({ error: 'no player' }); return; }
      const start = performance.now();
      let draws = 0, maxGap = 0, last = start, frames = [];
      // measure the real animation-frame cadence available on this machine
      let rafs = 0, lastRaf = performance.now(), rafGaps = [];
      const countRaf = () => {
        const t = performance.now();
        rafGaps.push(t - lastRaf); lastRaf = t; rafs += 1;
        if (rafs < 400) requestAnimationFrame(countRaf);
      };
      requestAnimationFrame(countRaf);

      const originalBlit = sp.blit.bind(sp);
      sp.blit = (b) => { draws += 1; frames.push(sp.current); return originalBlit(b); };
      const originalDraw = sp.draw.bind(sp);
      sp.draw = () => { const t = performance.now(); originalDraw();
        const dt = t - last; if (dt > maxGap) maxGap = dt; last = t; };

      const track = document.querySelector('[data-stage-track]');
      const travel = Math.max(1, track.getBoundingClientRect().height - window.innerHeight);
      const steps = 260, duration = ${view.durationMs ?? 6000};
      let i = 0;
      const tick = () => {
        i += 1;
        const p = i / steps;
        window.scrollTo(0, p * travel);
        requestAnimationFrame(() => requestAnimationFrame(tick));
        if (i >= steps) {
          const elapsed = performance.now() - start;
          resolve({
            variant: sp.variantKey,
            frames: sp.frames.length,
            decoded: sp.loaded.size,
            aliveQueue: sp.order.length,
            loadStats: sp.loadStats || null,
            inFlight: sp.inFlight.size,
            active: sp.active,
            draws,
            distinctFrames: new Set(frames).size,
            uniqueTargets: new Set(frames).size,
            maxDrawGapMs: Math.round(maxGap),
            rafs,
            rafPerSec: +(rafs / (elapsedMs / 1000)).toFixed(1),
            rafMedianGapMs: Math.round(rafGaps.sort((a, b) => a - b)[Math.floor(rafGaps.length / 2)] || 0),
            scrollSteps: steps,
            elapsedMs: Math.round(elapsed),
            avgDrawsPerFrameMs: +(draws / elapsed).toFixed(3)
          });
        }
      };
      requestAnimationFrame(tick);
    })`,
    awaitPromise: true,
    returnByValue: true,
  });
  return result.result.value;
}

const out = [];
for (const view of job.views) out.push({ view: view.name, ...(await run(view)) });
writeFileSync('build/scroll-perf.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
ws.close();
chrome.kill();
process.exit(0);
