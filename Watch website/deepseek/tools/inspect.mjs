/**
 * Headless inspection harness.
 *
 * Drives Chrome over the DevTools protocol so we can capture specific scroll
 * offsets, collect console errors and probe the DOM for measured checks.
 *
 *   node tools/inspect.mjs tools/views.json
 */
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333;
const OUT = 'build/shots';

const jobFile = process.argv[2] || 'tools/views.json';
const job = JSON.parse((await import('node:fs')).readFileSync(jobFile, 'utf8'));

mkdirSync(OUT, { recursive: true });

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars',
  '--force-color-profile=srgb', `--remote-debugging-port=${PORT}`,
  '--no-first-run', '--no-default-browser-check',
  '--user-data-dir=build/chrome-profile', 'about:blank',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function endpoint() {
  for (let i = 0; i < 80; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const list = await res.json();
      const page = list.find((t) => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch {}
    await sleep(250);
  }
  throw new Error('chrome did not expose a page target');
}

const wsUrl = await endpoint();
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => {
  ws.onopen = res;
  ws.onerror = rej;
});

let id = 0;
const pending = new Map();
const events = [];
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(new Error(msg.error.message));
    else resolve(msg.result);
  } else if (msg.method) {
    events.push(msg);
  }
};

function send(method, params = {}) {
  id += 1;
  const msgId = id;
  return new Promise((resolve, reject) => {
    pending.set(msgId, { resolve, reject });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
}

await send('Page.enable');
await send('Runtime.enable');
await send('Log.enable');
await send('Network.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

const consoleErrors = [];
const failedRequests = [];
await send('Runtime.addBinding', { name: '__inspect' }).catch(() => {});

const results = [];

for (const view of job.views) {
  const mobile = Boolean(view.mobile);
  // a real mobile viewport: without screenOrientation + screenWidth the meta
  // viewport is not honoured and everything renders oversized
  await send('Emulation.setDeviceMetricsOverride', {
    width: view.width,
    height: view.height,
    deviceScaleFactor: view.dpr || 1,
    mobile,
    screenWidth: view.width,
    screenHeight: view.height,
    positionX: 0,
    positionY: 0,
    screenOrientation: view.width > view.height
      ? { type: 'landscapePrimary', angle: 90 }
      : { type: 'portraitPrimary', angle: 0 },
  });
  await send('Emulation.setTouchEmulationEnabled', mobile
    ? { enabled: true, maxTouchPoints: 5 }
    : { enabled: false });
  if (view.reduced) {
    await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  } else {
    await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }] });
  }

  await send('Page.navigate', { url: `http://127.0.0.1:5179/${view.query || ''}` });
  await sleep(view.settle ?? 3500);

  for (const scroll of view.scrolls || [0]) {
    await send('Runtime.evaluate', {
      expression: `window.scrollTo({top:${scroll}, behavior:'auto'}); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`,
      awaitPromise: true,
    });
    // wait for the stage to have painted the frame that belongs to this offset,
    // otherwise the screenshot catches the previous frame still on the canvas
    await send('Runtime.evaluate', {
      expression: `new Promise((resolve) => {
        const t0 = performance.now();
        const tick = () => {
          const sp = window.__stage;
          const done = !sp || sp.isSettled();
          if (done || performance.now() - t0 > 4000) {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
            return;
          }
          setTimeout(tick, 40);
        };
        tick();
      })`,
      awaitPromise: true,
    });
    await sleep(view.pause ?? 500);
    // Headless compositing can hand back the previous canvas texture, so nudge
    // the scroll and let two more frames composite before capturing.
    await send('Runtime.evaluate', {
      expression: `new Promise((resolve) => {
        const y = window.scrollY;
        window.scrollBy(0, 1);
        requestAnimationFrame(() => {
          window.scrollTo({ top: y, behavior: 'auto' });
          requestAnimationFrame(() => requestAnimationFrame(resolve));
        });
      })`,
      awaitPromise: true,
    });
    await sleep(260);
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    writeFileSync(`${OUT}/${view.name}-${scroll}.png`, Buffer.from(shot.data, 'base64'));

    // ground truth for the stage: the canvas pixels themselves
    if (view.canvasDump) {
      const dump = await send('Runtime.evaluate', {
        expression: `(() => { const c = document.querySelector('[data-stage-canvas]');
          return c ? c.toDataURL('image/png') : ''; })()`,
        returnByValue: true,
      });
      const url = dump.result && dump.result.value;
      if (url && url.startsWith('data:image/png;base64,')) {
        writeFileSync(`${OUT}/${view.name}-${scroll}-canvas.png`,
          Buffer.from(url.split(',')[1], 'base64'));
      }
    }

    // the probe is authored as a function expression; wrap and invoke it
    const probeSrc = view.probe || '() => ({})';
    const probe = await send('Runtime.evaluate', {
      expression: `(${probeSrc})()`,
      returnByValue: true,
      awaitPromise: false,
    });
    if (probe.exceptionDetails) {
      const ex = probe.exceptionDetails;
      results.push({
        view: view.name, scroll, probe: null,
        probeError: ex.text,
        probeDetail: (ex.exception && (ex.exception.description || ex.exception.value)) || ex.exceptionDetails,
      });
      continue;
    }
    results.push({ view: view.name, scroll, probe: probe.result?.value ?? null });
  }
}

const logs = events
  .filter((e) => e.method === 'Log.entryAdded')
  .map((e) => `${e.params.entry.level}: ${e.params.entry.text}`);

const exceptions = events
  .filter((e) => e.method === 'Runtime.exceptionThrown')
  .map((e) => e.params.exceptionDetails?.exception?.description || e.params.exceptionDetails?.text);

const netFails = events
  .filter((e) => e.method === 'Network.loadingFailed')
  .map((e) => `${e.params.errorText} (${e.params.type})`);

const probeErrors = results.filter((r) => r.probeError).map((r) => `${r.view}@${r.scroll}: ${r.probeError}`);
writeFileSync('build/inspect-report.json', JSON.stringify({ results, logs, exceptions, netFails, probeErrors }, null, 2));
if (probeErrors.length) console.log('PROBE ERRORS:', [...new Set(probeErrors)].slice(0, 3).join('\n'));
console.log('views captured:', job.views.length, 'shots:', results.length);
if (logs.length) console.log('LOG:', [...new Set(logs)].slice(0, 20).join('\n'));
if (exceptions.length) console.log('EXCEPTIONS:', [...new Set(exceptions)].slice(0, 10).join('\n'));
if (netFails.length) console.log('NET FAILS:', [...new Set(netFails)].slice(0, 10).join('\n'));
console.log('report: build/inspect-report.json');

ws.close();
chrome.kill();
process.exit(0);
