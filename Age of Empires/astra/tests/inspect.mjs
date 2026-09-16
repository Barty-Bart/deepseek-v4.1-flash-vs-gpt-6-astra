import { chromium } from "@playwright/test";
import { writeFile, mkdir } from "node:fs/promises";
await mkdir("artifacts/v1.1", { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
});
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://localhost:5173");
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(500);
await page.screenshot({ path: "artifacts/v1.1/welcome.png" });
await page.getByRole("button", { name: "Found your settlement" }).click();
await page.waitForTimeout(400);
await page.screenshot({ path: "artifacts/v1.1/settlement.png" });
const performance = await page.evaluate(async () => {
  const { game, renderer } = window.__hearth;
  for (let i = 0; i < 24; i++) {
    const p = game.nearestOpen(17 + (i % 6), 29 + Math.floor(i / 6));
    game.addUnit("soldier", "player", p.x + 0.5, p.y + 0.5);
  }
  game.units
    .filter((u) => u.team === "player" && u.type === "villager")
    .forEach((u, i) => game.assignGather(u, ["food", "wood", "gold"][i]));
  const render = [],
    frames = [];
  const original = renderer.draw.bind(renderer);
  renderer.draw = (...args) => {
    const start = performance.now();
    original(...args);
    render.push(performance.now() - start);
  };
  await new Promise((resolve) => {
    let start, last;
    function sample(t) {
      if (!start) start = t;
      if (last) frames.push(t - last);
      last = t;
      if (t - start < 5000) requestAnimationFrame(sample);
      else resolve();
    }
    requestAnimationFrame(sample);
  });
  const sorted = render.slice().sort((a, b) => a - b);
  return {
    viewport: [innerWidth, innerHeight],
    devicePixelRatio,
    units: game.units.length,
    sampleSeconds: frames.reduce((a, b) => a + b, 0) / 1000,
    frames: frames.length,
    meanFPS: 1000 / (frames.reduce((a, b) => a + b, 0) / frames.length),
    renderMeanMs: render.reduce((a, b) => a + b, 0) / render.length,
    renderP95Ms: sorted[Math.floor(sorted.length * 0.95)],
  };
});
await page.setViewportSize({ width: 390, height: 844 });
await page.keyboard.press("h");
await page.keyboard.press(".");
await page.screenshot({ path: "artifacts/v1.1/mobile-layout.png" });
const mobile = await page
  .locator(".topbar,.bottom-ui,.selection-panel")
  .evaluateAll((els) =>
    els.map((e) => ({
      selector: e.className,
      x: e.getBoundingClientRect().x,
      right: e.getBoundingClientRect().right,
    })),
  );
await writeFile(
  "artifacts/v1.1/inspection.json",
  JSON.stringify(
    { browser: await browser.version(), errors, performance, mobile },
    null,
    2,
  ),
);
console.log(JSON.stringify({ errors, performance, mobile }, null, 2));
await browser.close();
