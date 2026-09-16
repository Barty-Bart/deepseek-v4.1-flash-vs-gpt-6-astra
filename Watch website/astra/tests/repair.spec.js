import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { timeline, storyDistances } from "../src/sequence.js";

const manifest = JSON.parse(readFileSync("public/media/manifest.json", "utf8"));
const progressAt = (frame, mobile, source) => {
  let low = 0,
    high = 1;
  for (let n = 0; n < 40; n++) {
    const mid = (low + high) / 2;
    if (
      timeline(mid, mobile, source.timeline).frameProgress *
        (source.frameCount - 1) <
      frame
    )
      low = mid;
    else high = mid;
  }
  return (low + high) / 2;
};

for (const [width, height, aspect] of [
  [1440, 900, "landscape"],
  [390, 844, "portrait"],
]) {
  test(`small wheel steps cross shortened transitions ${aspect}`, async ({
    page,
  }) => {
    const mobile = aspect === "portrait",
      source = manifest[aspect];
    const edit = JSON.parse(readFileSync(source.timingEdit.sidecar, "utf8"));
    await page.setViewportSize({ width, height });
    await page.goto("/");
    const canvas = page.locator(".film-canvas");
    await expect(canvas).toHaveAttribute("data-frame", "0");
    for (const interval of edit.intervals) {
      const first = edit.sourceFrameIndices.indexOf(interval.first);
      const last = edit.sourceFrameIndices.indexOf(interval.last);
      const start = progressAt(first, mobile, source),
        end = progressAt(last, mobile, source);
      // Neither reported pause may occupy even two ordinary 80px wheel steps.
      const span =
        (end - start) * storyDistances(mobile).reduce((a, b) => a + b) * height;
      expect(span).toBeLessThan(mobile ? 100 : 150);
      await page.evaluate((p) => {
        const intro = document.querySelector("#intro");
        scrollTo({
          top: p * (intro.offsetHeight - innerHeight),
          behavior: "instant",
        });
      }, start);
      await expect
        .poll(async () =>
          Math.abs(Number(await canvas.getAttribute("data-frame")) - first),
        )
        .toBeLessThanOrEqual(1);
      await page.mouse.move(width / 2, height / 2);
      let previous = Number(await canvas.getAttribute("data-frame"));
      for (let i = 0; i < 3; i++) {
        await page.mouse.wheel(0, 80);
        await expect
          .poll(async () => Number(await canvas.getAttribute("data-frame")))
          .toBeGreaterThan(previous);
        previous = Number(await canvas.getAttribute("data-frame"));
      }
      expect(previous).toBeGreaterThan(last);
      for (let i = 0; i < 3; i++) {
        await page.mouse.wheel(0, -80);
        await expect
          .poll(async () => Number(await canvas.getAttribute("data-frame")))
          .toBeLessThan(previous);
        previous = Number(await canvas.getAttribute("data-frame"));
      }
    }
  });
}

test("all five cards reveal distinct wrist images on hover and keyboard focus", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const cards = page.locator(".product-image");
  const sources = new Set();
  for (let i = 0; i < 5; i++) {
    const card = cards.nth(i),
      secondary = card.locator(".product-image-secondary");
    await card.scrollIntoViewIfNeeded();
    await page.mouse.move(0, 0);
    await expect(card).toHaveClass(/supplement-ready/);
    await expect(secondary).toHaveCSS("opacity", "0");
    expect(await secondary.evaluate((el) => el.naturalWidth)).toBeGreaterThan(
      0,
    );
    sources.add(await secondary.getAttribute("src"));
    await card.hover();
    await expect(secondary).toHaveCSS("opacity", "1");
    await card.screenshot({ path: `artifacts/repair-v3/hover-card-${i}.png` });
    await page.mouse.move(0, 0);
    await expect(secondary).toHaveCSS("opacity", "0");
    await page.keyboard.press("Tab");
    await card.focus();
    await expect(secondary).toHaveCSS("opacity", "1");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(card).toBeFocused();
    await card.evaluate((el) => el.blur());
  }
  expect(sources.size).toBe(5);
});

test("slow and failed supplementary loads preserve the original photograph", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/product-*-wrist-v1.webp", async (route) => {
    await gate;
    await route.fulfill({ status: 404, body: "Unavailable" });
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  const card = page.locator(".product-image").first();
  await card.hover();
  const primary = card.locator(".product-image-primary");
  await expect(primary).not.toHaveJSProperty("naturalWidth", 0);
  await expect(card.locator(".product-image-secondary")).toHaveCSS(
    "opacity",
    "0",
  );
  release();
  await expect(card).not.toHaveClass(/supplement-ready/);
  await card.click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("reduced motion shows supplementary views without animation", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const card = page.locator(".product-image").first();
  await card.hover();
  await expect(card).toHaveClass(/supplement-ready/);
  await expect(card.locator(".product-image-secondary")).toHaveCSS(
    "opacity",
    "1",
  );
  await expect(card.locator(".product-image-secondary")).toHaveCSS(
    "transition-duration",
    "0s",
  );
});

test("touch cards keep the product photo and open details with one tap", async ({
  browser,
}) => {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
  });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:4174/");
  const card = page.locator(".product-image").first();
  await card.scrollIntoViewIfNeeded();
  await expect(card).toHaveClass(/supplement-ready/);
  await expect(card.locator(".product-image-secondary")).toHaveCSS(
    "opacity",
    "0",
  );
  await card.tap();
  await expect(page.getByRole("dialog")).toBeVisible();
  await context.close();
});
