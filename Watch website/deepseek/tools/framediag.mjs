/** Trace which frame the timeline wants vs which bitmap is on the canvas, per rAF. */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9348;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-fd','about:blank'],
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
  const sp = window.__stage;
  const track = document.querySelector('[data-stage-track]');
  const travel = Math.max(1, track.getBoundingClientRect().height - window.innerHeight);
  const N = 300;
  const trace = [];
  let n = 0;
  const loop = () => {
    n += 1;
    window.scrollTo(0, (n / N) * travel);
    requestAnimationFrame(() => {
      trace.push([n, sp.current, sp.drawnBitmapIndex, sp.loaded.has(sp.current) ? 1 : 0, sp.inFlight.size]);
      if (n < N) { loop(); return; }
      const missing = trace.filter((t) => t[3] === 0).length;
      const drew = new Set(trace.map((t) => t[2])).size;
      resolve({ samples: trace.length, wantedFrameMissing: missing, distinctDrawn: drew,
                firstTen: trace.slice(0, 10), lastTen: trace.slice(-10),
                finalCurrent: sp.current, decoded: sp.loaded.size });
    });
  };
  requestAnimationFrame(loop);
})` });
console.log(JSON.stringify(r.result.value, null, 1));
ws.close(); chrome.kill(); process.exit(0);
