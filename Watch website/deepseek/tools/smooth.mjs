/**
 * Bounded smoothness check. Scrolls the pinned stage once over a fixed duration
 * and reports frame pacing plus how often the wanted frame was actually painted.
 */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9355;
const target = JSON.parse(process.argv[2] || '{"width":1440,"height":900,"durationMs":8000}');
const base = target.url || 'http://127.0.0.1:5178/';
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-sm','about:blank'],
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
  width: target.width, height: target.height, deviceScaleFactor: 1, mobile: Boolean(target.mobile),
  screenWidth: target.width, screenHeight: target.height, positionX: 0, positionY: 0,
});
await send('Page.enable');
await send('Page.navigate', { url: base });
await sleep(6500);

const r = await send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression:
`new Promise((resolve) => {
  const sp = window.__stage;
  const track = document.querySelector('[data-stage-track]');
  const travel = Math.max(1, track.getBoundingClientRect().height - window.innerHeight);
  const durationMs = ${target.durationMs};
  window.scrollTo({ top: 0, behavior: 'instant' });
  let rafs = 0, drew = 0, wanted = 0, haveWanted = 0;
  const gaps = [], traces = [];
  const realBlit = sp.blit.bind(sp);
  sp.blit = (b) => { drew += 1; return realBlit(b); };
  const t0 = performance.now();
  let last = t0;
  const loop = () => {
    rafs += 1;
    const now = performance.now();
    gaps.push(now - last); last = now;
    const t = Math.min(1, (now - t0) / durationMs);
    window.scrollTo({ top: t * travel, behavior: 'instant' });
    wanted += 1;
    if (sp.loaded.has(sp.current)) haveWanted += 1;
    if (traces.length < 40) traces.push([sp.current, sp.drawnBitmapIndex]);
    if (t < 1) { requestAnimationFrame(loop); return; }
    gaps.sort((a, b) => a - b);
    resolve({
      variant: sp.variantKey, frames: sp.frames.length, rafs, drew,
      wantedChecks: wanted, wantedPresent: haveWanted,
      completeness: +(haveWanted / Math.max(1, wanted)).toFixed(3),
      longFrameCount: gaps.filter((g) => g > 34).length,
      p95GapMs: Math.round(gaps[Math.floor(gaps.length * 0.95)] || 0),
      maxGapMs: Math.round(gaps[gaps.length - 1] || 0),
      wallMs: Math.round(performance.now() - t0),
      decoded: sp.loaded.size, inFlight: sp.inFlight.size,
      loadStats: sp.loadStats ? {
        started: sp.loadStats.started,
        meanNetMs: +(sp.loadStats.netMs / Math.max(1, sp.loadStats.started)).toFixed(1),
        meanDecodeMs: +(sp.loadStats.decodeMs / Math.max(1, sp.loadStats.started)).toFixed(1),
        failed: sp.loadStats.failed,
      } : null
    });
  };
  requestAnimationFrame(loop);
})` });
if (r.exceptionDetails) console.log('EXC', r.exceptionDetails.text, r.exceptionDetails.exception && r.exceptionDetails.exception.description);
console.log(JSON.stringify(r.result && r.result.value ? r.result.value : { empty: true, details: r.exceptionDetails ? r.exceptionDetails.text : null }, null, 1));
ws.close(); chrome.kill(); process.exit(0);
