// Bootstrap: wires the simulation, renderer, controls, HUD and audio together.
import { Game } from './game.js';
import { Renderer } from './render.js';
import { Controls } from './input.js';
import { Hud } from './ui.js';
import { Sound } from './audio.js';
import { TEAM } from './config.js';

const canvas = document.getElementById('game');
const minimapCanvas = document.getElementById('minimap');

function seedFromUrl() {
  const params = new URLSearchParams(location.search);
  const raw = params.get('seed');
  if (raw === 'random') return Math.floor(Math.random() * 1e9);
  const n = Number(raw);
  return Number.isFinite(n) && raw !== null && raw !== '' ? n : 1337;
}

const sound = new Sound();
const renderer = new Renderer(canvas);
// Controls and the HUD reference each other, so wire them after construction.
const controls = new Controls({ canvas, renderer, sound, hud: null });
const hud = new Hud({ game: null, controls, sound });
controls.hud = hud;

let game;
let started = false;
let prevSelectionSignature = '';

function selectionSignature() {
  const u = controls.selUnits.map((x) => `${x.id}:${x.task}:${Math.round(x.hp)}`).join(',');
  const b = controls.selBuilding
    ? `${controls.selBuilding.id}:${controls.selBuilding.queue.length}:${Math.round(controls.selBuilding.hp)}`
    : '';
  return `${u}|${b}`;
}

function boot(seed) {
  game = new Game(seed);
  renderer.setGame(game);
  controls.setGame(game);
  hud.setGame(game);
  hud.onMuteChanged();
  hud.onPauseChanged();
  prevSelectionSignature = '';
}

const applySeed = seedFromUrl();
boot(applySeed);

// Audio needs a user gesture before it can start on most browsers.
const startAudio = () => sound.init();
window.addEventListener('pointerdown', startAudio, { once: true });
window.addEventListener('keydown', startAudio, { once: true });

// The match is rendered behind the title card but does not run until Start.
hud.onStartGame = () => {
  started = true;
  sound.init();
  hud.toast('Gather wood and food, then build a House.', 'good');
};

let prevToastWarn = { pop: false };
function routeEvent(ev) {
  switch (ev.type) {
    case 'warcry':
      if (ev.team === TEAM.ENEMY) hud.toast('Ashfell has sent a raiding party.', 'warn');
      break;
    case 'complete':
      if (ev.team === TEAM.PLAYER) hud.toast('A building is finished.', 'good');
      break;
    case 'victory':
      hud.toast('Ashfell has fallen.', 'good');
      break;
    case 'defeat':
      hud.toast('Your town centre has been destroyed.', 'warn');
      break;
    default:
      break;
  }
}

let last = performance.now();
let acc = 0;
const STEP = 1 / 60;

function frame(now) {
  requestAnimationFrame(frame);
  let dt = (now - last) / 1000;
  last = now;
  if (!Number.isFinite(dt) || dt <= 0) dt = 1 / 60;
  dt = Math.min(dt, 0.1);

  if (hud.restartRequested) {
    hud.restartRequested = false;
    boot(applySeed);
    prevToastWarn = { pop: false };
  }

  if (started) controls.update(dt);

  if (started && !controls.paused) {
    acc += dt;
    let guard = 0;
    while (acc >= STEP && guard++ < 5) {
      game.update(STEP);
      acc -= STEP;
    }
    if (acc > STEP * 6) acc = 0;
    for (const ev of game.drainEvents()) {
      sound.handleEvent(ev);
      routeEvent(ev);
    }
  } else {
    game.drainEvents();
  }

  renderer.draw({
    camera: controls.camera,
    placing: controls.placing,
    dragBox: controls.dragBox,
    isSelected: (e) => controls.isSelected(e),
  });
  renderer.drawMinimap(minimapCanvas, game, controls.camera);
  hud.refresh();

  const sig = selectionSignature();
  if (sig !== prevSelectionSignature) {
    prevSelectionSignature = sig;
    controls.selectionKey = sig;
    hud.actionSignature = '';
  }

  // Warn once when the player is population-capped and idle.
  const capped = game.players[TEAM.PLAYER].pop >= game.players[TEAM.PLAYER].maxPop;
  if (capped && !prevToastWarn.pop) {
    prevToastWarn.pop = true;
    hud.toast('Population limit reached — build a house.', 'warn');
  } else if (!capped) {
    prevToastWarn.pop = false;
  }
}

function resize() {
  renderer.resize();
  controls.clampCamera();
}

window.addEventListener('resize', resize);
resize();
requestAnimationFrame(frame);

// Exposed for verification tooling; not part of the player-facing controls.
window.__verdant = {
  get game() {
    return game;
  },
  controls,
  renderer,
  hud,
  boot,
};
