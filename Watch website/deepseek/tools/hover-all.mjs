/** Force :hover on every card and capture one strip of all five hover states. */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync } from 'node:fs';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9375;
const base = JSON.parse(readFileSync(process.argv[2], 'utf8')).url;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars','--force-color-profile=srgb',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-ha','about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function endpoint() {
  for (let i = 0; i < 90; i += 1) {
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

await send('Emulation.setDeviceMetricsOverride', { width: 1500, height: 900, deviceScaleFactor: 1,
  mobile: false, screenWidth: 1500, screenHeight: 900, positionX: 0, positionY: 0 });
await send('Page.enable'); await send('DOM.enable'); await send('CSS.enable');
await send('Page.navigate', { url: base });
await sleep(5200);
const pos = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
  document.querySelector('#collection').scrollIntoView({behavior:'instant'});
  return true; })()` });
await sleep(1200);
const doc = await send('DOM.getDocument');
mkdirSync('build/look', { recursive: true });
for (let i = 1; i <= 5; i += 1) {
  const node = await send('DOM.querySelector', { nodeId: doc.root.nodeId, selector: `.product-card:nth-child(${i}) .card-media` });
  if (!node.nodeId) { console.log('card', i, 'not found'); continue; }
  await send('CSS.forcePseudoState', { nodeId: node.nodeId, forcedPseudoClasses: ['hover'] });
  await sleep(650);
  const state = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
    const c = document.querySelector('.product-card:nth-child(${i})');
    const w = c.querySelector('.card-wrist'); const s = c.querySelector('.card-still');
    const box = c.querySelector('.card-media').getBoundingClientRect();
    return { name: c.querySelector('.card-name').textContent,
      wristOpacity: +getComputedStyle(w).opacity, stillOpacity: +getComputedStyle(s).opacity,
      fit: getComputedStyle(w).objectFit, padding: getComputedStyle(w).paddingLeft,
      wristNat: w.naturalWidth + 'x' + w.naturalHeight,
      cardBox: Math.round(box.width) + 'x' + Math.round(box.height) }; })()` });
  console.log(JSON.stringify(state.result.value));
  const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 72 });
  writeFileSync(`build/look/hover-card-${i}.jpg`, Buffer.from(shot.data, 'base64'));
  await send('CSS.forcePseudoState', { nodeId: node.nodeId, forcedPseudoClasses: [] });
}
ws.close(); chrome.kill(); process.exit(0);
