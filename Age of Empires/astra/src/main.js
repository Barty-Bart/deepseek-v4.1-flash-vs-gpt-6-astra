import "./style.css";
import { Game } from "./simulation.js";
import { Renderer } from "./renderer.js";
import { Sound } from "./audio.js";
import { BUILDINGS, UNITS, AGES, costText, project } from "./data.js";

const $ = (s) => document.querySelector(s);
const canvas = $("#world"),
  sound = new Sound();
let game = new Game(),
  renderer = new Renderer(canvas, $("#minimap"), game),
  selection = [],
  buildingMode = null,
  started = false,
  lastUI = 0,
  last = performance.now(),
  noticeTimer,
  helpWasPaused = false,
  actionSignature = "",
  pointer = { x: 0, y: 0, inside: false },
  drag = null;
const keys = new Set();
const icons = {
  sound:
    '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>',
  muted: '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="m16 9 6 6m0-6-6 6"/>',
  pause: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
  play: '<path d="m8 4 12 8-12 8z"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 8.5a2.6 2.6 0 1 1 4 2.2c-1.5.8-1.5 1.3-1.5 2.8M12 16v1"/>',
  home: '<path d="m3 11 9-8 9 8M5 10v10h14V10M10 20v-7h4v7"/>',
};
const svg = (path) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true">${path}</svg>`;
$("#sound-button").innerHTML = svg(icons[sound.muted ? "muted" : "sound"]);
$("#sound-button").classList.toggle("muted", sound.muted);
$("#help-button").innerHTML = svg(icons.help);
$("#pause-button").innerHTML = svg(icons.pause);
$("#home-button").innerHTML = svg(icons.home) + " HOME BASE";
const formatTime = (t) =>
  `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
const selected = () =>
  selection.map((id) => game.get(id)).filter((e) => e && game.fog.canSee(e));
const workers = () =>
  selected().filter(
    (e) => e.kind === "unit" && e.type === "villager" && e.team === "player",
  );
const controlled = () =>
  selected().filter((e) => e.kind === "unit" && e.team === "player");
function showNotice(message, error = false) {
  const el = $("#world-notice");
  el.textContent = message;
  el.classList.add("visible");
  el.classList.toggle("error", error);
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => el.classList.remove("visible"), 3800);
  if (error) sound.play("error");
}
function select(entities, add = false) {
  const ids = entities.filter((e) => e && game.fog.canSee(e)).map((e) => e.id);
  selection = add ? [...new Set([...selection, ...ids])] : ids;
  renderer.selected = new Set(selection);
  actionSignature = "";
  updateUI();
  if (ids.length) sound.play("select");
}
function bindEvents() {
  game.listeners.push((e) => {
    if (e.type === "build") sound.play("build");
    if (e.type === "age-advanced" && e.team === "player") {
      sound.play("complete");
      showNotice(
        `${AGES[e.age].name} begins. Your people and watchtowers grow stronger.`,
      );
      actionSignature = "";
    }
    if (e.type === "discovered") {
      showNotice(
        "The Redfen settlement is charted. Their town centre lies ahead.",
      );
      sound.play("complete");
    }
    if (e.type === "arrow" && game.fog.state(e.x, e.y) === 2)
      sound.play("arrow");
    if (e.type === "complete") {
      sound.play("complete");
      showNotice(
        `${BUILDINGS[e.building.type].name} complete.${e.building.type === "house" ? " Room for five more settlers." : e.building.type === "barracks" ? " Your soldiers await." : ""}`,
      );
      actionSignature = "";
    }
    if (e.type === "trained") {
      sound.play("complete");
      if (e.unit.type === "soldier")
        showNotice("A spearman is ready for orders.");
    }
    if (e.type === "hit") {
      const p = renderer.toScreen(e.x, e.y);
      if (
        game.fog.state(e.x, e.y) === 2 &&
        p.x > 0 &&
        p.x < renderer.width &&
        p.y > 0 &&
        p.y < renderer.height
      )
        sound.play("hit");
    }
    if (e.type === "enemy-sighted") {
      showNotice("Redfen spears sighted. Ready your defenders.");
      sound.play("alert");
    }
    if (e.type === "attack-alert") {
      showNotice("Your settlement is under attack!");
      sound.play("alert");
    }
    if (e.type === "victory" || e.type === "defeat") endGame(e.type);
  });
}
bindEvents();
function start() {
  started = true;
  game.start();
  sound.init();
  sound.play("complete");
  $("#welcome").hidden = true;
  renderer.home();
  select([game.town("player")]);
  showNotice(
    "Your story begins. Select villagers and right-click resources to gather.",
  );
}
function restart() {
  game = new Game();
  renderer.game = game;
  bindEvents();
  selection = [];
  buildingMode = null;
  renderer.placement = null;
  renderer.commandMarkers = [];
  keys.clear();
  $("#pause-modal").hidden = true;
  $("#end-modal").hidden = true;
  $("#help-modal").hidden = true;
  $("#placement-hint").hidden = true;
  $("#pause-button").innerHTML = svg(icons.pause);
  $("#pause-button").setAttribute("aria-label", "Pause game");
  canvas.classList.remove("placing");
  game.start();
  renderer.home();
  select([game.town("player")]);
  actionSignature = "";
  updateUI();
  showNotice("A new chapter. Your settlers are ready.");
}
function togglePause(force) {
  if (!started || !["playing"].includes(game.status)) return;
  game.paused = force ?? !game.paused;
  keys.clear();
  $("#pause-modal").hidden = !game.paused;
  $("#pause-button").innerHTML = svg(icons[game.paused ? "play" : "pause"]);
  $("#pause-button").setAttribute(
    "aria-label",
    game.paused ? "Resume game" : "Pause game",
  );
}
function openHelp() {
  helpWasPaused = game.paused;
  game.paused = true;
  keys.clear();
  $("#help-modal").hidden = false;
}
function closeHelp() {
  $("#help-modal").hidden = true;
  game.paused = helpWasPaused;
}
function endGame(result) {
  cancelPlacement();
  sound.play(result);
  $("#pause-modal").hidden = true;
  $("#end-modal").hidden = false;
  const win = result === "victory";
  $("#end-title").textContent = win
    ? "Your banner endures."
    : "The hearth falls silent.";
  $("#end-eyebrow").textContent = win
    ? "VICTORY · THE BORDERLANDS ARE YOURS"
    : "DEFEAT · A CHAPTER, NOT THE END";
  $("#end-message").textContent = win
    ? "The Redfen town centre has fallen. From three humble settlers, you forged a home worth fighting for."
    : "Your town centre has been destroyed. Gather sooner, grow your village, and keep spears close to home.";
  $("#end-stats").innerHTML =
    `<div><strong>${formatTime(game.time)}</strong><span>TIME</span></div><div><strong>${Math.floor(game.stats.gathered)}</strong><span>GATHERED</span></div><div><strong>${game.stats.trained}</strong><span>TRAINED</span></div><div><strong>${game.stats.kills}</strong><span>DEFEATED</span></div>`;
}
function canPlay() {
  return (
    started &&
    game.status === "playing" &&
    !game.paused &&
    $("#help-modal").hidden
  );
}
function beginPlacement(type) {
  if (!canPlay()) return;
  if (!workers().length) {
    showNotice("Select a villager to build.", true);
    return;
  }
  if (!game.afford("player", BUILDINGS[type].cost)) {
    showNotice(`You need ${costText(BUILDINGS[type].cost)}.`, true);
    return;
  }
  buildingMode = type;
  canvas.classList.add("placing");
  $("#placement-hint").hidden = false;
  updateGhost();
  sound.play("select");
}
function cancelPlacement() {
  buildingMode = null;
  renderer.placement = null;
  $("#placement-hint").hidden = true;
  canvas.classList.remove("placing");
}
function updateGhost() {
  if (!buildingMode) return;
  const p = renderer.toWorld(pointer.x, pointer.y),
    d = BUILDINGS[buildingMode],
    x = Math.floor(p.x - d.w / 2 + 0.5),
    y = Math.floor(p.y - d.h / 2 + 0.5),
    valid = game.placement(buildingMode, x, y);
  renderer.placement = { type: buildingMode, x, y, valid: valid.ok };
}
function advanceSelected() {
  if (!canPlay()) return;
  const b = selected()[0];
  if (!b || b.team !== "player" || b.type !== "town") {
    showNotice("Select your town centre to advance.", true);
    return;
  }
  const result = game.advance(b);
  if (!result.ok) showNotice(result.reason, true);
  else {
    sound.play("order");
    showNotice(
      `Advancing to the ${AGES[b.research.age].name}. Villager training waits until research is complete.`,
    );
  }
  actionSignature = "";
  updateUI();
}
function advanceAction(b) {
  if (b.research)
    return `<button class="action advance cancel-research" data-action="cancel-advance" title="Cancel advancement and refund its full cost"><span class="age-icon">${AGES[b.research.age].numeral}</span><span class="action-name">Advancing…</span><span class="cost">Cancel & refund</span><span class="duration research-countdown"></span><i class="research-fill"></i></button>`;
  const age = AGES[game.ages.player + 1];
  if (!age)
    return '<div class="age-complete"><b>III · CITADEL AGE</b><span>Your civilization is fully advanced.</span></div>';
  return `<button class="action advance" data-action="advance" title="${age.name} · ${costText(age.cost)} · ${age.time}s. Per age: +15% gather speed; spearmen +20 health / +3 attack; towers +200 health / +6 attack / +1 range."><span class="hotkey">U</span><span class="age-icon">${age.numeral}</span><span class="action-name">${age.name}</span><span class="cost">♨ ${age.cost.food}  ◆ ${age.cost.gold}</span><span class="duration">Advance · ${age.time} seconds</span></button><div class="age-benefits">A stronger civilization.<small>Faster gathering · veteran spears<br>Stronger towers · wider watch</small></div>`;
}
function trainSelected() {
  const b = selected()[0];
  if (!b || b.team !== "player" || !canPlay()) return;
  const type = BUILDINGS[b.type]?.trains;
  if (!type) return;
  const result = game.train(b, type);
  if (!result.ok) showNotice(result.reason, true);
  else {
    sound.play("order");
    showNotice(`${UNITS[type].name} added to the training queue.`);
  }
  updateUI();
}
function idleVillager() {
  const idle = game.units.filter(
    (u) =>
      u.team === "player" && u.type === "villager" && u.order.kind === "idle",
  );
  if (!idle.length) {
    showNotice("Every villager has a task. Well done.");
    return;
  }
  const index = idle.findIndex((u) => selection.includes(u.id)),
    u = idle[(index + 1) % idle.length];
  select([u]);
  const p = project(u.x, u.y);
  renderer.camera.x = p.x;
  renderer.camera.y = p.y;
}
function selectArmy() {
  const army = game.units.filter(
    (u) => u.team === "player" && u.type === "soldier",
  );
  if (!army.length) {
    showNotice("Build a barracks and train your first spearman.");
    return;
  }
  select(army);
}
function issueOrder(x, y) {
  if (!canPlay()) return;
  if (buildingMode) {
    cancelPlacement();
    return;
  }
  const target = renderer.hitTest(x, y),
    pos = renderer.toWorld(x, y),
    units = controlled(),
    buildings = selected().filter(
      (e) =>
        e.kind === "building" &&
        e.team === "player" &&
        e.complete &&
        BUILDINGS[e.type].trains,
    );
  if (!units.length) {
    if (buildings.length) {
      buildings.forEach((b) => (b.rally = { x: pos.x, y: pos.y }));
      renderer.commandMarkers.push({ ...pos, life: 1 });
      showNotice("Rally point set. New units will gather here.");
      sound.play("order");
    }
    return;
  }
  if (target?.team && target.team !== "player") {
    units.forEach((u) => game.commandAttack(u, target));
    renderer.commandMarkers.push({ ...pos, attack: true, life: 1 });
  } else if (
    target?.kind === "resource" ||
    (target?.type === "farm" && target.complete && target.team === "player")
  ) {
    const v = units.filter((u) => u.type === "villager");
    v.forEach((u) => game.commandGather(u, target));
    game.commandMove(
      units.filter((u) => u.type !== "villager"),
      pos.x,
      pos.y,
    );
    if (v.length)
      showNotice(
        `Gathering ${target.kind === "resource" ? target.type : "food"}. Villagers deliver each load to the town centre.`,
      );
  } else if (
    target?.kind === "building" &&
    !target.complete &&
    target.team === "player"
  ) {
    units
      .filter((u) => u.type === "villager")
      .forEach((u) => game.commandBuild(u, target));
  } else if (
    target?.type === "town" &&
    target.team === "player" &&
    units.some((u) => u.carry > 0)
  ) {
    for (const u of units) {
      if (u.carry > 0) {
        u.order = { kind: "return" };
        game.routeTo(u, target);
      } else game.commandMove([u], pos.x, pos.y);
    }
  } else {
    game.commandMove(units, pos.x, pos.y);
    renderer.commandMarkers.push({ ...pos, life: 1 });
  }
  sound.play("order");
  updateUI();
}
function actionButton(type, kind = "build") {
  const d = kind === "train" ? UNITS[type] : BUILDINGS[type];
  return `<button class="action ${kind === "train" ? "train" : ""}" data-action="${kind}" data-type="${type}" title="${d.name} — ${costText(d.cost)} — ${d.time}s${d.description ? " · " + d.description : ""}"><span class="hotkey">${kind === "train" ? "V" : d.key}</span><canvas width="65" height="52" data-icon="${type}"></canvas><span class="action-name">${kind === "train" ? "Train " : ""}${d.name}</span><span class="cost">${Object.entries(
    d.cost,
  )
    .map(([k, v]) => `${k === "food" ? "♨" : k === "wood" ? "▰" : "◆"} ${v}`)
    .join(
      "  ",
    )}</span><span class="duration">${d.time} seconds</span></button>`;
}
function updateUI() {
  const res = game.teams.player;
  for (const r of ["food", "wood", "gold"]) {
    $("#" + r).textContent = Math.floor(res[r]);
    $("#" + r + "-workers").textContent = game.units.filter(
      (u) =>
        u.team === "player" &&
        ((u.order.kind === "gather" && u.order.resourceType === r) ||
          (u.order.kind === "return" && u.carryType === r)),
    ).length;
  }
  $("#population").innerHTML =
    `${game.pop("player")} <i>/ ${game.cap("player")}</i>`;
  $("#population").style.color =
    game.pop("player") + game.queued("player") >= game.cap("player")
      ? "#e1ad7b"
      : "";
  $("#game-time").textContent = formatTime(game.time);
  $("#zoom-label").textContent = Math.round(renderer.camera.zoom * 100) + "%";
  $("#idle-count").textContent = game.units.filter(
    (u) =>
      u.team === "player" && u.type === "villager" && u.order.kind === "idle",
  ).length;
  const et = game.town("enemy"),
    age = AGES[game.ages.player],
    town = game.town("player");
  $("#civilization-button").innerHTML =
    `<b>${age.numeral}</b> ${age.name.toUpperCase()} <span>${town?.research ? "ADVANCING…" : "↗"}</span>`;
  $("#exploration-label").textContent =
    game.fog.exploredPercent() + "% charted";
  $("#enemy-status").textContent =
    et && game.fog.canSee(et)
      ? `Redfen settlement · ${Math.ceil((et.hp / et.maxHp) * 100)}% strong`
      : game.status === "victory"
        ? "The Redfen banner has fallen"
        : game.fog.discoveredEnemy
          ? "Settlement charted · scout for updates"
          : "Uncharted · explore toward the northeast";
  for (const el of document.querySelectorAll("[data-goal]")) {
    const done = game.goals[el.dataset.goal];
    el.classList.toggle("done", done);
    el.querySelector("b").textContent = done
      ? "✓"
      : { gather: 1, house: 2, barracks: 3, army: 4 }[el.dataset.goal];
  }
  selection = selection.filter(
    (id) => game.get(id) && game.fog.canSee(game.get(id)),
  );
  renderer.selected = new Set(selection);
  const list = selected(),
    e = list[0],
    own = e?.team === "player",
    multiple = list.length > 1,
    workerCount = list.filter((u) => u.type === "villager").length,
    soldierCount = list.filter((u) => u.type === "soldier").length;
  const sig = `${selection.join(",")}-${e?.complete}-${buildingMode}-${game.ages.player}-${e?.research?.age}-${e?.age}`;
  if (actionSignature !== sig) {
    actionSignature = sig;
    renderer.portrait($("#portrait"), e);
    $("#selection-owner").textContent =
      e?.kind === "resource"
        ? "THE BORDERLANDS"
        : own
          ? "HEARTHGUARD · YOUR SETTLEMENT"
          : e
            ? "REDFEN · RIVAL SETTLEMENT"
            : "YOUR SETTLEMENT";
    $("#selection-name").textContent = multiple
      ? `${list.length} ${workerCount === list.length ? "villagers" : soldierCount === list.length ? "spearmen" : "settlers"}`
      : e
        ? e.kind === "unit"
          ? UNITS[e.type].name
          : e.kind === "building"
            ? BUILDINGS[e.type].name
            : e.type === "food"
              ? "Berry bushes"
              : e.type === "wood"
                ? "Woodland"
                : "Gold deposit"
        : "The beginning of a kingdom";
    let html = "",
      label = "SETTLEMENT COMMANDS";
    if (own) {
      if (e.kind === "building" && e.complete && BUILDINGS[e.type].trains) {
        html =
          actionButton(BUILDINGS[e.type].trains, "train") +
          (e.type === "town" ? advanceAction(e) : "");
        label =
          e.type === "town" ? "CIVILIZATION & PEOPLE" : "TRAINING GROUNDS";
      } else if (e.kind === "building" && !e.complete) {
        html =
          '<div class="empty-actions">Your villagers are raising this building.<br>Send more villagers to build it faster.</div>';
        label = "UNDER CONSTRUCTION";
      } else if (workerCount) {
        html = ["house", "farm", "barracks", "tower"]
          .map((t) => actionButton(t))
          .join("");
        label = "BUILD YOUR SETTLEMENT";
      } else if (soldierCount) {
        html =
          '<button class="action stop" data-action="stop" title="Stop selected units (X)"><span class="hotkey">X</span><span class="stop-icon">⊠</span><span class="action-name">Stop</span></button><div class="empty-actions">Right-click an enemy to attack.<br>Your soldiers engage nearby foes.</div>';
        label = "FIELD COMMANDS";
      } else if (e.type === "tower") {
        const stats = game.towerStats(e);
        html = `<div class="tower-info"><b>THE LONG WATCH</b><span>Automatically fires at enemies in range.</span><small>⚔ ${stats.damage} attack · ◎ ${stats.range} range · ◉ ${game.visionRadius(e)} vision</small><span>Advancing ages upgrades every tower.</span></div>`;
        label = "WATCH & DEFEND";
      } else if (e.type === "farm") {
        html =
          '<div class="empty-actions">Select a villager and right-click this farm to gather food.</div>';
        label = "FOOD FOR THE SETTLEMENT";
      } else {
        html =
          '<div class="empty-actions">A place by the fire.<br>This house adds 5 population capacity.</div>';
        label = "ROOM TO GROW";
      }
    } else if (e?.kind === "resource")
      html =
        '<div class="empty-actions">Select your villagers, then right-click here to gather. Each load returns to your town centre.</div>';
    else if (e)
      html =
        '<div class="empty-actions">A rival of the Hearthguard.<br>Select soldiers and right-click to attack.</div>';
    else
      html =
        '<div class="empty-actions">Select a villager to gather and build, or your town centre to train more settlers.</div>';
    $("#actions-label").textContent = label;
    $("#actions").innerHTML = html;
    document
      .querySelectorAll("[data-icon]")
      .forEach((c) => renderer.actionIcon(c, c.dataset.icon));
  }
  for (const b of document.querySelectorAll(".action[data-type]")) {
    const d =
      b.dataset.action === "train"
        ? UNITS[b.dataset.type]
        : BUILDINGS[b.dataset.type];
    b.classList.toggle(
      "unaffordable",
      !game.afford("player", d.cost) ||
        (b.dataset.action === "train" &&
          game.pop("player") + game.queued("player") >= game.cap("player")),
    );
  }
  const advanceButton = $('[data-action="advance"]');
  if (advanceButton)
    advanceButton.classList.toggle(
      "unaffordable",
      !game.afford("player", AGES[game.ages.player + 1].cost),
    );
  if (e?.research) {
    const countdown = $(".research-countdown"),
      fill = $(".research-fill");
    if (countdown)
      countdown.textContent =
        Math.ceil((1 - e.research.progress) * AGES[e.research.age].time) +
        "s remaining";
    if (fill) fill.style.width = e.research.progress * 100 + "%";
  }
  let status = "",
    details = "";
  if (multiple) {
    status = `${workerCount ? workerCount + " villagers" : ""}${workerCount && soldierCount ? " · " : ""}${soldierCount ? soldierCount + " spearmen" : ""}`;
    details = "Right-click to give the group an order.";
  } else if (e?.kind === "unit") {
    status = {
      idle: "Awaiting your orders",
      move: "On the move",
      gather: `Gathering ${e.order.resourceType}`,
      return: "Returning resources to town",
      build: "Constructing a building",
      attack: "In combat",
    }[e.order.kind];
    details = `<div class="stat-pair"><span><strong>⚔ ${game.unitStats(e).damage}</strong> attack</span><span><strong>↗ ${UNITS[e.type].speed}</strong> speed</span>${e.type === "villager" ? `<span><strong>${Math.floor(e.carry)} / 14</strong> carried</span>` : ""}</div>`;
  } else if (e?.kind === "building") {
    status = !e.complete
      ? `Under construction · ${Math.floor(e.progress * 100)}%`
      : e.type === "town"
        ? `${AGES[game.ages[e.team]].name} · ${e.research ? "Advancing civilization" : "The heart of your settlement"}`
        : e.type === "barracks"
          ? "Discipline. Courage. A sharpened spear."
          : e.type === "farm"
            ? `${Math.ceil(e.amount)} food remaining`
            : e.type === "tower"
              ? `${AGES[game.ages[e.team]].name} · ${e.targetId ? "Arrows loosed at the enemy" : "Watching the borderlands"}`
              : "A home for five more settlers";
    if (e.research) {
      details = `<div class="research-track"><i style="width:${e.research.progress * 100}%"></i></div><span>Advancing to ${AGES[e.research.age].name} · ${Math.ceil((1 - e.research.progress) * AGES[e.research.age].time)}s${e.queue.length ? " · " + e.queue.length + " villager(s) waiting" : ""}</span>`;
    } else if (e.queue.length) {
      details =
        '<div class="queue">' +
        e.queue
          .map(
            (q, i) =>
              `<div class="queue-item" title="${UNITS[q.type].name} · ${i === 0 ? Math.ceil((1 - q.progress) * UNITS[q.type].time) + "s remaining" : "Waiting"}">${q.type === "villager" ? "♟" : "⚔"}${own ? `<button data-cancel="${i}" aria-label="Cancel queued ${UNITS[q.type].name}">×</button>` : ""}<i style="width:${q.progress * 100}%"></i></div>`,
          )
          .join("") +
        `<span class="queue-label">${Math.ceil((1 - e.queue[0].progress) * UNITS[e.queue[0].type].time)}s · ${e.queue.length} queued</span></div>`;
    } else
      details =
        e.complete && BUILDINGS[e.type].trains
          ? "Queue up to 5 units · Right-click to set a rally point"
          : e.type === "farm"
            ? "A villager will work the farm after building it."
            : e.type === "house"
              ? "Population capacity +5 when complete."
              : "";
  } else if (e?.kind === "resource") {
    status = `${Math.ceil(e.amount)} ${e.type} available`;
    details = "Carry capacity: 14 · Drop-off: town centre";
  } else status = "Select a villager or your town centre.";
  $("#selection-status").textContent = status;
  $("#selection-details").innerHTML = details;
  if (e?.hp) {
    const hp = multiple ? list.reduce((n, e) => n + e.hp, 0) : e.hp,
      max = multiple ? list.reduce((n, e) => n + e.maxHp, 0) : e.maxHp;
    $("#selection-health").innerHTML =
      `<div class="health-track"><div class="health-fill" style="width:${Math.max(0, (hp / max) * 100)}%;${!own ? "background:#ba7764" : ""}"></div></div><div class="health-label"><span>HEALTH</span><b>${Math.ceil(hp)} / ${max}</b></div>`;
  } else $("#selection-health").innerHTML = "";
  $("#field-tip").innerHTML =
    game.time < 65
      ? "A busy village is a strong village.<br>Keep your workers gathering."
      : !game.goals.barracks
        ? "A quiet border never stays quiet.<br>Raise a barracks."
        : game.time < 170
          ? "A handful of spears at home<br>can save a whole settlement."
          : "A kingdom is built together.<br>Send your army as one.";
}
$("#start-button").onclick = start;
$("#pause-button").onclick = () => togglePause();
$("#resume-button").onclick = () => togglePause(false);
$("#restart-button").onclick = restart;
$("#play-again").onclick = restart;
$("#sound-button").onclick = () => {
  sound.init();
  sound.toggle();
  $("#sound-button").innerHTML = svg(icons[sound.muted ? "muted" : "sound"]);
  $("#sound-button").classList.toggle("muted", sound.muted);
  $("#sound-button").setAttribute(
    "aria-label",
    sound.muted ? "Unmute sound" : "Mute sound",
  );
};
$("#help-button").onclick = openHelp;
$("#close-help").onclick = closeHelp;
$("#home-button").onclick = () => renderer.home();
$("#civilization-button").onclick = () => {
  renderer.home();
  select([game.town("player")]);
};
$("#zoom-in").onclick = () => renderer.zoomAt(1.15);
$("#zoom-out").onclick = () => renderer.zoomAt(1 / 1.15);
$("#idle-button").onclick = idleVillager;
$("#army-button").onclick = selectArmy;
$("#guide-toggle").onclick = () => {
  const el = $("#guide-list");
  el.hidden = !el.hidden;
  $("#guide-toggle span").textContent = el.hidden ? "+" : "−";
};
$("#actions").onclick = (e) => {
  const b = e.target.closest("[data-action]");
  if (!b) return;
  if (b.dataset.action === "build") beginPlacement(b.dataset.type);
  if (b.dataset.action === "train") trainSelected();
  if (b.dataset.action === "advance") advanceSelected();
  if (b.dataset.action === "cancel-advance" && canPlay()) {
    game.cancelAdvance(selected()[0]);
    actionSignature = "";
    updateUI();
  }
  if (b.dataset.action === "stop")
    controlled().forEach((u) => {
      u.order = { kind: "idle" };
      u.path = [];
    });
};
$("#selection-details").onclick = (e) => {
  const b = e.target.closest("[data-cancel]");
  if (b && canPlay()) {
    const target = selected()[0];
    if (target?.team === "player")
      game.cancelTrain(target, Number(b.dataset.cancel));
    updateUI();
  }
};
canvas.addEventListener("contextmenu", (e) => {
  e.preventDefault();
  issueOrder(e.clientX, e.clientY);
});
canvas.addEventListener("pointerdown", (e) => {
  if (!canPlay()) return;
  sound.init();
  if (e.button === 2) return;
  pointer = { x: e.clientX, y: e.clientY, inside: true };
  if (e.button === 0 && buildingMode) {
    updateGhost();
    const p = renderer.placement;
    const result = game.construct(buildingMode, p.x, p.y, workers());
    if (result.ok) {
      cancelPlacement();
      showNotice("Foundation laid. Your villagers are on their way.");
      updateUI();
    } else showNotice(result.reason, true);
    return;
  }
  drag = {
    x: e.clientX,
    y: e.clientY,
    lastX: e.clientX,
    lastY: e.clientY,
    button: e.button,
    moved: false,
    shift: e.shiftKey,
  };
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove", (e) => {
  pointer = { x: e.clientX, y: e.clientY, inside: true };
  if (drag) {
    if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 5)
      drag.moved = true;
    if (drag.button === 1) {
      renderer.camera.x -= (e.clientX - drag.lastX) / renderer.camera.zoom;
      renderer.camera.y -= (e.clientY - drag.lastY) / renderer.camera.zoom;
      renderer.clampCamera();
    } else if (drag.button === 0 && drag.moved)
      renderer.selectionBox = {
        x: drag.x,
        y: drag.y,
        w: e.clientX - drag.x,
        h: e.clientY - drag.y,
      };
    drag.lastX = e.clientX;
    drag.lastY = e.clientY;
  } else {
    renderer.hover = canPlay() ? renderer.hitTest(e.clientX, e.clientY) : null;
    canvas.classList.toggle("can-interact", !!renderer.hover);
  }
  updateGhost();
});
canvas.addEventListener("pointerup", (e) => {
  if (!drag) return;
  if (drag.button === 0) {
    if (drag.moved) {
      const x1 = Math.min(drag.x, e.clientX),
        x2 = Math.max(drag.x, e.clientX),
        y1 = Math.min(drag.y, e.clientY),
        y2 = Math.max(drag.y, e.clientY);
      const list = game.units.filter((u) => {
        const p = renderer.toScreen(u.x, u.y);
        return (
          u.team === "player" &&
          p.x >= x1 &&
          p.x <= x2 &&
          p.y - 12 * renderer.camera.zoom >= y1 &&
          p.y - 12 * renderer.camera.zoom <= y2
        );
      });
      select(list, drag.shift);
    } else {
      const hit = renderer.hitTest(e.clientX, e.clientY);
      if (drag.shift && hit && selection.includes(hit.id)) {
        selection = selection.filter((id) => id !== hit.id);
        renderer.selected = new Set(selection);
        actionSignature = "";
        updateUI();
      } else select(hit ? [hit] : [], drag.shift);
    }
  }
  drag = null;
  renderer.selectionBox = null;
});
canvas.addEventListener("pointercancel", () => {
  drag = null;
  renderer.selectionBox = null;
});
canvas.addEventListener("pointerleave", () => {
  pointer.inside = false;
  renderer.hover = null;
});
canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    renderer.zoomAt(Math.exp(-e.deltaY * 0.0012), e.clientX, e.clientY);
    updateGhost();
  },
  { passive: false },
);
$("#minimap").addEventListener("pointerdown", (e) => {
  const rect = e.target.getBoundingClientRect();
  renderer.minimapClick(
    ((e.clientX - rect.left) / rect.width) * e.target.width,
    ((e.clientY - rect.top) / rect.height) * e.target.height,
  );
});
window.addEventListener("keydown", (e) => {
  if (e.target.matches("input,textarea")) return;
  const k = e.key.toLowerCase();
  if ([" ", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(k))
    e.preventDefault();
  if (k === "escape") {
    if (!$("#help-modal").hidden) closeHelp();
    else if (buildingMode) cancelPlacement();
    else if (game.paused) togglePause(false);
    else select([]);
    return;
  }
  if (k === "m" && !e.repeat) {
    $("#sound-button").click();
    return;
  }
  if (k === "?" && !e.repeat) {
    openHelp();
    return;
  }
  if (k === " " && !e.repeat) {
    if (!$("#help-modal").hidden) return;
    togglePause();
    return;
  }
  if (!canPlay()) return;
  keys.add(k);
  if (e.repeat) return;
  if (k === "h") renderer.home();
  if (k === ".") idleVillager();
  if (k === "q") selectArmy();
  if (k === "v") trainSelected();
  if (k === "u") advanceSelected();
  if (["1", "2", "3", "4"].includes(k))
    beginPlacement(["house", "farm", "barracks", "tower"][Number(k) - 1]);
  if (k === "x")
    controlled().forEach((u) => {
      u.order = { kind: "idle" };
      u.path = [];
    });
});
window.addEventListener("keyup", (e) => keys.delete(e.key.toLowerCase()));
window.addEventListener("blur", () => {
  keys.clear();
  drag = null;
  renderer.selectionBox = null;
  if (canPlay()) togglePause(true);
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden && canPlay()) togglePause(true);
  last = performance.now();
});
function frame(now) {
  const dt = Math.min((now - last) / 1000, 0.06);
  last = now;
  if (canPlay()) {
    const speed = 600 / renderer.camera.zoom;
    let dx =
        (keys.has("d") || keys.has("arrowright") ? 1 : 0) -
        (keys.has("a") || keys.has("arrowleft") ? 1 : 0),
      dy =
        (keys.has("s") || keys.has("arrowdown") ? 1 : 0) -
        (keys.has("w") || keys.has("arrowup") ? 1 : 0);
    if (pointer.inside && !drag) {
      if (pointer.x < 9) dx -= 1;
      if (pointer.x > renderer.width - 9) dx += 1;
      if (pointer.y < 9) dy -= 1;
      if (pointer.y > renderer.height - 9) dy += 1;
    }
    if (dx || dy) {
      const norm = Math.hypot(dx, dy);
      renderer.camera.x += (dx / norm) * speed * dt;
      renderer.camera.y += (dy / norm) * speed * dt;
      renderer.clampCamera();
      updateGhost();
    }
    game.tick(dt);
  }
  renderer.draw(dt, now / 1000);
  if (now - lastUI > 130) {
    updateUI();
    lastUI = now;
  }
  requestAnimationFrame(frame);
}
// Development inspection hook, excluded from production builds. No player shortcuts.
if (import.meta.env.DEV)
  Object.defineProperty(window, "__hearth", {
    get: () => ({
      game,
      renderer,
      select,
      selected,
      beginPlacement,
      updateUI,
      restart,
    }),
  });
updateUI();
renderer.camera.x -= (renderer.width * 0.2) / renderer.camera.zoom;
requestAnimationFrame(frame);
