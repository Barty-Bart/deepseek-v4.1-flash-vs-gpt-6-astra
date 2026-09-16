/**
 * Functional pass over the demo interactions: bag maths, product panel,
 * mobile menu, trade-in validation and reduced-motion presentation.
 */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9362;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-ia','about:blank'], { stdio: 'ignore' });
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

const evalJs = async (expr, awaitPromise = false) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise });
  if (r.exceptionDetails) return { __error: r.exceptionDetails.exception?.description || r.exceptionDetails.text };
  return r.result.value;
};

const out = {};

/* ---------- desktop: bag + product panel ---------- */
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1,
  mobile: false, screenWidth: 1440, screenHeight: 900, positionX: 0, positionY: 0 });
await send('Page.enable');
await send('Page.navigate', { url: 'http://127.0.0.1:5179/' });
await sleep(4500);

out.cardsRendered = await evalJs("document.querySelectorAll('.product-card').length");
out.cardMediaConsistent = await evalJs(`(() => {
  const boxes = [...document.querySelectorAll('.card-media')].map((n) => {
    const r = n.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height);
  });
  return { boxes, uniform: new Set(boxes).size === 1 };
})()`);
out.imgRatios = await evalJs(`[...document.querySelectorAll('.card-media img')].map((i) =>
  ({ nat: i.naturalWidth + 'x' + i.naturalHeight, fit: getComputedStyle(i).objectFit }))`);

// add each watch once via the grid buttons, then check the totals
await evalJs(`[...document.querySelectorAll('[data-quick-add]')].forEach((b) => b.click())`);
await sleep(500);
out.bagAfterAddAll = await evalJs(`({
  count: document.querySelector('[data-bag-count]').textContent,
  subtotal: document.querySelector('[data-total-subtotal]').textContent,
  total: document.querySelector('[data-total-grand]').textContent,
  lines: document.querySelectorAll('.bag-item').length,
  stored: localStorage.getItem('meridian.bag.v1')
})`);

// change a quantity
await evalJs(`document.querySelector('[data-bag-open]').click()`);
await sleep(400);
out.bagOpen = await evalJs(`!document.querySelector('[data-bag-modal]').hidden`);
await evalJs(`document.querySelector('[data-inc]').click()`);
await sleep(300);
out.afterInc = await evalJs(`({ subtotal: document.querySelector('[data-total-subtotal]').textContent,
  qty: document.querySelector('.bag-item-qty').textContent })`);
// remove one line
await evalJs(`document.querySelector('[data-remove]').click()`);
await sleep(300);
out.afterRemove = await evalJs(`({ subtotal: document.querySelector('[data-total-subtotal]').textContent,
  lines: document.querySelectorAll('.bag-item').length })`);
// demo summary then reset
await evalJs(`document.querySelector('[data-demo-checkout]').click()`);
await sleep(300);
out.demoSummary = await evalJs(`({ shown: !document.querySelector('[data-demo-summary]').hidden,
  text: document.querySelector('[data-demo-summary]').textContent.replace(/\\s+/g,' ').trim().slice(0,120) })`);
await evalJs(`document.querySelector('[data-demo-close]').click(); document.querySelector('[data-bag-reset]').click()`);
await sleep(400);
out.afterReset = await evalJs(`({ count: document.querySelector('[data-bag-count]').textContent,
  emptyShown: !document.querySelector('[data-bag-empty]').hidden,
  stored: localStorage.getItem('meridian.bag.v1') })`);
await evalJs(`document.querySelector('[data-bag-dismiss]').click()`);

/* ---------- product panel ---------- */
await evalJs(`document.querySelector('[data-open-product]').click()`);
await sleep(500);
out.panelOpened = await evalJs(`({ open: !document.querySelector('[data-product-modal]').hidden,
  title: document.querySelector('[data-pm-title]').textContent,
  price: document.querySelector('[data-pm-price]').textContent,
  variants: document.querySelectorAll('[data-variant]').length,
  specs: document.querySelectorAll('[data-pm-specs] div').length })`);
await evalJs(`document.querySelectorAll('[data-variant]').length > 2 && document.querySelectorAll('[data-variant]')[2].click()`);
await sleep(300);
out.variantSwitch = await evalJs(`({ title: document.querySelector('[data-pm-title]').textContent,
  pressed: [...document.querySelectorAll('[data-variant]')].filter((b) => b.getAttribute('aria-pressed') === 'true').length,
  image: document.querySelector('[data-pm-image]').getAttribute('src') })`);

/* ---------- trade-in validation ---------- */
await evalJs(`document.querySelector('[data-product-modal] .modal-close').click()`);
await evalJs(`document.querySelector('[data-trade-form]').dispatchEvent(new Event('submit', {cancelable:true, bubbles:true}))`);
await sleep(300);
out.formEmptySubmit = await evalJs(`({
  errors: [...document.querySelectorAll('.field-error')].filter((e) => !e.hidden).map((e) => e.textContent),
  focused: document.activeElement && document.activeElement.name,
  resultHidden: document.querySelector('[data-trade-result]').hidden
})`);
await evalJs(`(() => {
  const f = document.querySelector('[data-trade-form]');
  f.brand.value = 'Grand Seiko'; f.model.value = 'SBGW231';
  f.condition.value = 'Excellent';
  f.querySelector('button[type=submit]').click();
})()`);
await sleep(400);
out.formValidSubmit = await evalJs(`({
  shown: !document.querySelector('[data-trade-result]').hidden,
  message: document.querySelector('.form-result-title').textContent,
  rows: [...document.querySelectorAll('[data-trade-summary] div')].map((d) => d.textContent.trim())
})`);

console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill(); process.exit(0);
