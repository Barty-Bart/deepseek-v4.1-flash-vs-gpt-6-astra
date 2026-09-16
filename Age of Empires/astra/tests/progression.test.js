import test from "node:test";
import assert from "node:assert/strict";
import { Game } from "../src/simulation.js";
import { AGES } from "../src/data.js";
const run = (g, s) => {
  for (let i = 0; i < s * 20; i++) g.tick(0.05);
};
const fresh = () => {
  const g = new Game();
  g.start();
  g.ai.nextThink = Infinity;
  return g;
};

test("advancement spends resources, respects research time, pauses training, and can be refunded", () => {
  const g = fresh(),
    town = g.town("player");
  g.teams.player.food = 500;
  assert.ok(g.train(town, "villager").ok);
  const food = g.teams.player.food,
    gold = g.teams.player.gold;
  assert.ok(g.advance(town).ok);
  assert.equal(g.teams.player.food, food - 200);
  assert.equal(g.teams.player.gold, gold - 100);
  assert.equal(g.advance(town).ok, false);
  run(g, 15);
  assert.equal(g.ages.player, 1);
  assert.equal(town.queue[0].progress, 0);
  assert.ok(town.research.progress > 0);
  g.paused = true;
  const progress = town.research.progress;
  run(g, 10);
  assert.equal(town.research.progress, progress);
  g.paused = false;
  g.cancelAdvance(town);
  assert.equal(g.teams.player.food, food);
  assert.equal(g.teams.player.gold, gold);
  assert.equal(town.research, null);
  assert.ok(g.advance(town).ok);
  run(g, 34);
  assert.equal(g.ages.player, 1);
  run(g, 2);
  assert.equal(g.ages.player, 2);
  assert.equal(town.research, null);
  run(g, 12);
  assert.equal(g.pop("player"), 4);
});
test("both age upgrades improve existing and newly trained units and towers without skipping levels", () => {
  const g = fresh(),
    town = g.town("player"),
    soldier = g.addUnit("soldier", "player", 14.5, 34.5),
    tower = g.addBuilding("tower", "player", 20, 30, true);
  g.teams.player.food = 1000;
  g.teams.player.gold = 1000;
  soldier.hp -= 20;
  tower.hp -= 50;
  assert.ok(g.advance(town).ok);
  run(g, 36);
  assert.equal(g.ages.player, 2);
  assert.equal(soldier.maxHp, 135);
  assert.equal(soldier.hp, 115);
  assert.equal(g.unitStats(soldier).damage, 17);
  assert.equal(tower.maxHp, 850);
  assert.equal(tower.hp, 800);
  assert.equal(g.towerStats(tower).range, 8);
  assert.ok(g.advance(town).ok);
  run(g, 46);
  assert.equal(g.ages.player, 3);
  assert.equal(g.unitStats(soldier).damage, 20);
  assert.equal(tower.maxHp, 1050);
  assert.equal(g.towerStats(tower).damage, 24);
  assert.equal(g.towerStats(tower).range, 9);
  const veteran = g.addUnit("soldier", "player", 14.5, 35.5);
  assert.equal(veteran.hp, 155);
  assert.equal(g.advance(town).ok, false);
});
test("advancement accelerates gathering without granting free resources", () => {
  const amounts = [];
  for (const age of [1, 2, 3]) {
    const g = fresh(),
      u = g.units.find((u) => u.team === "player");
    g.completeAdvance("player", age);
    const r = g.resources.find(
      (r) => r.type === "food" && r.x === 17 && r.y === 32,
    );
    u.x = 16.5;
    u.y = 32.5;
    g.commandGather(u, r);
    const before = g.teams.player.food;
    run(g, 2);
    assert.equal(g.teams.player.food, before);
    amounts.push(u.carry);
  }
  assert.ok(amounts[1] > amounts[0]);
  assert.ok(amounts[2] > amounts[1]);
});
test("watchtowers cost resources, require construction, and provide vision only after completion", () => {
  const g = fresh(),
    u = g.units.find((u) => u.team === "player");
  let site;
  for (let y = 25; y < 38 && !site; y++)
    for (let x = 10; x < 25; x++)
      if (g.placement("tower", x, y).ok) {
        site = { x, y };
        break;
      }
  const wood = g.teams.player.wood,
    gold = g.teams.player.gold,
    result = g.construct("tower", site.x, site.y, [u]);
  assert.ok(result.ok);
  const b = result.building;
  assert.equal(g.teams.player.wood, wood - 110);
  assert.equal(g.teams.player.gold, gold - 50);
  assert.equal(b.complete, false);
  assert.equal(g.visionRadius(b), 2.5);
  run(g, 50);
  assert.ok(b.complete);
  assert.equal(g.visionRadius(b), 10);
  assert.ok(g.fog.state(b.x + 7, b.y) === 2);
});
test("towers acquire only enemies in range and arrows do real damage after flight", () => {
  const g = fresh();
  g.units = [];
  const tower = g.addBuilding("tower", "player", 23, 16, true),
    enemy = g.addUnit("villager", "enemy", 27.5, 17.5),
    friend = g.addUnit("villager", "player", 25.5, 17.5);
  enemy.order = { kind: "move", x: enemy.x, y: enemy.y };
  g.fog.update();
  g.updateTower(tower, 0.1);
  assert.equal(enemy.hp, 55);
  assert.equal(g.projectiles.length, 1);
  assert.equal(g.projectiles[0].targetId, enemy.id);
  g.updateProjectiles(1);
  assert.equal(enemy.hp, 43);
  assert.equal(friend.hp, 55);
  enemy.x = 40.5;
  enemy.y = 30.5;
  tower.cooldown = 0;
  g.updateTower(tower, 2);
  assert.equal(g.projectiles.length, 0);
  tower.complete = false;
  enemy.x = 27.5;
  enemy.y = 17.5;
  run(g, 0.5);
  assert.equal(enemy.hp, 43);
});
test("discovery starts dark, reveals with scouts, and retains explored terrain after they leave", () => {
  const g = fresh();
  assert.equal(g.fog.state(34, 10), 0);
  assert.equal(g.fog.state(13, 31), 2);
  assert.ok(g.fog.exploredPercent() < 20);
  const scout = g.units.find((u) => u.team === "player");
  scout.x = 32.5;
  scout.y = 12.5;
  g.fog.update();
  assert.equal(g.fog.state(34, 10), 2);
  assert.ok(g.fog.discoveredEnemy);
  const explored = g.fog.exploredPercent();
  scout.x = 15.5;
  scout.y = 33.5;
  g.fog.update();
  assert.equal(g.fog.state(34, 10), 1);
  assert.equal(g.fog.exploredPercent(), explored);
  assert.equal(g.fog.state(45, 44), 0);
});
test("fog hides units and remembers buildings as last observed without leaking hidden changes", () => {
  const g = fresh(),
    town = g.town("enemy"),
    scout = g.units.find((u) => u.team === "player");
  assert.ok(!g.fog.knownEntities().some((e) => e.team === "enemy"));
  scout.x = 32.5;
  scout.y = 12.5;
  g.fog.update();
  const hp = town.hp;
  assert.ok(
    g.fog.knownEntities().some((e) => e.kind === "unit" && e.team === "enemy"),
  );
  scout.x = 15.5;
  scout.y = 33.5;
  g.fog.update();
  town.hp = 1000;
  g.completeAdvance("enemy", 2);
  assert.equal(g.fog.knownEntities().find((e) => e.id === town.id).hp, hp);
  assert.equal(g.fog.knownEntities().find((e) => e.id === town.id).age, 1);
  assert.ok(
    !g.fog.knownEntities().some((e) => e.kind === "unit" && e.team === "enemy"),
  );
  // An unseen demolished building remains a memory until the area is visited.
  g.buildings = g.buildings.filter((b) => b.id !== town.id);
  g.fog.update();
  assert.ok(g.fog.knownEntities().some((e) => e.id === town.id));
  scout.x = 32.5;
  scout.y = 12.5;
  g.fog.update();
  assert.ok(!g.fog.knownEntities().some((e) => e.id === town.id));
});
test("remembered resources keep their last observed quantity and hidden placement is rejected", () => {
  const g = fresh(),
    scout = g.units.find((u) => u.team === "player"),
    r = g.resources.find((r) => r.type === "gold" && r.x === 26 && r.y === 23);
  scout.x = 25.5;
  scout.y = 23.5;
  g.fog.update();
  const amount = r.amount;
  scout.x = 15.5;
  scout.y = 33.5;
  g.fog.update();
  r.amount = 0;
  g.rebuildBlocked();
  g.fog.update();
  assert.equal(g.fog.knownEntities().find((e) => e.id === r.id).amount, amount);
  assert.equal(g.placement("tower", 43, 43).ok, false);
  assert.match(g.placement("tower", 43, 43).reason, /Explore/);
  scout.x = 25.5;
  scout.y = 23.5;
  g.fog.update();
  assert.ok(!g.fog.knownEntities().some((e) => e.id === r.id));
});
test("restarting creates fresh age, exploration, research and tower state", () => {
  const g = fresh();
  g.completeAdvance("player", 3);
  g.addBuilding("tower", "player", 20, 30, true);
  const scout = g.units.find((u) => u.team === "player");
  scout.x = 34;
  scout.y = 13;
  g.fog.update();
  const reset = new Game();
  assert.equal(reset.ages.player, 1);
  assert.equal(reset.fog.state(34, 10), 0);
  assert.ok(!reset.buildings.some((b) => b.type === "tower"));
  assert.equal(reset.town("player").research, null);
  assert.equal(reset.projectiles.length, 0);
});
