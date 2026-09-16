import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { timeline } from "../src/sequence.js";
const manifest = JSON.parse(readFileSync("public/media/manifest.json", "utf8"));

for (const [width, height] of [
  [1440, 900],
  [1024, 768],
  [768, 1024],
  [390, 844],
  [360, 800],
]) {
  test(`actual film forward, reverse and framing ${width}x${height}`, async ({
    page,
  }) => {
    test.skip(
      !["accepted", "preview"].includes(manifest.status),
      "Actual films are not integrated.",
    );
    const portrait = width <= 700 || (width <= 1000 && height > width);
    const name = portrait ? "portrait" : "landscape",
      source = manifest[name];
    const requested = [],
      failures = [];
    page.on("request", (r) => {
      if (/\/frame-\d+\.webp/.test(r.url())) requested.push(r.url());
    });
    page.on("response", (r) => {
      if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`);
    });
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await page.evaluate(() => document.fonts.ready);
    const canvas = page.locator(".film-canvas");
    await expect(canvas).toHaveAttribute("data-frame", "0");
    const first = await canvas.evaluate((el) => el.toDataURL());
    for (const progress of [0, 0.36, 0.62, 0.84, 0.99, 0.48, 0]) {
      await page.evaluate((p) => {
        const intro = document.querySelector("#intro");
        scrollTo({
          top: (intro.offsetHeight - innerHeight) * p,
          behavior: "instant",
        });
      }, progress);
      const expected = Math.round(
        timeline(progress, portrait, source.timeline).frameProgress *
          (source.frameCount - 1),
      );
      await expect
        .poll(async () =>
          Math.abs(Number(await canvas.getAttribute("data-frame")) - expected),
        )
        .toBeLessThanOrEqual(1);
      await expect(canvas).toHaveClass(/visible/);
      if ([0, 0.36, 0.62, 0.99].includes(progress)) {
        await page.screenshot({
          path: `artifacts/media-qa/film-${width}-${progress}.png`,
        });
      }
    }
    expect(await canvas.evaluate((el) => el.toDataURL())).toBe(first);
    expect(requested.every((url) => url.includes(`/media/${name}-`))).toBe(
      true,
    );
    expect(failures).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
