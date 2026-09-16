import { Game } from '../src/game.js';
import { TEAM, TILE, BUILDING_STATS } from '../src/config.js';
const g = new Game(1337);
const tc = g.buildings.find(b => b.team === 0 && b.type === 'towncenter');
g.players[0].res = { food: 5000, wood: 5000, gold: 5000 };
const vills = g.units.filter(u => u.team === 0);
// find a legal farm spot
let spot = null;
for (let r = -10; r <= 10 && !spot; r++) for (let c = -10; c <= 10 && !spot; c++) {
  if (g.canPlace('farm', 0, tc.tx + c, tc.ty + r).ok) spot = { tx: tc.tx + c, ty: tc.ty + r };
}
console.log('farm spot:', spot);
const res = g.placeBuilding('farm', 0, spot.tx, spot.ty, vills.slice(0, 2));
console.log('placed:', res.ok, res.reason || '');
const farm = res.building;
console.log('farm complete at placement?', farm.complete);
for (let i = 0; i < 60 * 30; i++) { g.update(1/30); g.drainEvents(); }
console.log('farm complete now?', farm.complete, 'progress', farm.progress, '/', farm.buildTime);
console.log('farm.foodNodeId =', farm.foodNodeId);
console.log('resource node exists =', farm.foodNodeId ? !!g.resourceById.get(farm.foodNodeId) : false);
console.log('farm resource nodes in world:', g.resources.filter(n => n.kind === 'farm').length);
// Can you click it to gather?
const c = farm.x, cyy = farm.y;
console.log('resourceAt(center):', !!g.resourceAt(c, cyy), 'buildingAt(center):', g.buildingAt(c, cyy)?.type);
console.log('villager tasks:', g.units.filter(u=>u.team===0&&u.type==='villager').map(u=>u.task));
