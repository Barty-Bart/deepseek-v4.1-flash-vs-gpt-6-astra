import { test, expect } from "@playwright/test";
const step = async (page, seconds) =>
  page.evaluate((s) => {
    const g = window.__hearth.game;
    for (let i = 0; i < s * 20; i++) g.tick(0.05);
    window.__hearth.updateUI();
  }, seconds);
const point = async (page, id) =>
  page.evaluate((id) => {
    const { game, renderer } = window.__hearth,
      e = game.get(id);
    const p = renderer.toScreen(e.x + (e.w || 0) / 2, e.y + (e.h || 0) / 2);
    return {
      x: p.x,
      y: p.y - (e.kind === "unit" ? 13 * renderer.camera.zoom : 0),
    };
  }, id);
const clickEntity = async (page, id, button = "left") => {
  const p = await point(page, id);
  await page.mouse.click(p.x, p.y, { button });
};
async function begin(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Found your settlement" }).click();
  await expect(page.locator("#welcome")).toBeHidden();
}
async function place(page, type) {
  await page.locator(`[data-action="build"][data-type="${type}"]`).click();
  const site = await page.evaluate((type) => {
    const { game, renderer } = window.__hearth,
      d = { house: [2, 2], farm: [2, 2], barracks: [3, 2] }[type];
    for (let y = 27; y < 39; y++)
      for (let x = 11; x < 25; x++) {
        const p = renderer.toScreen(x + d[0] / 2, y + d[1] / 2);
        if (
          p.x > 380 &&
          p.x < 1200 &&
          p.y > 230 &&
          p.y < 720 &&
          game.placement(type, x, y).ok
        )
          return { ...p, tx: x, ty: y };
      }
  }, type);
  expect(site).toBeTruthy();
  await page.mouse.move(site.x, site.y);
  await page.mouse.click(site.x, site.y);
  await expect(page.locator("#placement-hint")).toBeHidden();
  return page.evaluate(
    ({ type, site }) =>
      window.__hearth.game.buildings.find(
        (b) =>
          b.team === "player" &&
          b.type === type &&
          b.x === site.tx &&
          b.y === site.ty,
      ).id,
    { type, site },
  );
}

test("player controls exercise gathering, construction, training, camera and pause", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await begin(page);
  const ids = await page.evaluate(() => ({
    town: window.__hearth.game.town("player").id,
    workers: window.__hearth.game.units
      .filter((u) => u.team === "player")
      .map((u) => u.id),
    food: window.__hearth.game.resources.find(
      (r) => r.type === "food" && r.x === 17 && r.y === 32,
    ).id,
  }));
  // Individual selection and a real right-click gathering command.
  await clickEntity(page, ids.workers[0]);
  await expect(page.locator("#selection-name")).toHaveText("Villager");
  await clickEntity(page, ids.food, "right");
  expect(
    await page.evaluate(
      (id) => window.__hearth.game.get(id).order.kind,
      ids.workers[0],
    ),
  ).toBe("gather");
  await step(page, 35);
  expect(
    await page.evaluate(() => window.__hearth.game.teams.player.food),
  ).toBeGreaterThan(240);
  // Invalid placement must remain in placement mode without spending.
  await page.locator('[data-type="house"]').click();
  const townPoint = await point(page, ids.town);
  await page.mouse.move(townPoint.x, townPoint.y);
  await page.mouse.click(townPoint.x, townPoint.y);
  await expect(page.locator("#placement-hint")).toBeVisible();
  await expect(page.locator("#world-notice")).toContainText("clear");
  await page.keyboard.press("Escape");
  const house = await place(page, "house");
  expect(
    await page.evaluate((id) => window.__hearth.game.get(id).complete, house),
  ).toBe(false);
  await step(page, 40);
  expect(
    await page.evaluate((id) => window.__hearth.game.get(id).complete, house),
  ).toBe(true);
  await expect(page.locator("#population")).toContainText("/ 15");
  // Training through the town centre action button.
  await clickEntity(page, ids.town);
  await page.locator('[data-action="train"]').click();
  await expect(page.locator(".queue-item")).toHaveCount(1);
  await step(page, 13);
  expect(await page.evaluate(() => window.__hearth.game.pop("player"))).toBe(4);
  // Drag selection contains villagers only.
  const points = await Promise.all(ids.workers.map((id) => point(page, id)));
  const left = Math.min(...points.map((p) => p.x)) - 18,
    right = Math.max(...points.map((p) => p.x)) + 18,
    top = Math.min(...points.map((p) => p.y)) - 18,
    bottom = Math.max(...points.map((p) => p.y)) + 18;
  await page.mouse.move(left, top);
  await page.mouse.down();
  await page.mouse.move(right, bottom, { steps: 10 });
  await page.mouse.up();
  expect(
    await page.evaluate(
      () =>
        window.__hearth.selected().filter((e) => e.type === "villager").length,
    ),
  ).toBeGreaterThanOrEqual(3);
  // Raise a barracks with the group and train an actual soldier.
  const barracks = await place(page, "barracks");
  await step(page, 35);
  expect(
    await page.evaluate(
      (id) => window.__hearth.game.get(id).complete,
      barracks,
    ),
  ).toBe(true);
  await clickEntity(page, barracks);
  await page.locator('[data-action="train"]').click();
  await step(page, 16);
  expect(
    await page.evaluate(() =>
      window.__hearth.game.units.some(
        (u) => u.team === "player" && u.type === "soldier",
      ),
    ),
  ).toBe(true);
  await page.keyboard.press("q");
  await expect(page.locator("#selection-name")).toHaveText("Spearman");
  await page.mouse.click(960, 560, { button: "right" });
  expect(
    await page.evaluate(() => window.__hearth.selected()[0].order.kind),
  ).toBe("move");
  const oldCamera = await page.evaluate(() => ({
    ...window.__hearth.renderer.camera,
  }));
  await page.keyboard.down("d");
  await page.waitForTimeout(200);
  await page.keyboard.up("d");
  expect(
    await page.evaluate(() => window.__hearth.renderer.camera.x),
  ).toBeGreaterThan(oldCamera.x);
  await page.keyboard.press("h");
  await page.mouse.move(900, 500);
  await page.mouse.wheel(0, -400);
  expect(
    await page.evaluate(() => window.__hearth.renderer.camera.zoom),
  ).toBeGreaterThan(oldCamera.zoom);
  await page.locator("#minimap").click({ position: { x: 155, y: 50 } });
  await page.locator("#home-button").click();
  await page.keyboard.press("Space");
  await expect(page.locator("#pause-modal")).toBeVisible();
  const time = await page.evaluate(() => window.__hearth.game.time);
  await page.waitForTimeout(180);
  expect(await page.evaluate(() => window.__hearth.game.time)).toBe(time);
  await page.getByRole("button", { name: "Return to the borderlands" }).click();
  await page.getByRole("button", { name: "Show controls" }).click();
  await expect(page.locator("#help-modal")).toBeVisible();
  await page.getByRole("button", { name: "Understood" }).click();
  await page.getByRole("button", { name: "Mute sound", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Unmute sound", exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "artifacts/gameplay.png" });
  expect(errors).toEqual([]);
});

test("combat reaches victory and defeat dialogs and restart restores the opening", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await begin(page);
  for (const [team, result, title] of [
    ["enemy", "victory", "Your banner endures."],
    ["player", "defeat", "The hearth falls silent."],
  ]) {
    // Test setup supplies an army; real target acquisition and damage resolve the match.
    await page.evaluate((team) => {
      const { game, renderer, select } = window.__hearth;
      game.ai.nextThink = Infinity;
      const target = game.town(team),
        attacker = team === "enemy" ? "player" : "enemy";
      game.units = game.units.filter((u) => u.team !== team);
      const units = [];
      for (const p of game.accessTiles(target)) {
        const u = game.addUnit("soldier", attacker, p.x + 0.5, p.y + 0.5);
        units.push(u);
        if (attacker === "enemy") game.commandAttack(u, target);
      }
      const p = {
        x: (target.x - target.y) * 32,
        y: (target.x + target.y + 3) * 16,
      };
      renderer.camera.x = p.x;
      renderer.camera.y = p.y;
      select(units);
    }, team);
    if (team === "enemy") {
      const target = await page.evaluate(
        () => window.__hearth.game.town("enemy").id,
      );
      await clickEntity(page, target, "right");
    }
    await step(page, 40);
    expect(await page.evaluate(() => window.__hearth.game.status)).toBe(result);
    await expect(page.locator("#end-title")).toHaveText(title);
    await expect(page.locator("#end-modal")).toBeVisible();
    await page.screenshot({ path: `artifacts/${result}.png` });
    await page.getByRole("button", { name: "Write a new chapter" }).click();
    await expect(page.locator("#end-modal")).toBeHidden();
    expect(await page.evaluate(() => window.__hearth.game.pop("player"))).toBe(
      3,
    );
    await expect(page.locator("#food")).toHaveText("240");
  }
  expect(errors).toEqual([]);
});

test("the interface remains usable at a compact desktop size", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await begin(page);
  await page.keyboard.press(".");
  await expect(page.locator('[data-type="barracks"]')).toBeVisible();
  const boxes = await page.locator(".bottom-ui section").evaluateAll((els) =>
    els.map((e) => {
      const r = e.getBoundingClientRect();
      return { x: r.x, y: r.y, right: r.right, bottom: r.bottom };
    }),
  );
  for (const b of boxes) {
    expect(b.x).toBeGreaterThanOrEqual(0);
    expect(b.right).toBeLessThanOrEqual(1024);
    expect(b.bottom).toBeLessThanOrEqual(768);
  }
  await page.screenshot({ path: "artifacts/compact.png" });
});
