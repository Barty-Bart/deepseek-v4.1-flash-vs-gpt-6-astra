import { chromium } from "@playwright/test";
import sharp from "sharp";
import { mkdir } from "node:fs/promises";
await mkdir("public/assets/masters", { recursive: true });
const browser = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: [
    "--enable-webgl",
    "--use-gl=angle",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
  ],
});
const page = await browser.newPage();
for (const item of [
  ...["midnight", "ivory", "forest", "eclipse", "atelier"].map((variant) => ({
    variant,
    mode: "product",
    width: 900,
    height: 1100,
    name: variant,
  })),
  {
    variant: "midnight",
    mode: "hero",
    width: 1400,
    height: 1400,
    name: "hero-watch",
  },
  {
    variant: "midnight",
    mode: "portrait",
    width: 720,
    height: 1000,
    name: "portrait-watch",
  },
  {
    variant: "midnight",
    mode: "macro",
    width: 1400,
    height: 1300,
    name: "craft-macro",
  },
]) {
  await page.setViewportSize({ width: item.width, height: item.height });
  await page.goto(
    `http://127.0.0.1:5174/render.html?variant=${item.variant}&mode=${item.mode}`,
  );
  await page.waitForFunction(() => window.renderReady);
  const file = `public/assets/masters/${item.name}-v1.png`;
  await page.screenshot({ path: file, omitBackground: true });
  await sharp(file)
    .webp({ quality: 88 })
    .toFile(`public/assets/${item.name}-v1.webp`);
  console.log(`Rendered ${item.name}`);
}
await browser.close();
