/**
 * Verifies this revision's fixes:
 *  - the film advances continuously with no flat or jumped segments
 *  - hovering a product card swaps to its wrist image
 *  - the stats row and trade panel are centred
 */
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync, readFileSync } from 'node:fs';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9370;
const base = (JSON.parse(readFileSync(process.argv[2] || 'tools/verify-pass2.json','utf8')).url) || 'http://127.0.0.1:5179/';
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars','--force-color-profile=srgb',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-v2','about:blank'], { stdio: 'ignore' });
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
const js = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  if (r.exceptionDetails) return { __error: r.exceptionDetails.exception?.description };
  return r.result.value;
};

mkdirSync('build/look', { recursive: true });
const out = {};
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1,
  mobile: false, screenWidth: 1440, screenHeight: 900, positionX: 0, positionY: 0 });
await send('Page.enable'); await send('DOM.enable'); await send('CSS.enable');
await send('Page.navigate', { url: base });
await sleep(5000);

/* ---- 1. continuous film mapping ---- */
out.film = await js(`(() => {
  const sp = window.__stage;
  const track = document.querySelector('[data-stage-track]');
  const travel = track.getBoundingClientRect().height - window.innerHeight;
  const seen = [];
  // walk the whole stage and record the frame at each step
  for (let i = 0; i <= 240; i += 1) {
    const y = (i / 240) * travel;
    window.scrollTo({ top: y, behavior: 'instant' });
    const p = Math.max(0, Math.min(1, -track.getBoundingClientRect().top / travel));
    seen.push(sp.mappingFor(p).frame);
  }
  const steps = [];
  for (let i = 1; i < seen.length; i += 1) steps.push(seen[i] - seen[i - 1]);
  const stalled = steps.filter((d) => d === 0).length;
  const jumped = steps.filter((d) => d > 3).length;
  return {
    samples: seen.length,
    firstFrame: Math.round(seen[0]), lastFrame: Math.round(seen[seen.length - 1]),
    totalFrames: sp.frames.length,
    stalledSteps: stalled,
    jumpedSteps: jumped,
    minStep: Math.min(...steps), maxStep: Math.max(...steps),
    medianStep: steps.slice().sort((a, b) => a - b)[Math.floor(steps.length / 2)],
    clipFrames: sp.entry.clips
  };
})()`);

/* ---- 2. hover swap on every card ---- */
await js(`document.querySelector('#collection').scrollIntoView({behavior:'instant'})`);
await sleep(900);
const hoverResults = [];
const cardCount = await js(`document.querySelectorAll('.card-media').length`);
for (let i = 0; i < cardCount; i += 1) {
  const doc = await send('DOM.getDocument');
  const nodeRes = await send('DOM.querySelector', { nodeId: doc.root.nodeId,
    selector: `.product-card:nth-child(${i + 1}) .card-media` });
  if (!nodeRes.nodeId) continue;
  await send('CSS.forcePseudoState', { nodeId: nodeRes.nodeId, forcedPseudoClasses: ['hover'] });
  await sleep(700);
  const state = await js(`(() => {
    const card = document.querySelector('.product-card:nth-child(${i + 1})');
    const wrist = card.querySelector('.card-wrist');
    const still = card.querySelector('.card-still');
    return {
      name: card.querySelector('.card-name').textContent,
      wristOpacity: +getComputedStyle(wrist).opacity,
      stillOpacity: +getComputedStyle(still).opacity,
      wristSrc: wrist.getAttribute('src'),
      wristLoaded: wrist.naturalWidth > 0,
      wristSize: wrist.naturalWidth + 'x' + wrist.naturalHeight
    };
  })()`);
  hoverResults.push(state);
  await send('CSS.forcePseudoState', { nodeId: nodeRes.nodeId, forcedPseudoClasses: [] });
  if (i === 2) {
    await send('CSS.forcePseudoState', { nodeId: nodeRes.nodeId, forcedPseudoClasses: ['hover'] });
    await sleep(500);
    const shot = await send('Page.captureScreenshot', { format: 'jpeg', quality: 70 });
    writeFileSync('build/look/hover-forest.jpg', Buffer.from(shot.data, 'base64'));
    await send('CSS.forcePseudoState', { nodeId: nodeRes.nodeId, forcedPseudoClasses: [] });
  }
}
out.hover = hoverResults;

/* ---- 3. layout centring ---- */
await js(`document.querySelector('#story').scrollIntoView({behavior:'instant'})`);
await sleep(500);
out.statsLayout = await js(`(() => {
  const section = document.querySelector('#story');
  const list = document.querySelector('.stats-list');
  const cells = [...document.querySelectorAll('.stats-list div')].map((d) => {
    const r = d.getBoundingClientRect();
    return { left: Math.round(r.left), width: Math.round(r.width),
             centre: Math.round(r.left + r.width / 2) };
  });
  const sr = section.getBoundingClientRect();
  const sectionCentre = Math.round(sr.left + sr.width / 2);
  const listRect = list.getBoundingClientRect();
  return {
    sectionCentre,
    listCentre: Math.round(listRect.left + listRect.width / 2),
    cells,
    equalWidths: new Set(cells.map((c) => c.width)).size === 1,
    centresSpread: Math.round(Math.max(...cells.map((c) => c.centre)) - Math.min(...cells.map((c) => c.centre))),
    noteCentred: (() => {
      const n = document.querySelector('.concept-note').getBoundingClientRect();
      return Math.round(n.left + n.width / 2);
    })()
  };
})()`);

await js(`document.querySelector('#trade-in').scrollIntoView({behavior:'instant'})`);
await sleep(500);
out.tradeLayout = await js(`(() => {
  const section = document.querySelector('#trade-in');
  const panel = document.querySelector('.trade-panel');
  const sr = section.getBoundingClientRect();
  const pr = panel.getBoundingClientRect();
  const actions = document.querySelector('.form-actions').getBoundingClientRect();
  const input = document.querySelector('#trade-brand').getBoundingClientRect();
  return {
    sectionCentre: Math.round(sr.left + sr.width / 2),
    panelCentre: Math.round(pr.left + pr.width / 2),
    panelWidth: Math.round(pr.width),
    actionsCentre: Math.round(actions.left + actions.width / 2),
    fieldWidth: Math.round(input.width),
    panelInnerCentre: Math.round(pr.left + pr.width / 2)
  };
})()`);

console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill(); process.exit(0);
