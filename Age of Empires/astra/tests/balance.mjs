import { Game } from "../src/simulation.js";
const g = new Game();
g.start();
const assigned = new Set();
let next = 0,
  attackAt = 330;
function build(type) {
  const worker = g.units.find(
    (u) =>
      u.team === "player" && u.type === "villager" && u.order.kind !== "build",
  );
  if (!worker) return false;
  if (type === "tower") {
    for (const [x, y] of [
      [18, 29],
      [17, 28],
      [19, 30],
      [20, 28],
    ])
      if (g.construct(type, x, y, [worker]).ok) return true;
    return false;
  }
  for (let r = 3; r < 13; r++)
    for (let y = 30 - r; y <= 30 + r; y++)
      for (let x = 14 - r; x <= 14 + r; x++) {
        if (g.construct(type, x, y, [worker]).ok) return true;
      }
  return false;
}
for (let t = 0; t < 6600 && g.status === "playing"; t++) {
  g.tick(0.1);
  if (g.time >= next) {
    next = g.time + 3;
    const workers = g.units.filter(
      (u) => u.team === "player" && u.type === "villager",
    );
    const want = {
      food: Math.ceil(workers.length * 0.6),
      wood: Math.max(1, Math.floor(workers.length * 0.2)),
      gold: Math.max(
        0,
        workers.length -
          Math.ceil(workers.length * 0.6) -
          Math.max(1, Math.floor(workers.length * 0.2)),
      ),
    };
    const job = (u) =>
      u.order.kind === "gather"
        ? u.order.resourceType
        : u.order.kind === "return"
          ? u.carryType
          : null;
    const counts = { food: 0, wood: 0, gold: 0 };
    workers.forEach((u) => {
      if (job(u)) counts[job(u)]++;
    });
    for (const u of workers)
      if (!assigned.has(u.id) || u.order.kind === "idle") {
        const type = ["food", "wood", "gold"].sort(
          (a, b) => want[b] - counts[b] - (want[a] - counts[a]),
        )[0];
        g.assignGather(u, type);
        counts[type]++;
        assigned.add(u.id);
      }
    const tc = g.town("player");
    if (workers.length < 10 && tc.queue.length < 2) g.train(tc, "villager");
    const savingForAge = g.time > 145 && g.ages.player === 1 && !tc.research;
    if (savingForAge) g.advance(tc);
    if (
      g.time > 80 &&
      !g.buildings.some((b) => b.team === "player" && b.type === "tower")
    )
      build("tower");
    if (
      g.pop("player") + g.queued("player") >= g.cap("player") - 2 &&
      !g.buildings.some(
        (b) => b.team === "player" && b.type === "house" && !b.complete,
      )
    )
      build("house");
    if (
      g.time > 25 &&
      !g.buildings.some((b) => b.team === "player" && b.type === "barracks")
    )
      build("barracks");
    if (
      g.time > 150 &&
      g.buildings.filter((b) => b.team === "player" && b.type === "barracks")
        .length < 2
    )
      build("barracks");
    for (const b of g.buildings.filter(
      (b) => b.team === "player" && b.type === "barracks" && b.complete,
    ))
      if (b.queue.length < 2 && !savingForAge) g.train(b, "soldier");
    if (
      g.time > attackAt &&
      g.units.filter((u) => u.team === "player" && u.type === "soldier")
        .length >= 10
    ) {
      const enemy =
        g.buildings.find(
          (b) => b.team === "enemy" && b.type === "tower" && g.fog.canSee(b),
        ) || g.town("enemy");
      for (const u of g.units.filter(
        (u) => u.team === "player" && u.type === "soldier",
      ))
        if (g.fog.canSee(enemy)) g.commandAttack(u, enemy);
        else g.commandMove([u], enemy.x + 1, enemy.y + 4);
      attackAt += 35;
    }
  }
  if (t % 600 === 0)
    console.log(
      JSON.stringify({
        time: Math.round(g.time),
        res: Object.fromEntries(
          Object.entries(g.teams.player).map(([k, v]) => [k, Math.round(v)]),
        ),
        p: g.units.filter((u) => u.team === "player").length,
        army: g.units.filter((u) => u.team === "player" && u.type === "soldier")
          .length,
        e: g.units.filter((u) => u.team === "enemy").length,
        age: g.ages.player,
        towers: g.buildings.filter(
          (b) => b.type === "tower" && b.team === "player",
        ).length,
        hp: g.town("player")?.hp,
        enemyhp: g.town("enemy")?.hp,
        raids: g.ai.raids,
      }),
    );
}
console.log(
  JSON.stringify({ outcome: g.status, time: g.time, stats: g.stats, ai: g.ai }),
);
const idle = new Game();
idle.start();
for (let t = 0; t < 9000 && idle.status === "playing"; t++) idle.tick(0.1);
console.log(
  "unattended",
  idle.status,
  idle.time,
  idle.town("player")?.hp,
  idle.ai,
);
