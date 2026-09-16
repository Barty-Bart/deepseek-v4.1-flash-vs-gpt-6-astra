import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const step = async (page, s) =>
  page.evaluate((s) => {
    const { game, updateUI } = window.__hearth;
    for (let i = 0; i < s * 20; i++) game.tick(0.05);
    game.fog.update();
    updateUI();
  }, s);
const clickEntity = async (page, id) => {
  const p = await page.evaluate((id) => {
    const { game, renderer } = window.__hearth,
      e = game.get(id),
      p = renderer.toScreen(e.x + (e.w || 0) / 2, e.y + (e.h || 0) / 2);
    return {
      ...p,
      y: p.y - (e.kind === "unit" ? 15 * renderer.camera.zoom : 0),
    };
  }, id);
  await page.mouse.click(p.x, p.y);
};
test.beforeAll(async () => mkdir("artifacts/v1.1", { recursive: true }));

test("advance through both ages, construct a watchtower, and reset the civilization through the UI", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Found your settlement" }).click();
  await expect(page.locator("#civilization-button")).toContainText(
    "HEARTH AGE",
  );
  await expect(page.locator("#enemy-status")).toContainText("Uncharted");
  await page.screenshot({ path: "artifacts/v1.1/opening-fog.png" });
  await page.evaluate(() => {
    const g = window.__hearth.game;
    g.ai.nextThink = Infinity;
    g.teams.player.food = 800;
    g.teams.player.gold = 500;
  });
  await page.locator('[data-action="advance"]').click();
  await expect(page.locator('[data-action="cancel-advance"]')).toBeVisible();
  await step(page, 5);
  await page.locator('[data-action="cancel-advance"]').click();
  expect(
    await page.evaluate(() => window.__hearth.game.teams.player.food),
  ).toBe(800);
  await page.keyboard.press(".");
  await expect(page.locator('[data-type="tower"]')).toBeVisible();
  await page.keyboard.press("4");
  const site = await page.evaluate(() => {
    const { game, renderer } = window.__hearth;
    for (let x = 18; x < 23; x++)
      for (let y = 28; y < 35; y++) {
        const p = renderer.toScreen(x + 1, y + 1);
        if (p.x < 1150 && p.y < 700 && game.placement("tower", x, y).ok)
          return { ...p, tx: x, ty: y };
      }
  });
  expect(site).toBeTruthy();
  await page.mouse.move(site.x, site.y);
  await page.mouse.click(site.x, site.y);
  await step(page, 45);
  const tower = await page.evaluate(
    () =>
      window.__hearth.game.buildings.find(
        (b) => b.type === "tower" && b.team === "player",
      ).id,
  );
  expect(
    await page.evaluate((id) => window.__hearth.game.get(id).complete, tower),
  ).toBe(true);
  await clickEntity(page, tower);
  await expect(page.locator("#selection-name")).toHaveText("Watchtower");
  await expect(page.locator("#actions")).toContainText("12 attack");
  await page.screenshot({ path: "artifacts/v1.1/watchtower-hearth.png" });
  await page.locator("#civilization-button").click();
  await page.keyboard.press("u");
  await step(page, 36);
  await expect(page.locator("#civilization-button")).toContainText(
    "BANNER AGE",
  );
  await clickEntity(page, tower);
  await expect(page.locator("#selection-health")).toContainText("850");
  await expect(page.locator("#actions")).toContainText("18 attack");
  await page.screenshot({ path: "artifacts/v1.1/watchtower-banner.png" });
  await page.locator("#civilization-button").click();
  await page.locator('[data-action="advance"]').click();
  await step(page, 46);
  await expect(page.locator("#civilization-button")).toContainText(
    "CITADEL AGE",
  );
  await clickEntity(page, tower);
  await expect(page.locator("#selection-health")).toContainText("1050");
  await expect(page.locator("#actions")).toContainText("24 attack");
  await page.screenshot({ path: "artifacts/v1.1/watchtower-citadel.png" });
  // Actual incoming targets cause visible projectiles and damage.
  await page.evaluate((id) => {
    const { game } = window.__hearth,
      b = game.get(id),
      u = game.addUnit("villager", "enemy", b.x + 5.5, b.y + 0.5);
    u.order = { kind: "move", x: u.x, y: u.y };
    game.fog.update();
  }, tower);
  await step(page, 1);
  expect(
    await page.evaluate(() =>
      window.__hearth.game.units.some((u) => u.team === "enemy" && u.hp < 55),
    ),
  ).toBe(true);
  await page.keyboard.press("Space");
  await page.getByRole("button", { name: "Start a new settlement" }).click();
  await expect(page.locator("#civilization-button")).toContainText(
    "HEARTH AGE",
  );
  expect(
    await page.evaluate(() =>
      window.__hearth.game.buildings.some((b) => b.type === "tower"),
    ),
  ).toBe(false);
  expect(
    await page.evaluate(() => window.__hearth.game.fog.state(34, 10)),
  ).toBe(0);
  expect(errors).toEqual([]);
});

test("scouting reveals the map, fog hides live enemies, and revisiting updates remembered structures", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Found your settlement" }).click();
  await page.evaluate(() => {
    const g = window.__hearth.game;
    g.ai.nextThink = Infinity;
    g.units = g.units.filter((u) => u.team === "player");
    g.fog.update();
  });
  const enemy = await page.evaluate(
    () => window.__hearth.game.town("enemy").id,
  );
  const hiddenHit = await page.evaluate((id) => {
    const { game, renderer } = window.__hearth,
      e = game.get(id),
      p = renderer.toScreen(e.x + 1.5, e.y + 1.5);
    return renderer.hitTest(p.x, p.y)?.id;
  }, enemy);
  expect(hiddenHit).toBeUndefined();
  await page.keyboard.press(".");
  // A real right-click into dark land issues an exploration move, not a hidden attack.
  await page.evaluate(() => {
    const r = window.__hearth.renderer;
    r.camera.x = (32.5 - 12.5) * 32;
    r.camera.y = (32.5 + 12.5) * 16;
  });
  const destination = await page.evaluate(() =>
    window.__hearth.renderer.toScreen(32.5, 12.5),
  );
  await page.mouse.click(destination.x, destination.y, { button: "right" });
  expect(
    await page.evaluate(() => window.__hearth.selected()[0].order.kind),
  ).toBe("move");
  await step(page, 25);
  expect(
    await page.evaluate(() => window.__hearth.game.fog.state(34, 10)),
  ).toBe(2);
  await expect(page.locator("#enemy-status")).toContainText("100%");
  await page.screenshot({ path: "artifacts/v1.1/discovered-settlement.png" });
  // Hotkeys must never spend the rival's resources or control its town centre.
  await clickEntity(page, enemy);
  await page.keyboard.press("u");
  await page.keyboard.press("v");
  expect(
    await page.evaluate(() => window.__hearth.game.town("enemy").research),
  ).toBe(null);
  expect(
    await page.evaluate(() => window.__hearth.game.town("enemy").queue.length),
  ).toBe(0);
  await page.keyboard.press(".");

  // Move home using a real command while keeping the camera on the rival settlement.
  await page.evaluate(() => {
    const r = window.__hearth.renderer;
    r.home();
  });
  const home = await page.evaluate(() =>
    window.__hearth.renderer.toScreen(15.5, 33.5),
  );
  await page.mouse.click(home.x, home.y, { button: "right" });
  await step(page, 25);
  expect(
    await page.evaluate(() => window.__hearth.game.fog.state(34, 10)),
  ).toBe(1);
  await expect(page.locator("#enemy-status")).toContainText(
    "scout for updates",
  );
  await page.evaluate(() => {
    const { game, renderer } = window.__hearth;
    game.town("enemy").hp = 123;
    game.addUnit("soldier", "enemy", 33.5, 13.5);
    game.fog.update();
    renderer.camera.x = (34.5 - 10.5) * 32;
    renderer.camera.y = (34.5 + 10.5) * 16;
  });
  const memory = await page.evaluate((id) => {
    const { game } = window.__hearth;
    return {
      hp: game.fog.knownEntities().find((e) => e.id === id).hp,
      enemies: game.fog
        .knownEntities()
        .filter((e) => e.kind === "unit" && e.team === "enemy").length,
    };
  }, enemy);
  expect(memory.hp).toBe(2000);
  expect(memory.enemies).toBe(0);
  await page.screenshot({ path: "artifacts/v1.1/explored-fog.png" });
  expect(errors).toEqual([]);
});

test("all four construction commands fit the compact desktop panel", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  await page.getByRole("button", { name: "Found your settlement" }).click();
  await page.keyboard.press(".");
  for (const type of ["house", "farm", "barracks", "tower"]) {
    const b = page.locator(`[data-type="${type}"]`);
    await expect(b).toBeVisible();
    const r = await b.boundingBox();
    expect(r.x + r.width).toBeLessThanOrEqual(1024);
    expect(r.y + r.height).toBeLessThanOrEqual(768);
  }
  await page.screenshot({ path: "artifacts/v1.1/compact.png" });
});
