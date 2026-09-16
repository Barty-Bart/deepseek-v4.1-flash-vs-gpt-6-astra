/** Draw-completeness at several scroll speeds, plus a reverse pass. */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9349;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-ss','about:blank'],
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
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', {
  width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
  screenWidth: 1440, screenHeight: 900, positionX: 0, positionY: 0,
});
await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
await sleep(5000);
await send('Runtime.evaluate', { expression: 'window.scrollTo(0,0)' });

async function pass(label, durationMs, reverse) {
  // make sure the stage exists before timing
  const ready = await send('Runtime.evaluate', { returnByValue: true,
    expression: "!!(window.__stage && document.querySelector('[data-stage-track]') && window.__stage.loaded.size > 0)" });
  if (!ready.result.value) { console.log('stage not ready for', label); }
  const r = await send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: `new Promise((resolve) => {
    const sp = window.__stage;
    const track = document.querySelector('[data-stage-track]');
    const travel = Math.max(1, track.getBoundingClientRect().height - window.innerHeight);
    const reverse = ISREVERSE;
    const durationMs = DURATIONMS;
    window.scrollTo({ top: reverse ? travel : 0, behavior: 'instant' });
    let rafs = 0, drew = 0, gaps = [];
    const realBlit = sp.blit.bind(sp);
    sp.blit = (b) => { drew += 1; return realBlit(b); };
    const t0 = performance.now();
    let last = t0;
    const loop = () => {
      rafs += 1;
      const e = performance.now() - t0;
      gaps.push(e - last); last = e;
      const t = Math.min(1, e / durationMs);
      window.scrollTo({ top: reverse ? (1 - t) * travel : t * travel, behavior: 'instant' });
      if (t < 1) { requestAnimationFrame(loop); return; }
      gaps.sort((a, b) => a - b);
      resolve({
        rafs, drew,
        wallMs: Math.round(performance.now() - t0),
        longFrames: gaps.filter((g) => g > 34).length,
        p95GapMs: Math.round(gaps[Math.floor(gaps.length * 0.95)] || 0),
        maxGapMs: Math.round(gaps[gaps.length - 1] || 0),
        current: sp.current, decoded: sp.loaded.size, inFlight: sp.inFlight.size
      });
    };
    requestAnimationFrame(loop);
  })`.replace('ISREVERSE', String(reverse)).replace('DURATIONMS', String(durationMs)) });
  if (r.exceptionDetails) console.log('eval error:', r.exceptionDetails.text, r.exceptionDetails.exception && r.exceptionDetails.exception.description);
  return { pass: label, ...(r.result.value || { error: 'no value' }) };
}

const out = [];
out.push(await pass('slow 300px/s', 19000, false));
out.push(await pass('normal 1000px/s', 5600, false));
out.push(await pass('fast 2500px/s', 2300, false));
out.push(await pass('reverse 1000px/s', 5600, true));
console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill(); process.exit(0);
