// Dump a late-match snapshot of both settlements.
import { Game } from '../src/game.js';
import { updateAI } from '../src/ai.js';
import { AGES } from '../src/config.js';

const minutes = Number(process.argv[2] || 12);
const seed = Number((process.argv.find(a => a.startsWith('--seed=')) || '--seed=1337').split('=')[1]);
const g = new Game(seed);
const bothAI = process.argv.includes('--both');

for (let i = 0; i < minutes * 60 * 30; i++) {
  if (bothAI) updateAI(g, 1 / 30, 0);
  g.update(1 / 30);
  g.drainEvents();
  if (g.state !== 'playing') break;
}

const mm = Math.floor(g.time / 60);
const ss = Math.floor(g.time % 60);
console.log(`seed=${seed} state=${g.state} t=${mm}m${String(ss).padStart(2, '0')}s  (bothAI=${bothAI})`);
for (const team of [0, 1]) {
  const p = g.players[team];
  const byType = {};
  for (const u of g.units) if (u.team === team) byType[u.type] = (byType[u.type] || 0) + 1;
  const bType = {};
  for (const b of g.buildings) if (b.team === team) bType[b.type + (b.complete ? '' : '(site)')] = (bType[b.type + (b.complete ? '' : '(site)')] || 0) + 1;
  const tc = g.buildings.find((b) => b.team === team && b.type === 'towncenter');
  console.log(
    `${team === 0 ? 'Riverwatch' : 'Ashfell  '} age=${AGES[p.age].name.padEnd(10)} pop=${p.pop}/${p.maxPop} ` +
    `res f${Math.round(p.res.food)} w${Math.round(p.res.wood)} g${Math.round(p.res.gold)} ` +
    `| units ${JSON.stringify(byType)} | buildings ${JSON.stringify(bType)}` +
    `| tcHp=${tc ? Math.round(tc.hp) : 'gone'}${tc && tc.research ? ' researching' : ''}`,
  );
}
const farms = g.resources.filter(n => n.kind === 'farm');
console.log(`farm food nodes: ${farms.length}, worked recently: ${farms.filter(f => g.time - (f.workedAt||-99) < 3).length}`);
console.log(`projectiles in flight: ${g.arrows.length}`);
