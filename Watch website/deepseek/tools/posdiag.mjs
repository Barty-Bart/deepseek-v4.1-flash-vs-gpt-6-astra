import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9350;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-pos','about:blank'],
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
await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
await sleep(5000);
const r = await send('Runtime.evaluate', { returnByValue: true, awaitPromise: true, expression: `(async () => {
  const sp = window.__stage;
  const track = document.querySelector('[data-stage-track]');
  const out = { docH: document.documentElement.scrollHeight, winH: window.innerHeight,
                trackH: Math.round(track.getBoundingClientRect().height) };
  out.maxScroll = out.docH - out.winH;
  out.travel = Math.round(out.trackH - out.winH);
  const samples = [];
  for (const y of [0, 1000, 2000, 3000, 4000, 5000]) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise((res) => requestAnimationFrame(() => requestAnimationFrame(res)));
    samples.push({ want: y, got: Math.round(window.scrollY), p: +sp.progress().toFixed(3),
                   current: sp.current, trackTop: Math.round(track.getBoundingClientRect().top) });
  }
  out.samples = samples;
  return out;
})()` });
console.log(JSON.stringify(r.result.value, null, 1));
ws.close(); chrome.kill(); process.exit(0);
