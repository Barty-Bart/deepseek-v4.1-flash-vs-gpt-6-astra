/** Mobile navigation, focus management, anchor offsets and reduced motion. */
import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9363;
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,'--no-first-run','--user-data-dir=build/chrome-ma','about:blank'], { stdio: 'ignore' });
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
const js = async (expr, awaitPromise = false) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise });
  if (r.exceptionDetails) return { __error: r.exceptionDetails.exception?.description };
  return r.result.value;
};

const out = {};

/* ---------- mobile menu at 390 ---------- */
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2,
  mobile: true, screenWidth: 390, screenHeight: 844, positionX: 0, positionY: 0 });
await send('Page.enable');
await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
await sleep(4500);

out.tapTargets = await js(`(() => {
  const small = [];
  for (const el of document.querySelectorAll('button, a[href], select, input')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (el.closest('[hidden]')) continue;
    if (r.height < 44 && !el.classList.contains('skip-story') && !el.classList.contains('footer-nav')) {
      small.push((el.className || el.tagName) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
    }
  }
  return small.slice(0, 8);
})()`);

out.menuClosedInitially = await js(`document.querySelector('[data-mobile-menu]').hidden`);
await js(`document.querySelector('[data-menu-toggle]').click()`);
await sleep(400);
out.menuOpen = await js(`({ hidden: document.querySelector('[data-mobile-menu]').hidden,
  expanded: document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded'),
  bodyLocked: document.body.classList.contains('is-locked'),
  focusInMenu: document.querySelector('[data-mobile-menu]').contains(document.activeElement),
  linkCount: document.querySelectorAll('[data-mobile-menu] a').length,
  labels: [...document.querySelectorAll('[data-mobile-menu] a')].map((a) => a.textContent) })`);

// Escape closes and returns focus to the toggle
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await sleep(400);
out.afterEscape = await js(`({ hidden: document.querySelector('[data-mobile-menu]').hidden,
  expanded: document.querySelector('[data-menu-toggle]').getAttribute('aria-expanded'),
  focusOnToggle: document.activeElement === document.querySelector('[data-menu-toggle]'),
  bodyLocked: document.body.classList.contains('is-locked') })`);

// navigating from the menu closes it and lands with the header offset respected
await js(`document.querySelector('[data-menu-toggle]').click()`);
await sleep(300);
await js(`[...document.querySelectorAll('[data-mobile-menu] a')].find((a) => a.getAttribute('href') === '#craft').click()`);
await sleep(1400);
out.afterMenuNavigate = await js(`(() => {
  const target = document.querySelector('#craft');
  const header = document.querySelector('[data-header]');
  const pad = parseInt(getComputedStyle(document.documentElement).scrollPaddingTop || '0', 10);
  return {
    menuHidden: document.querySelector('[data-mobile-menu]').hidden,
    bodyLocked: document.body.classList.contains('is-locked'),
    hash: location.hash,
    targetTopMinusHeader: Math.round(target.getBoundingClientRect().top - header.getBoundingClientRect().height),
    scrollPaddingTop: pad,
    scrollY: Math.round(window.scrollY)
  };
})()`);

// bag drawer focus trap and escape
await js(`document.querySelector('[data-bag-open]').click()`);
await sleep(400);
out.bagFocus = await js(`({ open: !document.querySelector('[data-bag-modal]').hidden,
  focusInside: document.querySelector('[data-bag-modal]').contains(document.activeElement) })`);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await sleep(400);
out.bagClosedByEscape = await js(`document.querySelector('[data-bag-modal]').hidden`);

/* ---------- reduced motion ---------- */
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1,
  mobile: false, screenWidth: 1440, screenHeight: 900, positionX: 0, positionY: 0 });
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
await send('Page.navigate', { url: 'http://127.0.0.1:5178/' });
await sleep(4000);
out.reducedMotion = await js(`(() => ({
  canvasDisplay: getComputedStyle(document.querySelector('[data-stage-canvas]')).display,
  trackHeight: Math.round(document.querySelector('[data-stage-track]').getBoundingClientRect().height),
  windowHeight: window.innerHeight,
  posterVisible: !document.querySelector('[data-stage-poster]').classList.contains('is-hidden'),
  activeBeats: [...document.querySelectorAll('.beat.is-active')].map((b) => b.dataset.beat),
  allBeatTextVisible: [...document.querySelectorAll('.beat')].every((b) => b.getBoundingClientRect().height > 0),
  headline: document.querySelector('.beat.is-active .beat-title') ? document.querySelector('.beat.is-active .beat-title').textContent : null
}))()`);
await js(`window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'})`);
await sleep(600);
out.reducedSectionFlow = await js(`({
  scrolledToBottom: Math.round(window.scrollY) > 1000,
  footerVisible: document.querySelector('.site-footer').getBoundingClientRect().top < window.innerHeight
})`);

console.log(JSON.stringify(out, null, 1));
ws.close(); chrome.kill(); process.exit(0);
