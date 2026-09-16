/** Minimal rAF + scroll cadence check, with and without the film running. */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9347;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-diag','about:blank'],
  { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function endpoint() {
  for (let i = 0; i < 80; i += 1) {
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const pg = l.find((t) => t.type === 'page'); if (pg) return pg.webSocketDebuggerUrl; } catch {}
    await sleep(250);
  } throw new Error('no page');
}
const ws = new WebSocket(await endpoint());
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map();
ws.onmessage = (ev) => { const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { const { resolve, reject } = pending.get(m.id); pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result); } };
const send = (method, params = {}) => new Promise((resolve, reject) => {
  id += 1; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });

await send('Emulation.setDeviceMetricsOverride', {
  width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  screenWidth: 1440, screenHeight: 900, positionX: 0, positionY: 0,
});
await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
await sleep(4000);
const r = await send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: `new Promise((resolve) => {
  const N = 200;
  const t0 = performance.now();
  let n = 0;
  const loop = () => {
    n += 1;
    if (n < N) { requestAnimationFrame(loop); return; }
    const wall = performance.now() - t0;
    resolve({ rafPerSec: +(N / (wall / 1000)).toFixed(1), wallMs: Math.round(wall), steps: N });
  };
  requestAnimationFrame(loop);
})` });
console.log('bare rAF cadence:', JSON.stringify(r.result.value));

const s = await send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: `new Promise((resolve) => {
  const sp = window.__stage;
  window.__evicted = 0;
  const realEvict = sp.evict.bind(sp);
  sp.evict = (a) => { const before = sp.loaded.size; realEvict(a); window.__evicted += before - sp.loaded.size; };
  window.__loaded = 0;
  const realStore = sp.store.bind(sp);
  sp.store = (i, b) => { window.__loaded += 1; return realStore(i, b); };
  const track = document.querySelector('[data-stage-track]');
  const travel = Math.max(1, track.getBoundingClientRect().height - window.innerHeight);
  const durationMs = 9000;           // ~620 px/s: a normal wheel or trackpad scroll
  const t0 = performance.now();
  let n = 0, draws = 0, rafs = 0;
  const realBlit = sp.blit.bind(sp);
  sp.blit = (b) => { draws += 1; return realBlit(b); };
  const loop = () => {
    rafs += 1;
    const elapsed = performance.now() - t0;
    const t = Math.min(1, elapsed / durationMs);
    window.scrollTo(0, t * travel);
    if (t < 1) { requestAnimationFrame(loop); return; }
    const wall = performance.now() - t0;
    resolve({ rafPerSec: +(rafs / (wall / 1000)).toFixed(1), wallMs: Math.round(wall), draws, rafs,
              loaded: window.__loaded, evicted: window.__evicted,
              started: sp.loadStats ? sp.loadStats.started : null,
              current: sp.current, decoded: sp.loaded.size, inFlight: sp.inFlight.size });
  };
  requestAnimationFrame(loop);
})` });
console.log('scroll loop with film:', JSON.stringify(s.result.value));
ws.close(); chrome.kill(); process.exit(0);
