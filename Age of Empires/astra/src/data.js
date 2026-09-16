export const MAP_SIZE = 48;
export const TILE_W = 64;
export const TILE_H = 32;
export const AGES = {
  1: { name: "Hearth Age", numeral: "I", cost: {}, time: 0 },
  2: {
    name: "Banner Age",
    numeral: "II",
    cost: { food: 200, gold: 100 },
    time: 35,
  },
  3: {
    name: "Citadel Age",
    numeral: "III",
    cost: { food: 350, gold: 200 },
    time: 45,
  },
};
export const BUILDINGS = {
  town: {
    name: "Town centre",
    w: 3,
    h: 3,
    hp: 2000,
    cost: {},
    time: 0,
    pop: 10,
    description: "The heart of your settlement",
    trains: "villager",
  },
  house: {
    name: "House",
    w: 2,
    h: 2,
    hp: 450,
    cost: { wood: 65 },
    time: 15,
    pop: 5,
    description: "Room for five more settlers",
    key: "1",
  },
  farm: {
    name: "Farm",
    w: 2,
    h: 2,
    hp: 300,
    cost: { wood: 55 },
    time: 12,
    description: "A steady source of food",
    key: "2",
  },
  barracks: {
    name: "Barracks",
    w: 3,
    h: 2,
    hp: 1000,
    cost: { wood: 150 },
    time: 28,
    description: "Train soldiers to defend and conquer",
    trains: "soldier",
    key: "3",
  },
  tower: {
    name: "Watchtower",
    w: 2,
    h: 2,
    hp: 650,
    cost: { wood: 110, gold: 50 },
    time: 22,
    description:
      "Reveals distant land and fires arrows at enemies. Improves with each age.",
    key: "4",
  },
};
export const UNITS = {
  villager: {
    name: "Villager",
    hp: 55,
    speed: 2.05,
    cost: { food: 50 },
    time: 12,
    damage: 4,
    cooldown: 1.3,
    range: 1.1,
    sight: 3.1,
  },
  soldier: {
    name: "Spearman",
    hp: 115,
    speed: 2.3,
    cost: { food: 60, gold: 30 },
    time: 15,
    damage: 14,
    cooldown: 1.1,
    range: 1.3,
    sight: 5.4,
  },
};
export const RESOURCE_NAMES = { food: "Food", wood: "Wood", gold: "Gold" };
export const TEAM = {
  player: {
    main: "#387d73",
    light: "#69a99a",
    dark: "#224f48",
    name: "Hearthguard",
  },
  enemy: { main: "#b64e43", light: "#e78463", dark: "#723d34", name: "Redfen" },
};
export const costText = (cost) =>
  Object.entries(cost)
    .map(([r, n]) => `${n} ${r}`)
    .join(" · ");
export function seededRandom(seed) {
  return () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function project(x, y) {
  return { x: ((x - y) * TILE_W) / 2, y: ((x + y) * TILE_H) / 2 };
}
export function unproject(x, y) {
  return { x: x / TILE_W + y / TILE_H, y: y / TILE_H - x / TILE_W };
}
