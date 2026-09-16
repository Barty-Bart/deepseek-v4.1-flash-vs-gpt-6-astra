import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { timeline } from "../src/sequence.js";

for (const [width, height] of [
  [1440, 900],
  [1024, 768],
  [768, 1024],
  [390, 844],
  [360, 800],
]) {
  test(`responsive layout and navigation ${width}x${height}`, async ({
    page,
  }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Every part, a purpose." }),
    ).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator(".hero-art img")).toHaveJSProperty(
      "complete",
      true,
    );
    await expect(page.locator(".hero-art img")).not.toHaveJSProperty(
      "naturalWidth",
      0,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(await page.locator("#intro").getAttribute("data-source")).toBe(
      width <= 700 || (width <= 1000 && height > width)
        ? "portrait"
        : "landscape",
    );
    if (width <= 900) {
      await page.getByRole("button", { name: "Open navigation menu" }).click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page
        .getByRole("navigation", { name: "Mobile navigation" })
        .getByRole("button", { name: "Collection" })
        .click();
      await expect(page.getByRole("dialog")).not.toBeVisible();
    } else {
      await page
        .getByRole("navigation", { name: "Main navigation" })
        .getByRole("link", { name: "Collection", exact: true })
        .click();
    }
    await expect(page.locator("#collection")).toBeInViewport();
    for (const id of ["craft", "about", "trade-in"]) {
      await page.locator(`#${id}`).scrollIntoViewIfNeeded();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
    }
    await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
    await page.waitForTimeout(150);
    await page.screenshot({
      path: `artifacts/viewport-${width}x${height}.png`,
      fullPage: true,
    });
    expect(errors).toEqual([]);
  });
}

test("variant selection, totals, persistence, removal and demo checkout", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Explore M01 Midnight", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Select M01 Eclipse" }).click();
  await expect(
    dialog.getByRole("heading", { name: "M01 Eclipse" }),
  ).toBeVisible();
  await dialog
    .getByRole("button", { name: "Increase quantity", exact: true })
    .click();
  await dialog.getByRole("button", { name: "Add to demo bag" }).click();
  await expect(page.getByTestId("bag-total")).toHaveText("$1,890 USD");
  await page.getByRole("button", { name: "Close panel" }).click();
  await page
    .getByRole("button", { name: "Explore M02 Atelier", exact: true })
    .click();
  await page.getByRole("button", { name: "Add to demo bag" }).click();
  await expect(page.getByTestId("bag-total")).toHaveText("$2,685 USD");
  await page.reload();
  await page.getByRole("button", { name: "Open bag, 3 items" }).click();
  await expect(page.getByTestId("bag-total")).toHaveText("$2,685 USD");
  await page.getByRole("button", { name: "Decrease eclipse quantity" }).click();
  await expect(page.getByTestId("bag-total")).toHaveText("$1,740 USD");
  await page.getByRole("button", { name: "Remove Atelier" }).click();
  await expect(page.getByTestId("bag-total")).toHaveText("$945 USD");
  await page.getByRole("button", { name: "Preview demo checkout" }).click();
  await expect(
    page.getByText("No payment was taken. No order has been placed."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset demo bag" }).click();
  await expect(page.getByText("A little room for possibility.")).toBeVisible();
  expect(
    await page.evaluate(() =>
      JSON.parse(localStorage.getItem("meridian-bag-v1")),
    ),
  ).toEqual([]);
});

test("filters and keyboard modal behavior", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open navigation menu" });
  await menu.click();
  await expect(page.getByRole("button", { name: "Close panel" })).toBeFocused();
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press("Tab");
    expect(
      await page.evaluate(() => !!document.activeElement.closest("dialog")),
    ).toBe(true);
  }
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(menu).toBeFocused();
  await page
    .getByRole("group", { name: "Filter collection" })
    .getByRole("button", { name: "M02 Atelier", exact: true })
    .click();
  await expect(page.locator(".product-card")).toHaveCount(1);
  await expect(
    page.getByRole("button", { name: "Explore M02 Atelier", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "All watches", exact: true }).click();
  await expect(page.locator(".product-card")).toHaveCount(5);
});

test("trade form validation and actual local image preview", async ({
  page,
}) => {
  const writes = [];
  page.on("request", (r) => {
    if (r.method() !== "GET") writes.push(r.url());
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Prepare demo valuation" }).click();
  await expect(page.getByText("Enter the watch brand.")).toBeVisible();
  await expect(page.getByLabel("Watch brand")).toBeFocused();
  await page.getByLabel("Watch brand").fill("My Watch");
  await page.getByRole("textbox", { name: /^Model/ }).fill("Reference 123");
  await page.getByLabel("Condition", { exact: false }).selectOption("good");
  await page.locator("input[type=file]").setInputFiles({
    name: "watch.png",
    mimeType: "image/png",
    buffer: readFileSync("public/assets/masters/midnight-v1.png"),
  });
  await expect(
    page.getByRole("img", { name: "Your selected watch upload preview" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Prepare demo valuation" }).click();
  await expect(
    page.getByText("Demo valuation request prepared — nothing has been sent."),
  ).toBeVisible();
  expect(writes).toEqual([]);
  await page.getByRole("textbox", { name: /^Model/ }).fill("Changed");
  await expect(
    page.getByText("Demo valuation request prepared — nothing has been sent."),
  ).not.toBeVisible();
  await page.getByRole("button", { name: "Remove photo" }).click();
  await expect(
    page.getByRole("img", { name: "Your selected watch upload preview" }),
  ).not.toBeVisible();
  await page.locator("input[type=file]").setInputFiles({
    name: "bad.png",
    mimeType: "image/png",
    buffer: Buffer.from("not an image"),
  });
  await expect(
    page.getByText("That image could not be opened. Please choose another."),
  ).toBeVisible();
});

const fixtureSource = (name) => ({
  frameCount: 120,
  width: 160,
  height: 100,
  fps: 18,
  poster: "/assets/hero-watch-v1.webp",
  pattern: `/fixtures/${name}/frame-{frame}.webp`,
  startIndex: 1,
});
async function mockFilm(page, { fail = false, delay = 0 } = {}) {
  await page.route("**/media/manifest.json", (route) =>
    route.fulfill({
      json: {
        version: 1,
        status: "accepted",
        landscape: fixtureSource("landscape"),
        portrait: fixtureSource("portrait"),
      },
    }),
  );
  const bytes = readFileSync("public/assets/midnight-v1.webp");
  await page.route("**/fixtures/**", async (route) => {
    if (delay) await new Promise((r) => setTimeout(r, delay));
    await route
      .fulfill(
        fail
          ? { status: 404, body: "Unavailable" }
          : { contentType: "image/webp", body: bytes },
      )
      .catch(() => {});
  });
}
test("sequence source selection, bounded loading, reverse scroll and resize", async ({
  page,
}) => {
  const requests = [];
  page.on("request", (r) => {
    if (r.url().includes("/fixtures/")) requests.push(r.url());
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await mockFilm(page);
  await page.goto("/");
  await expect(page.locator(".film-canvas")).toHaveClass(/visible/);
  await page.waitForTimeout(200);
  expect(requests.length).toBeLessThanOrEqual(7);
  expect(requests.every((u) => u.includes("/portrait/"))).toBe(true);
  await page.evaluate(() => {
    const s = document.querySelector("#intro");
    scrollTo({
      top: (s.offsetHeight - innerHeight) * 0.99,
      behavior: "instant",
    });
  });
  await expect(
    page.getByRole("heading", { name: "Made to become part of your day." }),
  ).toBeVisible();
  await page.evaluate(() => scrollTo({ top: 0, behavior: "instant" }));
  await expect(
    page.getByRole("heading", { name: "Every part, a purpose." }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(page.locator("#intro")).toHaveAttribute(
    "data-source",
    "landscape",
  );
  await expect
    .poll(() => requests.some((u) => u.includes("/landscape/")))
    .toBe(true);
  expect(requests.length).toBeLessThan(65);
});
test("reduced motion never fetches an animation sequence", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockFilm(page);
  const frames = [];
  page.on("request", (r) => {
    if (r.url().includes("/fixtures/")) frames.push(r.url());
  });
  await page.goto("/");
  await page.waitForTimeout(150);
  await expect(page.locator("#intro")).toHaveAttribute(
    "data-sequence",
    "poster",
  );
  await page.locator("#trade-in").scrollIntoViewIfNeeded();
  expect(frames).toEqual([]);
  expect(
    await page.locator("#intro").evaluate((el) => el.offsetHeight),
  ).toBeLessThanOrEqual(1150);
});
test("missing sequence frames retain a visible poster", async ({ page }) => {
  await mockFilm(page, { fail: true });
  await page.goto("/");
  await page.waitForTimeout(300);
  await expect(page.locator(".hero-art img")).toBeVisible();
  await expect(page.locator(".hero-art img")).not.toHaveJSProperty(
    "naturalWidth",
    0,
  );
  await expect(page.locator(".film-canvas")).not.toHaveClass(/visible/);
  await page.getByRole("link", { name: "Skip story", exact: true }).click();
  await expect(page.locator("#collection")).toBeInViewport();
});
test("corrupt local storage is safely ignored", async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem(
      "meridian-bag-v1",
      '[{"id":"midnight","quantity":-4},{"id":"other","quantity":5}]',
    ),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Open bag, 0 items" }).click();
  await expect(page.getByText("A little room for possibility.")).toBeVisible();
});
test("style tile renders shared tokens and working navigation", async ({
  page,
}) => {
  await page.goto("/style-tile.html");
  await expect(
    page.getByRole("heading", { name: "Quiet by design. Precise by nature." }),
  ).toBeVisible();
  await page.screenshot({ path: "artifacts/style-tile.png", fullPage: true });
  await page.getByRole("link", { name: "Explore M01" }).click();
  await expect(page.locator("#collection")).toBeInViewport();
});
test("piecewise timeline has readable holds and exact end coverage", () => {
  for (const mobile of [false, true]) {
    expect(timeline(0, mobile)).toEqual({ beat: 0, frameProgress: 0 });
    expect(timeline(1, mobile)).toEqual({ beat: 3, frameProgress: 1 });
    let previous = 0;
    for (let p = 0; p <= 1; p += 0.01) {
      const result = timeline(p, mobile);
      expect(result.frameProgress).toBeGreaterThanOrEqual(previous);
      previous = result.frameProgress;
    }
  }
});

test("breakpoint changes abort obsolete loads and release decoded bitmaps", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = window.createImageBitmap.bind(window);
    window.bitmapAudit = { active: 0, maximum: 0, closed: 0 };
    window.createImageBitmap = async (...args) => {
      const bitmap = await original(...args);
      const audit = window.bitmapAudit;
      audit.active++;
      audit.maximum = Math.max(audit.maximum, audit.active);
      const close = bitmap.close.bind(bitmap);
      bitmap.close = () => {
        audit.active--;
        audit.closed++;
        close();
      };
      return bitmap;
    };
  });
  const started = [],
    cancelled = [];
  page.on("request", (r) => {
    if (r.url().includes("/fixtures/")) started.push(r.url());
  });
  page.on("requestfailed", (r) => {
    if (r.url().includes("/fixtures/")) cancelled.push(r.url());
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockFilm(page, { delay: 250 });
  await page.goto("/");
  await expect
    .poll(() => started.some((u) => u.includes("/landscape/")))
    .toBe(true);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() => cancelled.some((u) => u.includes("/landscape/")))
    .toBe(true);
  await expect(page.locator(".film-canvas")).toHaveClass(/visible/);
  for (const p of [0.25, 0.75, 0.4, 0.99, 0.02]) {
    await page.evaluate((progress) => {
      const s = document.querySelector("#intro");
      scrollTo({
        top: (s.offsetHeight - innerHeight) * progress,
        behavior: "instant",
      });
    }, p);
    await page.waitForTimeout(400);
  }
  const audit = await page.evaluate(() => window.bitmapAudit);
  expect(audit.active).toBeLessThanOrEqual(13);
  expect(audit.maximum).toBeLessThanOrEqual(16);
  expect(audit.closed).toBeGreaterThan(0);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect
    .poll(() => page.evaluate(() => window.bitmapAudit.active))
    .toBe(0);
});
