import test from "node:test";
import assert from "node:assert/strict";
import { Game, distanceTo } from "../src/simulation.js";
import { BUILDINGS, UNITS } from "../src/data.js";
function advance(game, seconds) {
  for (let i = 0; i < seconds * 20; i++) game.tick(0.05);
}
function quietGame() {
  const g = new Game();
  g.start();
  g.ai.nextThink = Infinity;
  return g;
}
function site(g, type) {
  for (let y = 27; y < 39; y++)
    for (let x = 10; x < 25; x++)
      if (g.placement(type, x, y).ok) return { x, y };
  throw new Error("No building site");
}

test("reproducible opening has one player town, three villagers and distinct resources", () => {
  const a = new Game(),
    b = new Game();
  assert.equal(a.units.filter((u) => u.team === "player").length, 3);
  assert.equal(a.buildings.filter((u) => u.team === "player").length, 1);
  assert.deepEqual(a.resources, b.resources);
  assert.deepEqual(
    new Set(a.resources.map((r) => r.type)),
    new Set(["food", "wood", "gold"]),
  );
  for (const u of a.units)
    assert.ok(
      a.walkable(Math.floor(u.x), Math.floor(u.y)),
      `unit ${u.id} starts on a blocked cell`,
    );
});
test("gathering requires travel, carrying and delivery before resources increase", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player"),
    food = g.teams.player.food;
  g.assignGather(u, "food");
  advance(g, 2);
  assert.equal(g.teams.player.food, food);
  advance(g, 40);
  assert.ok(g.teams.player.food > food);
  assert.ok(g.stats.gathered >= 14);
  assert.ok(g.goals.gather);
  assert.ok(["gather", "return"].includes(u.order.kind));
});
test("all three resource types deliver and deplete their source", () => {
  for (const type of ["food", "wood", "gold"]) {
    const g = quietGame(),
      u = g.units.find((u) => u.team === "player"),
      before = g.teams.player[type];
    g.assignGather(u, type);
    const r = g.get(u.order.targetId),
      amount = r.amount;
    advance(g, 65);
    assert.ok(g.teams.player[type] > before, `${type} was not delivered`);
    assert.ok(r.amount < amount);
  }
});
test("construction spends wood immediately and adds population only on completion", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player"),
    wood = g.teams.player.wood,
    s = site(g, "house");
  const result = g.construct("house", s.x, s.y, [u]);
  assert.ok(result.ok);
  assert.equal(g.teams.player.wood, wood - 65);
  assert.equal(g.cap("player"), 10);
  assert.equal(result.building.complete, false);
  advance(g, 6);
  assert.equal(result.building.complete, false);
  advance(g, 35);
  assert.equal(result.building.complete, true);
  assert.equal(g.cap("player"), 15);
  assert.ok(g.goals.house);
});
test("overlap, water, map edge, unit occupancy and unaffordable placements are rejected without charge", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player"),
    wood = g.teams.player.wood;
  for (const [x, y] of [
    [12, 30],
    [30, 32],
    [-1, 3],
    [15, 33],
  ]) {
    const r = g.construct("house", x, y, [u]);
    assert.equal(r.ok, false);
    assert.equal(g.teams.player.wood, wood);
  }
  g.teams.player.wood = 0;
  assert.equal(g.construct("house", 22, 30, [u]).ok, false);
});
test("training costs, build times, population reservations and queue refunds apply", () => {
  const g = quietGame(),
    b = g.town("player"),
    food = g.teams.player.food;
  assert.ok(g.train(b, "villager").ok);
  assert.equal(g.teams.player.food, food - 50);
  advance(g, 10);
  assert.equal(g.pop("player"), 3);
  advance(g, 3);
  assert.equal(g.pop("player"), 4);
  assert.ok(g.train(b, "villager").ok);
  g.cancelTrain(b, 0);
  assert.equal(g.teams.player.food, food - 50);
  g.teams.player.food = 999;
  for (let i = 0; i < 5; i++) g.train(b, "villager");
  assert.equal(b.queue.length, 5);
  assert.equal(g.train(b, "villager").ok, false);
  advance(g, 65);
  assert.equal(g.pop("player"), 9);
  assert.ok(g.train(b, "villager").ok);
  assert.equal(g.train(b, "villager").ok, false);
});
test("farm builder begins gathering food after completion", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player"),
    s = site(g, "farm"),
    food = g.teams.player.food;
  assert.ok(g.construct("farm", s.x, s.y, [u]).ok);
  advance(g, 90);
  assert.ok(g.teams.player.food > food);
  assert.ok(["gather", "return"].includes(u.order.kind));
});
test("A* routes around buildings and never cuts a blocked corner", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player");
  u.x = 11.5;
  u.y = 31.5;
  g.commandMove([u], 16.5, 31.5);
  assert.ok(u.path.length > 4);
  let previous = { x: Math.floor(u.x), y: Math.floor(u.y) };
  for (const p of u.path) {
    const x = Math.floor(p.x),
      y = Math.floor(p.y);
    assert.ok(g.walkable(x, y));
    if (x !== previous.x && y !== previous.y) {
      assert.ok(g.walkable(x, previous.y));
      assert.ok(g.walkable(previous.x, y));
    }
    previous = { x, y };
  }
  for (let i = 0; i < 500; i++) {
    g.tick(0.05);
    assert.ok(g.walkable(Math.floor(u.x), Math.floor(u.y)));
  }
  assert.equal(u.order.kind, "idle");
});
test("soldiers acquire a nearby enemy, fight and take damage", () => {
  const g = quietGame(),
    a = g.addUnit("soldier", "player", 24.5, 15.5),
    b = g.addUnit("soldier", "enemy", 25.5, 15.5);
  advance(g, 2);
  assert.ok(a.hp < a.maxHp);
  assert.ok(b.hp < b.maxHp);
  advance(g, 20);
  assert.ok(!g.get(a.id) || !g.get(b.id));
});
test("destroying each town centre through combat produces the appropriate end state", () => {
  for (const [targetTeam, outcome] of [
    ["enemy", "victory"],
    ["player", "defeat"],
  ]) {
    const g = quietGame(),
      target = g.town(targetTeam),
      attackerTeam = targetTeam === "enemy" ? "player" : "enemy";
    g.units = g.units.filter((u) => u.team !== targetTeam);
    for (const p of g.accessTiles(target)) {
      const u = g.addUnit("soldier", attackerTeam, p.x + 0.5, p.y + 0.5);
      g.commandAttack(u, target);
    }
    advance(g, 40);
    assert.equal(g.status, outcome);
    const time = g.time;
    advance(g, 10);
    assert.equal(g.time, time);
    assert.ok(g.events.some((e) => e.type === outcome));
  }
});
test("opponent runs an economy, grows its population and sends a raid", () => {
  const g = new Game();
  g.start();
  advance(g, 160);
  assert.ok(
    g.units.filter((u) => u.team === "enemy" && u.type === "villager").length >
      4,
  );
  assert.ok(
    g.units.filter((u) => u.team === "enemy" && u.type === "soldier").length >=
      3,
  );
  assert.ok(g.ai.raids >= 1);
  assert.ok(g.buildings.filter((b) => b.team === "enemy").length > 3);
});
test("pause freezes resource delivery, queues, movement and match time", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player");
  g.assignGather(u, "gold");
  g.train(g.town("player"), "villager");
  g.paused = true;
  const before = JSON.stringify({
    time: g.time,
    x: u.x,
    y: u.y,
    resources: g.teams,
    queue: g.town("player").queue,
  });
  advance(g, 20);
  assert.equal(
    JSON.stringify({
      time: g.time,
      x: u.x,
      y: u.y,
      resources: g.teams,
      queue: g.town("player").queue,
    }),
    before,
  );
});

test("a worker displaced within an approach tile recentres and resumes gathering", () => {
  const g = quietGame(),
    u = g.units.find((u) => u.team === "player"),
    r = g.resources.find((r) => r.type === "gold" && r.x === 18 && r.y === 26),
    before = g.teams.player.gold;
  u.x = r.x - 0.96;
  u.y = r.y + 0.5;
  assert.ok(g.walkable(Math.floor(u.x), Math.floor(u.y)));
  g.commandGather(u, r);
  advance(g, 60);
  assert.ok(g.teams.player.gold > before);
});
test("idle units separate without crossing building footprints", () => {
  const g = quietGame(),
    a = g.addUnit("soldier", "player", 14.5, 34.5),
    b = g.addUnit("soldier", "player", 14.5, 34.5);
  advance(g, 2);
  assert.ok(Math.hypot(a.x - b.x, a.y - b.y) > 0.4);
  for (const u of [a, b])
    assert.ok(g.walkable(Math.floor(u.x), Math.floor(u.y)));
});
