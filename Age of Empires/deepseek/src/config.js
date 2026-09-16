// Central tuning values for Verdant Vale.
// Balance knobs live here so they are easy to adjust in one place.

export const TILE = 32;
export const COLS = 80;
export const ROWS = 60;
export const WORLD_W = COLS * TILE; // 2560
export const WORLD_H = ROWS * TILE; // 1920

export const TEAM = { PLAYER: 0, ENEMY: 1 };

// ------------------------------------------------------------------- ages

// Advancing costs resources and research time at the town centre, and unlocks
// buildings and units. Index 0 is the starting age.
export const AGES = [
  { name: 'Hearth Age', short: 'Hearth', blurb: 'Houses, farms, barracks, militia.' },
  { name: 'Keep Age', short: 'Keep', cost: { food: 350, gold: 120 }, time: 40, blurb: 'Unlocks watch towers and archers.' },
  { name: 'Crown Age', short: 'Crown', cost: { food: 700, gold: 350 }, time: 55, blurb: 'Unlocks knights and reinforces towers.' },
];
export const MAX_AGE = AGES.length - 1;

export const FORMATIONS = [
  { id: 'line', name: 'Line' },
  { id: 'box', name: 'Box' },
  { id: 'staggered', name: 'Staggered' },
  { id: 'flank', name: 'Flank' },
];

// ------------------------------------------------------------------ costs

export const COSTS = {
  villager: { food: 50 },
  soldier: { food: 55, gold: 20 },
  archer: { food: 40, gold: 30 },
  knight: { food: 80, gold: 60 },
  house: { wood: 25 },
  farm: { wood: 60 },
  barracks: { wood: 120 },
  watchtower: { wood: 60, gold: 20 },
};

export const TRAIN_TIME = { villager: 15, soldier: 18, archer: 18, knight: 22 };
export const BUILD_TIME = { house: 12, farm: 13, barracks: 20, watchtower: 18 };

export const POP_CAP_TC = 5;
export const POP_CAP_HOUSE = 5;
export const POP_CAP_MAX = 50;
export const BUILD_RADIUS_TILES = 8;

// ------------------------------------------------------------------ units

export const UNIT_STATS = {
  villager: {
    name: 'Villager',
    age: 0,
    hp: 45,
    speed: 68,
    radius: 8,
    dmg: 4,
    atkCd: 1.4,
    range: 15,
    aggro: 0,
    gather: 1.4,
    carry: 10,
    build: 1.2,
    sight: 5,
    role: 'Worker — gathers and builds',
  },
  soldier: {
    name: 'Soldier',
    age: 0,
    hp: 120,
    speed: 74,
    radius: 9,
    dmg: 11,
    atkCd: 1.2,
    range: 18,
    aggro: 190,
    gather: 0,
    carry: 0,
    build: 0,
    // Soldiers knock down structures faster than they cut through defenders.
    vsBuilding: 1.6,
    sight: 6,
    role: 'Melee — cheap and sturdy',
  },
  archer: {
    name: 'Archer',
    age: 1,
    hp: 80,
    speed: 76,
    radius: 8,
    dmg: 9,
    atkCd: 1.7,
    range: 138,
    aggro: 220,
    gather: 0,
    carry: 0,
    build: 0,
    ranged: true,
    projectileSpeed: 430,
    vsBuilding: 0.5,
    sight: 7,
    role: 'Ranged — soft, hits from afar',
  },
  knight: {
    name: 'Knight',
    age: 2,
    hp: 220,
    speed: 86,
    radius: 10,
    dmg: 18,
    atkCd: 1.3,
    range: 20,
    aggro: 210,
    gather: 0,
    carry: 0,
    build: 0,
    vsBuilding: 1.8,
    sight: 7,
    role: 'Heavy melee — expensive and strong',
  },
};

// -------------------------------------------------------------- buildings

export const BUILDING_STATS = {
  // The town centre shoots at raiders and researches new ages.
  towncenter: {
    name: 'Town Centre',
    age: 0,
    hp: 1300,
    w: 4,
    h: 4,
    attack: 10,
    atkCd: 2.0,
    range: 235,
    trains: ['villager'],
    research: true,
    sight: 11,
  },
  house: { name: 'House', age: 0, hp: 450, w: 2, h: 2, sight: 6 },
  farm: {
    name: 'Farm',
    age: 0,
    hp: 220,
    w: 3,
    h: 3,
    // Farms are a renewable food source: cost wood, then feed villagers forever.
    food: Infinity,
    sight: 4,
  },
  barracks: {
    name: 'Barracks',
    age: 0,
    hp: 900,
    w: 3,
    h: 3,
    trains: ['soldier', 'archer', 'knight'],
    sight: 7,
  },
  watchtower: {
    name: 'Watch Tower',
    age: 1,
    hp: 620,
    w: 2,
    h: 2,
    attack: 11,
    atkCd: 1.8,
    range: 210,
    sight: 13,
  },
};

export const DROP_OFF = 'towncenter';

export const RESOURCE_AMOUNT = { tree: 90, berry: 240, gold: 520 };
export const RESOURCE_LABEL = { tree: 'Wood', berry: 'Food', gold: 'Gold', farm: 'Food' };
export const RESOURCE_FROM = { tree: 'wood', berry: 'food', gold: 'gold', farm: 'food' };
export const RESOURCE_ICON = { wood: 'wood', food: 'food', gold: 'gold' };

export const START_RESOURCES = { food: 220, wood: 260, gold: 140 };

// ---------------------------------------------------------------- fog of war

// Unexplored ground is nearly black; explored-but-unwatched ground is a dim
// slate wash; anything currently in sight is drawn at full colour.
export const FOG = {
  unknown: [3, 6, 11],
  unknownAlpha: 246,
  explored: [10, 16, 26],
  exploredAlpha: 138,
  refresh: 0.22,
};

export const BASE_POS = [
  { x: 340, y: 1540 },
  { x: 1930, y: 430 },
];

export const TEAM_COLORS = [
  { main: '#4d7fd6', dark: '#2f5695', light: '#8fb4f0' },
  { main: '#c8483d', dark: '#8f2f28', light: '#ef8a7f' },
];

// ------------------------------------------------------------------ helpers

/**
 * Offsets that arrange `count` units around a target point.
 * Mirrors the classic line / box / staggered / flank choices.
 */
export function formationOffsets(formation, count, spacing = 27) {
  if (count <= 1) return [{ x: 0, y: 0 }];
  const out = [];
  if (formation === 'line') {
    for (let i = 0; i < count; i++) {
      out.push({ x: (i - (count - 1) / 2) * spacing * 1.3, y: 0 });
    }
  } else if (formation === 'staggered') {
    const cols = Math.ceil(Math.sqrt(count));
    const rows = Math.ceil(count / cols);
    for (let i = 0; i < count; i++) {
      const cx = i % cols;
      const cy = Math.floor(i / cols);
      out.push({
        x: (cx - (cols - 1) / 2) * spacing * 1.2,
        y: (cy - (rows - 1) / 2) * spacing + (cx % 2 ? spacing * 0.5 : 0),
      });
    }
  } else if (formation === 'flank') {
    for (let i = 0; i < count; i++) {
      const side = i % 2 === 0 ? -1 : 1;
      const idx = Math.floor(i / 2);
      out.push({
        x: side * (idx + 0.55) * spacing * 1.15,
        y: Math.abs(idx) * spacing * 0.3,
      });
    }
  } else {
    // box (default): compact square block
    const cols = Math.ceil(Math.sqrt(count));
    const rows = Math.ceil(count / cols);
    for (let i = 0; i < count; i++) {
      const cx = i % cols;
      const cy = Math.floor(i / cols);
      out.push({
        x: (cx - (cols - 1) / 2) * spacing,
        y: (cy - (rows - 1) / 2) * spacing,
      });
    }
  }
  return out;
}

export function ageUnlocks(age) {
  return {
    buildings: Object.keys(BUILDING_STATS).filter((k) => (BUILDING_STATS[k].age || 0) === age),
    units: Object.keys(UNIT_STATS).filter((k) => (UNIT_STATS[k].age || 0) === age),
  };
}
