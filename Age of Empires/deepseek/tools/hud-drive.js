// Boots the real index.html HUD markup and drives a selection, so the whole
// player-facing interface can be verified and screenshotted.
import { Game } from '../src/game.js';
import { Renderer } from '../src/render.js';
import { Controls } from '../src/input.js';
import { Hud } from '../src/ui.js';
import { Sound } from '../src/audio.js';
import { TEAM } from '../src/config.js';

const params = new URLSearchParams(location.search);

// Reuse the shipped markup rather than duplicating it.
const html = await fetch('../index.html').then((r) => r.text());
const parsed = new DOMParser().parseFromString(html, 'text/html');
document.body.innerHTML = parsed.body.innerHTML;

const canvas = document.getElementById('game');
const minimapCanvas = document.getElementById('minimap');
const sound = new Sound();
const renderer = new Renderer(canvas);
const controls = new Controls({ canvas, renderer, sound, hud: null });
const hud = new Hud({ game: null, controls, sound });
controls.hud = hud;

let game = new Game(Number(params.get('seed') || 1337));
renderer.setGame(game);
controls.setGame(game);
hud.setGame(game);
hud.hideMenu();
renderer.resize();
controls.clampCamera();

const scenario = params.get('scenario') || 'villagers';

if (scenario === 'midgame' || scenario === 'battle' || scenario === 'train') {
  const seconds = Number(params.get('t') || 300);
  const { updateAI } = await import('../src/ai.js');
  renderer.setGame(game);
  controls.setGame(game);
  for (let i = 0; i < seconds * 30; i++) {
    updateAI(game, 1 / 30, 0);
    game.update(1 / 30);
    game.drainEvents();
    if (game.state !== 'playing') break;
  }
  hud.setGame(game);
}

if (scenario === 'age') {
  const tc = game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter');
  game.players[0].res = { food: 900, wood: 900, gold: 600 };
  controls.setSelection([], tc);
  controls.centerOn(tc.x, tc.y + 40);
} else if (scenario === 'formation') {
  const { updateAI } = await import('../src/ai.js');
  const seconds = Number(params.get('t') || 330);
  for (let i = 0; i < seconds * 30; i++) {
    updateAI(game, 1 / 30, 0);
    game.update(1 / 30);
    game.drainEvents();
    if (game.state !== 'playing') break;
  }
  hud.setGame(game);
  const army = game.units.filter((u) => u.team === TEAM.PLAYER && u.type !== 'villager').slice(0, 8);
  if (army.length) {
    controls.setSelection(army, null);
    controls.formation = 'line';
    game.reformUnits(army, 'line');
    controls.centerOn(army[0].x, army[0].y);
  } else {
    const tc = game.buildings.find((b) => b.team === TEAM.PLAYER);
    controls.setSelection([], tc);
    controls.centerOn(tc.x, tc.y);
  }
} else if (scenario === 'ring') {
  const v = game.units.find((u) => u.team === TEAM.PLAYER);
  controls.centerOn(v.x, v.y - 20);
  const rect = canvas.getBoundingClientRect();
  const sx = rect.left + (v.x - controls.camera.x) * controls.camera.zoom;
  const sy = rect.top + (v.y - controls.camera.y) * controls.camera.zoom;
  canvas.dispatchEvent(new MouseEvent('mousedown', { clientX: sx, clientY: sy, button: 0, bubbles: true }));
  window.dispatchEvent(new MouseEvent('mouseup', { clientX: sx, clientY: sy, button: 0, bubbles: true }));
  // Freeze the ring part-way through its expansion so a still frame shows it.
  game.rings.forEach((r) => { r.life = r.max * 0.4; });
} else if (scenario === 'scouted') {
  const { updateAI } = await import('../src/ai.js');
  for (let i = 0; i < 150 * 30; i++) {
    updateAI(game, 1 / 30, 0);
    game.update(1 / 30);
    game.drainEvents();
    if (game.state !== 'playing') break;
  }
  hud.setGame(game);
  // Send a scout out and bring it home, so the ground it crossed is remembered
  // but no longer watched.
  const scout = game.units.find((u) => u.team === TEAM.PLAYER && u.type !== 'villager')
    || game.units.find((u) => u.team === TEAM.PLAYER);
  const homeX = scout.x;
  const homeY = scout.y;
  const outX = homeX + 430;
  const outY = homeY - 250;
  scout.x = outX;
  scout.y = outY;
  for (let i = 0; i < 45; i++) game.update(1 / 30);
  scout.x = homeX;
  scout.y = homeY;
  for (let i = 0; i < 12; i++) game.update(1 / 30);
  game.drainEvents();
  window.__scoutSpot = { x: outX, y: outY };
  // Park the camera on the frontier between watched and merely remembered land.
  const f = game.fog[0];
  let best = null;
  for (let r = 2; r < 58; r++) {
    for (let c = 2; c < 78; c++) {
      const i = r * 80 + c;
      if (!f.explored[i] || f.visible[i]) continue;
      let near = 0;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        if (f.visible[(r + dy) * 80 + c + dx]) near++;
      }
      if (near > 0 && (!best || near > best.near)) best = { c, r, near };
    }
  }
  if (best) controls.centerOn(best.c * 32, best.r * 32);
  else controls.centerOn(outX, outY);
  const army = game.units.filter((u) => u.team === TEAM.PLAYER && u.type !== 'villager').slice(0, 6);
  controls.setSelection(army, null);
} else if (scenario === 'villagers') {
  const vills = game.units.filter((u) => u.team === TEAM.PLAYER);
  controls.setSelection(vills, null);
  const tc = game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter');
  controls.centerOn(tc.x + 70, tc.y - 40);
} else if (scenario === 'train') {
  const barracks = game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'barracks' && b.complete)
    || game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter');
  if (barracks) {
    game.queueTrain(barracks, barracks.type === 'barracks' ? 'soldier' : 'villager');
    controls.setSelection([], barracks);
    controls.centerOn(barracks.x, barracks.y);
  }
} else {
  const soldiers = game.units.filter((u) => u.team === TEAM.PLAYER && u.type !== 'villager').slice(0, 6);
  const focusSource = game.buildings.find((b) => b.team === TEAM.PLAYER);
  const focus = soldiers.length ? soldiers[0] : focusSource;
  controls.setSelection(soldiers, null);
  controls.centerOn(focus.x, focus.y);
  if (!soldiers.length) {
    const tc = game.buildings.find((b) => b.team === TEAM.PLAYER && b.type === 'towncenter');
    controls.setSelection([], tc);
  }
}

if (params.get('placing')) {
  const villager = game.units.find((u) => u.team === TEAM.PLAYER);
  controls.setSelection([villager], null);
  controls.startPlacing(params.get('placing'));
  controls.pointer = { x: canvas.getBoundingClientRect().left + 640, y: canvas.getBoundingClientRect().top + 360, inside: true };
  controls.update(1 / 60);
}

function paint() {
  renderer.draw({
    camera: controls.camera,
    placing: controls.placing,
    dragBox: controls.dragBox,
    isSelected: (e) => controls.isSelected(e),
  });
  renderer.drawMinimap(minimapCanvas, game, controls.camera);
  hud.refresh();
}
paint();
if (params.get('loop') === '1') {
  let last = performance.now();
  const frame = (now) => {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    if (!controls.paused) game.update(dt);
    game.drainEvents();
    controls.update(dt);
    paint();
  };
  requestAnimationFrame(frame);
}
window.__hudHarness = { game, controls, hud, paint };
document.title = 'HUD-READY';
