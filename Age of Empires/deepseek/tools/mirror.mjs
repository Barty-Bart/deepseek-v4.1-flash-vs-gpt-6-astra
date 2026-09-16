// Balance probe: both settlements run the same AI. A healthy match is decided by
// play rather than by one side being strictly stronger.
import { Game } from '../src/game.js';
import { updateAI } from '../src/ai.js';

const args = process.argv.slice(2);
const minutes = Number(args.find((a) => /^\d+(\.\d+)?$/.test(a)) || 12);
const seedArg = args.find((a) => a.startsWith('--seed='));
const seed = seedArg ? Number(seedArg.split('=')[1]) : 1337;

const game = new Game(seed);
const DT = 1 / 30;
const steps = Math.round((minutes * 60) / DT);
let firstContact = null;

for (let i = 0; i < steps; i++) {
  updateAI(game, DT, 0);
  game.update(DT);
  game.drainEvents();
  if (!firstContact && game.units.some((u) => u.team === 0 && u.x < 1400 && u.y > 900)) firstContact = game.time;
  if (game.state !== 'playing') break;
}
const mm = Math.floor(game.time / 60);
const ss = Math.floor(game.time % 60);
console.log(
  `seed=${seed} result=${game.state} t=${mm}m${String(ss).padStart(2, '0')}s ` +
  `| P pop=${game.players[0].pop}/${game.players[0].maxPop} units=${game.units.filter((u) => u.team === 0).length} b=${game.buildings.filter((b) => b.team === 0).length} ` +
  `| E pop=${game.players[1].pop}/${game.players[1].maxPop} units=${game.units.filter((u) => u.team === 1).length} b=${game.buildings.filter((b) => b.team === 1).length} ` +
  `| foodLeft=${game.resources.filter((r) => r.kind === 'berry').length}`,
);
