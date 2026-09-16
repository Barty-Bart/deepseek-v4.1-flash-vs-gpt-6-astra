/**
 * Capture a few small JPEG views for visual inspection.
 * Keeps every artefact under the inspection budget: <=1280px on the long edge.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9360;
const job = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const base = job.url || 'http://127.0.0.1:5178/';
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  '--force-color-profile=srgb', `--remote-debugging-port=${PORT}`,'--no-first-run',
  '--user-data-dir=build/chrome-look','about:blank'], { stdio: 'ignore' });
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
mkdirSync('build/look', { recursive: true });

for (const v of job.views) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: v.width, height: v.height, deviceScaleFactor: 1, mobile: Boolean(v.mobile),
    screenWidth: v.width, screenHeight: v.height, positionX: 0, positionY: 0,
  });
  if (v.reduced) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  else await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });
  await send('Page.enable');
  await send('Page.navigate', { url: base });
  await sleep(v.settle || 4200);
  for (const y of v.scrolls) {
    if (v.selectorScroll) {
      const spots = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
        const at = (sel, off) => { const n = document.querySelector(sel);
          return n ? Math.round(n.getBoundingClientRect().top + window.scrollY + (off || 0)) : null; };
        return { stats: at('.stats', -120), trade: at('.trade-panel', -160),
                 tradeSteps: at('.trade-steps', -100) };
      })()` });
      const targets = spots.result.value;
      console.log('section offsets:', JSON.stringify(targets));
      for (const key of Object.keys(targets)) {
        if (targets[key] == null) continue;
        await send('Runtime.evaluate', { expression: `window.scrollTo({top:${targets[key]}, behavior:'instant'})` });
        await sleep(800);
        const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 68 });
        writeFileSync(`build/look/spot-${v.name}-${key}.jpg`, Buffer.from(shot.data, 'base64'));
        console.log('wrote spot-' + v.name + '-' + key + '.jpg');
      }
      continue;
    }
    await send('Runtime.evaluate', { expression: `window.scrollTo({top:${y}, behavior:'instant'})` });
    await sleep(700);
    if (v.hover) {
      await send('Runtime.evaluate', { expression: `document.querySelector('${v.hover}') && document.querySelector('${v.hover}').dispatchEvent(new MouseEvent('mouseover', {bubbles:true}))` });
      await send('Runtime.evaluate', { expression: `(() => { const n = document.querySelector('${v.hover}');
        if (n) { n.classList.add('is-hovered'); } })()` });
      await sleep(600);
    }
    const name = `${v.name}-${y}`;
    const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 68, captureBeyondViewport: false });
    writeFileSync(`build/look/${name}.jpg`, Buffer.from(shot.data, 'base64'));
    console.log('wrote', name + '.jpg');
  }
}
ws.close(); chrome.kill(); process.exit(0);
