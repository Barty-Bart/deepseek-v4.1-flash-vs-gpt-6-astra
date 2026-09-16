import {
  MAP_SIZE,
  TILE_W,
  TILE_H,
  BUILDINGS,
  TEAM,
  project,
  unproject,
  seededRandom,
} from "./data.js";

function poly(c, points, fill, stroke = null, width = 1) {
  c.beginPath();
  points.forEach((p, i) => (i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1])));
  c.closePath();
  if (fill) {
    c.fillStyle = fill;
    c.fill();
  }
  if (stroke) {
    c.strokeStyle = stroke;
    c.lineWidth = width;
    c.stroke();
  }
}
function ellipse(c, x, y, rx, ry, fill) {
  c.beginPath();
  c.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  c.fillStyle = fill;
  c.fill();
}
function line(c, x1, y1, x2, y2, color, width = 1) {
  c.beginPath();
  c.moveTo(x1, y1);
  c.lineTo(x2, y2);
  c.strokeStyle = color;
  c.lineWidth = width;
  c.stroke();
}
const p3 = (x, y, z = 0) => {
  const p = project(x, y);
  return [p.x, p.y - z];
};
function box(
  c,
  x,
  y,
  w,
  d,
  h,
  top = "#c6bb96",
  left = "#c0b48b",
  right = "#a29773",
  z = 0,
) {
  const a = p3(x, y, z),
    b = p3(x + w, y, z),
    cc = p3(x + w, y + d, z),
    d0 = p3(x, y + d, z),
    aa = p3(x, y, z + h),
    bb = p3(x + w, y, z + h),
    ccc = p3(x + w, y + d, z + h),
    dd = p3(x, y + d, z + h);
  poly(c, [d0, cc, ccc, dd], left, "#4e51342b");
  poly(c, [b, cc, ccc, bb], right, "#4e51342b");
  poly(c, [aa, bb, ccc, dd], top, "#4e51342b");
}
function roof(c, x, y, w, d, z, h, team) {
  const a = p3(x, y, z),
    b = p3(x + w, y, z),
    cc = p3(x + w, y + d, z),
    dd = p3(x, y + d, z),
    r1 = p3(x, y + d / 2, z + h),
    r2 = p3(x + w, y + d / 2, z + h);
  poly(c, [a, b, r2, r1], team.dark, "#263e38", 1);
  poly(c, [dd, cc, r2, r1], team.main, "#263e38", 1);
  poly(c, [b, cc, r2], "#c9ba8f", "#6a6546", 1);
  for (let i = 1; i < 5; i++) {
    const t = i / 5;
    line(
      c,
      dd[0] + (r1[0] - dd[0]) * t,
      dd[1] + (r1[1] - dd[1]) * t,
      cc[0] + (r2[0] - cc[0]) * t,
      cc[1] + (r2[1] - cc[1]) * t,
      team.light + "75",
      0.8,
    );
  }
  for (let i = 1; i < Math.ceil(w * 6); i++) {
    const t = i / Math.ceil(w * 6);
    line(
      c,
      dd[0] + (cc[0] - dd[0]) * t,
      dd[1] + (cc[1] - dd[1]) * t,
      r1[0] + (r2[0] - r1[0]) * t,
      r1[1] + (r2[1] - r1[1]) * t,
      team.dark + "55",
      0.55,
    );
  }
  line(c, r1[0] - 1, r1[1], r2[0] + 1, r2[1], team.light, 3);
}
function windowOn(c, x, y, z, side = "front") {
  const p = p3(x, y, z);
  poly(
    c,
    [
      [p[0] - 3, p[1] - 11],
      [p[0] + 3, p[1] - 8],
      [p[0] + 3, p[1]],
      [p[0] - 3, p[1] - 3],
    ],
    "#45564b",
    "#a89b70",
    1,
  );
  line(c, p[0], p[1] - 9, p[0], p[1] - 1, "#c6b786", 0.8);
}
function flag(c, x, y, z, team, t = 0) {
  const p = p3(x, y, z);
  line(c, p[0], p[1] + 24, p[0], p[1] - 11, "#7b6949", 2);
  ellipse(c, p[0], p[1] - 12, 2, 2, "#d9b46b");
  poly(
    c,
    [
      [p[0] + 1, p[1] - 10],
      [p[0] + 17, p[1] - 7 + Math.sin(t) * 2],
      [p[0] + 14, p[1] + 3 + Math.sin(t) * 2],
      [p[0] + 1, p[1] + 1],
    ],
    team.main,
    team.dark,
    0.6,
  );
  line(c, p[0] + 6, p[1] - 7, p[0] + 6, p[1], "#e4d6ad", 1);
  line(c, p[0] + 3, p[1] - 4, p[0] + 10, p[1] - 3, "#e4d6ad", 1);
}
function fence(c, x, y, length, axis = "x") {
  const end = axis === "x" ? p3(x + length, y, 10) : p3(x, y + length, 10),
    start = p3(x, y, 10);
  line(c, start[0], start[1], end[0], end[1], "#9d885d", 2);
  line(c, start[0], start[1] + 5, end[0], end[1] + 5, "#92794e", 1.6);
  for (let i = 0; i <= length * 3; i++) {
    const p = axis === "x" ? p3(x + i / 3, y) : p3(x, y + i / 3);
    line(c, p[0], p[1], p[0], p[1] - 14, "#ab9465", 2.3);
  }
}

export function drawBuilding(c, type, teamName = "player", time = 0, age = 1) {
  const team = TEAM[teamName],
    d = BUILDINGS[type];
  ellipse(c, 8, (d.w + d.h) * 8 + 9, d.w * 32 + 12, d.h * 13, "#243c3034");
  if (type === "farm") {
    box(c, 0.04, 0.04, 1.92, 1.92, 3, "#816943", "#8c734b", "#78613e");
    const rng = seededRandom(882);
    for (let row = 0; row < 7; row++) {
      const yy = 0.18 + row * 0.25;
      const a = p3(0.14, yy, 4),
        b = p3(1.84, yy, 4);
      line(c, a[0], a[1], b[0], b[1], "#554a31", 3);
      for (let i = 0; i < 12; i++) {
        const xx = 0.2 + i * 0.14,
          p = p3(xx, yy, 4),
          h = 5 + rng() * 6;
        line(c, p[0], p[1], p[0] + 1, p[1] - h, "#bca85b", 1);
        line(c, p[0], p[1] - h + 3, p[0] - 2, p[1] - h, "#dfc173", 1.7);
      }
    }
    fence(c, 0, 0, 2);
    fence(c, 0, 0, 2, "y");
    const a = p3(1.8, 0.2, 0);
    box(c, 1.72, 0.12, 0.25, 0.25, 10, "#a58d5b", "#927b4a", "#7c6845");
    return;
  }
  box(c, 0.05, 0.05, d.w - 0.1, d.h - 0.1, 4, "#b2ab82", "#9c9674", "#89876a");
  if (type === "tower") {
    const stone = age > 1;
    box(
      c,
      0.34,
      0.34,
      1.32,
      1.32,
      76,
      stone ? "#d7cfad" : "#baa374",
      stone ? "#c7bd98" : "#a18b5f",
      stone ? "#a59f82" : "#806f4e",
      4,
    );
    if (stone) {
      for (let z = 12; z < 76; z += 10) {
        const a = p3(0.34, 1.67, z),
          b = p3(1.67, 1.67, z),
          d = p3(1.67, 0.34, z);
        line(c, a[0], a[1], b[0], b[1], "#a49b7c", 0.8);
        line(c, b[0], b[1], d[0], d[1], "#888d73", 0.8);
      }
    } else {
      for (const x of [0.36, 1, 1.64]) {
        const p = p3(x, 1.68, 4);
        line(c, p[0], p[1], p[0], p[1] - 75, "#695f43", 3);
      }
      for (let z = 14; z < 70; z += 22) {
        const a = p3(0.4, 1.68, z),
          b = p3(1.61, 1.68, z + 20);
        line(c, a[0], a[1], b[0], b[1], "#d1b585", 2.5);
      }
    }
    const door = p3(1, 1.68, 4);
    poly(
      c,
      [
        [door[0] - 5, door[1] - 2],
        [door[0] - 5, door[1] - 20],
        [door[0] + 5, door[1] - 15],
        [door[0] + 5, door[1] + 3],
      ],
      "#4a5140",
    );
    windowOn(c, 1.67, 0.98, 48);
    windowOn(c, 0.88, 1.68, 56);
    box(c, 0.16, 0.16, 1.68, 1.68, 6, "#d3c39a", "#b7a47a", "#9d936f", 78);
    if (age === 3) {
      box(c, 0.2, 0.2, 1.6, 1.6, 12, "#c9c5a4", "#c2b896", "#aaa788", 84);
      for (const [x, y] of [
        [0.2, 0.2],
        [0.85, 0.2],
        [1.5, 0.2],
        [0.2, 0.85],
        [0.2, 1.5],
        [0.85, 1.5],
        [1.5, 1.5],
        [1.5, 0.85],
      ])
        box(c, x, y, 0.3, 0.3, 9, "#ded3ac", "#c4b995", "#aaa180", 96);
      flag(c, 1, 1, 128, team, time);
    } else {
      box(
        c,
        0.36,
        0.36,
        1.28,
        1.28,
        16,
        "#dacba4",
        stone ? "#c7b992" : "#9b895e",
        stone ? "#aaa080" : "#7e7453",
        84,
      );
      for (const x of [0.55, 1.16]) windowOn(c, x, 1.65, 94);
      roof(c, 0.08, 0.08, 1.84, 1.84, 100, 19, team);
      flag(c, 1, 0.8, 132, team, time);
    }
    const banner = p3(1.68, 1.05, 67);
    poly(
      c,
      [
        [banner[0] - 4, banner[1]],
        [banner[0] + 4, banner[1] - 4],
        [banner[0] + 4, banner[1] + 14],
        [banner[0], banner[1] + 20],
        [banner[0] - 4, banner[1] + 18],
      ],
      team.main,
      "#d5bd83",
      1,
    );
    return;
  }
  if (type === "town") {
    // A stone hall, a timber arcade and a small watchtower.
    box(c, 0.54, 0.35, 1.92, 1.68, 41, "#e0d5b4", "#d4c7a1", "#b7ab8a", 4);
    const left = p3(0.55, 2.03, 4),
      right = p3(2.46, 2.03, 4);
    line(c, left[0], left[1] - 14, right[0], right[1] - 14, "#aa9c78", 1);
    for (let i = 0; i < 5; i++) {
      const p = p3(0.58 + i * 0.38, 2.035, 5);
      line(c, p[0], p[1], p[0], p[1] - 34, "#8d805d", 1.7);
    }
    roof(c, 0.36, 0.2, 2.3, 1.98, 45, 31, team);
    box(c, 0.4, 1.95, 2.15, 0.62, 16, "#b9a880", "#c5b58b", "#a4946e", 3);
    // Dark arcade arches, pale posts and a weathered awning.
    for (let i = 0; i < 4; i++) {
      const x = 0.56 + i * 0.5,
        p = p3(x, 2.58, 4);
      poly(
        c,
        [
          [p[0], p[1]],
          [p[0], p[1] - 13],
          [p[0] + 5, p[1] - 16],
          [p[0] + 10, p[1] - 10],
          [p[0] + 10, p[1] + 5],
        ],
        "#4c5a48",
      );
    }
    roof(c, 0.29, 1.91, 2.4, 0.86, 22, 7, {
      ...team,
      main: "#b5aa79",
      dark: "#8a895f",
      light: "#dbcd99",
    });
    box(c, 2.08, 0.18, 0.68, 0.77, 57, "#e4d7b2", "#cfc39f", "#b4ab8b", 4);
    windowOn(c, 2.78, 0.56, 40);
    windowOn(c, 2.42, 0.96, 44);
    roof(c, 1.99, 0.08, 0.87, 0.97, 61, 22, team);
    flag(c, 2.4, 0.53, 92, team, time);
    for (let i = 0; i < 3; i++) windowOn(c, 2.47, 0.58 + i * 0.5, 26);
    // Steps and a small noticeboard.
    box(c, 1.02, 2.64, 1.1, 0.29, 3, "#d3c5a0", "#b8ac87", "#a99d7d");
    box(c, 1.08, 2.56, 0.99, 0.2, 6, "#d8cda9", "#c2b792", "#b0a684");
    const p = p3(0.24, 2.68, 0);
    line(c, p[0], p[1], p[0], p[1] - 18, "#87724d", 2);
    poly(
      c,
      [
        [p[0] - 6, p[1] - 23],
        [p[0] + 6, p[1] - 19],
        [p[0] + 6, p[1] - 9],
        [p[0] - 6, p[1] - 13],
      ],
      "#c9b684",
      "#8d7957",
    );
    box(c, 2.66, 2.13, 0.25, 0.27, 9, "#b59b64", "#937e51", "#806a46");
    if (age >= 2) {
      flag(c, 0.4, 2.68, 44, team, time);
      flag(c, 2.55, 2.68, 44, team, time);
    }
    if (age === 3) {
      for (const x of [0.1, 2.65]) {
        box(c, x, 2.58, 0.26, 0.28, 20, "#ded1a5", "#c6ba94", "#aaa285");
        box(
          c,
          x - 0.04,
          2.54,
          0.34,
          0.36,
          4,
          "#e8dcaf",
          "#cabf98",
          "#b4ad8b",
          20,
        );
      }
    }
  }
  if (type === "house") {
    box(c, 0.26, 0.35, 1.36, 1.19, 29, "#e3d3ad", "#d4c29a", "#b7a580", 4);
    const p = p3(0.89, 1.55, 4);
    poly(
      c,
      [
        [p[0] - 6, p[1] - 3],
        [p[0] - 6, p[1] - 20],
        [p[0] + 5, p[1] - 15],
        [p[0] + 5, p[1] + 2],
      ],
      "#615e44",
      "#a4916b",
    );
    for (const x of [0.29, 0.85, 1.6]) {
      const a = p3(x, 1.55, 5);
      line(c, a[0], a[1], a[0], a[1] - 27, "#806e4d", 2);
    }
    const a = p3(0.28, 1.55, 20),
      b = p3(1.62, 1.55, 20);
    line(c, a[0], a[1], b[0], b[1], "#8c7956", 2);
    windowOn(c, 1.63, 0.7, 20);
    roof(c, 0.12, 0.18, 1.66, 1.53, 34, 25, team);
    box(c, 0.48, 0.45, 0.23, 0.27, 25, "#b5aa86", "#a59a77", "#887e62", 43);
    fence(c, 0.08, 1.87, 0.63);
    fence(c, 1.68, 0.46, 1.38, "y");
    const bush = p3(0.35, 1.76);
    ellipse(c, bush[0], bush[1] - 3, 7, 5, "#6f8b4c");
  }
  if (type === "barracks") {
    box(c, 0.26, 0.3, 2.42, 1.27, 34, "#d7c9a7", "#c3b48b", "#ab9d7c", 4);
    roof(c, 0.1, 0.1, 2.74, 1.58, 39, 27, team);
    const p = p3(1.5, 1.58, 4);
    poly(
      c,
      [
        [p[0] - 11, p[1] - 5],
        [p[0] - 11, p[1] - 26],
        [p[0] + 1, p[1] - 28],
        [p[0] + 13, p[1] - 17],
        [p[0] + 13, p[1] + 7],
      ],
      "#485444",
      "#a1916e",
      1.5,
    );
    line(c, p[0] + 1, p[1] - 27, p[0] + 1, p[1] + 1, "#736548", 1.5);
    for (const x of [0.32, 0.94, 2.6]) {
      const a = p3(x, 1.58, 5);
      line(c, a[0], a[1], a[0], a[1] - 30, "#948560", 2.2);
    }
    windowOn(c, 2.7, 0.82, 25);
    flag(c, 0.52, 1.67, 58, team, time);
    const a = p3(2.76, 1.84);
    line(c, a[0] - 9, a[1], a[0] + 3, a[1] - 27, "#746443", 2);
    line(c, a[0] + 6, a[1] + 5, a[0] - 6, a[1] - 28, "#746443", 2);
    line(c, a[0] - 10, a[1] - 11, a[0] + 8, a[1] - 6, "#a18955", 2);
    poly(
      c,
      [
        [a[0] + 2, a[1] - 31],
        [a[0] + 6, a[1] - 26],
        [a[0] + 1, a[1] - 23],
      ],
      "#d6d6bd",
    );
    const q = p3(0.35, 1.9);
    ellipse(c, q[0], q[1] - 5, 6, 7, team.main);
    line(c, q[0], q[1] - 10, q[0], q[1], team.light, 2);
  }
}

export function drawUnit(c, u, time = 0, portrait = false) {
  const team = TEAM[u.team],
    moving = u.path?.length > 0,
    working = ["gather", "build", "attack"].includes(u.order?.kind),
    anim = u.anim || time;
  const stride = moving ? Math.sin(anim) * 2 : 0;
  const facing = Math.cos((u.angle || 0) - Math.PI / 4) > 0 ? 1 : -1;
  ellipse(c, 1, 1, 8, 3.5, "#273a344c");
  line(c, -2, -7, -3 + stride, 0, "#575a42", 3);
  line(c, 2, -7, 3 - stride, 0, "#494f3d", 3);
  if (u.type === "villager") {
    poly(
      c,
      [
        [-5, -19],
        [4, -19],
        [6, -7],
        [-5, -7],
      ],
      team.main,
      "#354b38",
      0.6,
    );
    poly(
      c,
      [
        [-2, -18],
        [3, -18],
        [4, -6],
        [-1, -6],
      ],
      "#d6cba4",
    );
    line(c, -5, -16, -7, -9 + (working ? Math.sin(anim) * 2 : 0), "#c8b38a", 3);
    line(c, 5, -16, 7, -10, "#c8b38a", 3);
    ellipse(c, 0, -23, 4.5, 5, "#dec39a");
    poly(
      c,
      [
        [-5, -23],
        [-4, -28],
        [2, -29],
        [5, -25],
        [4, -23],
      ],
      "#746147",
    );
    line(c, -5, -26, 5, -24, "#a58c5e", 2);
    if (u.carry > 0) {
      ellipse(
        c,
        -5,
        -13,
        4,
        5,
        u.carryType === "gold"
          ? "#c5a14e"
          : u.carryType === "food"
            ? "#b5a26a"
            : "#94744c",
      );
    }
    if (working) {
      const swing = Math.sin(anim) * 3;
      line(c, 7, -11, 11 + swing, -22, "#a68a59", 1.5);
      if (u.order.kind === "gather" && u.order.resourceType === "wood")
        poly(
          c,
          [
            [8 + swing, -23],
            [15 + swing, -22],
            [15 + swing, -18],
            [9 + swing, -19],
          ],
          "#bbc4ae",
        );
      else line(c, 8 + swing, -22, 15 + swing, -23, "#c1c5aa", 2);
    }
  } else {
    poly(
      c,
      [
        [-5, -21],
        [4, -21],
        [6, -7],
        [-6, -7],
      ],
      team.main,
      "#3e5146",
      0.8,
    );
    poly(
      c,
      [
        [-5, -21],
        [4, -21],
        [4, -15],
        [-5, -15],
      ],
      "#acb8ac",
    );
    line(c, 0, -18, 0, -9, "#d1ca9f", 1.2);
    ellipse(c, 0, -24, 4.2, 4.5, "#d7bb8e");
    ellipse(c, -0.4, -27, 5, 3.7, "#c0c9be");
    poly(
      c,
      [
        [-5, -27],
        [4, -27],
        [5, -24],
        [-5, -24],
      ],
      "#8b9f96",
    );
    line(c, -4, -29, 2, -30, "#e0e1ca", 1.5);
    const thrust = u.cooldown > 0.8 ? 6 : 0;
    line(c, 7, -8, 10 + thrust, -36, "#ac9564", 1.6);
    poly(
      c,
      [
        [10 + thrust, -42],
        [7 + thrust, -35],
        [12 + thrust, -34],
      ],
      "#d6dfcf",
      "#849c92",
      0.5,
    );
    line(c, 4, -19, 8, -15, "#b9b99b", 3);
    poly(
      c,
      [
        [-9, -20],
        [-2, -18],
        [-2, -10],
        [-6, -6],
        [-10, -12],
      ],
      team.dark,
      "#dac795",
      1.2,
    );
    line(c, -6, -18, -6, -10, "#cdbb83", 1.2);
    line(c, -9, -15, -3, -13, "#cdbb83", 1.2);
  }
  if (u.hitFlash > 0) {
    c.globalAlpha = 0.7;
    ellipse(c, 0, -15, 8, 13, "#f7e5c6");
    c.globalAlpha = 1;
  }
}

export class Renderer {
  constructor(canvas, mini, game) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d", { alpha: false });
    this.mini = mini;
    this.mc = mini.getContext("2d");
    this.game = game;
    this.camera = { x: 0, y: 0, zoom: 1.16 };
    this.selected = new Set();
    this.hover = null;
    this.placement = null;
    this.selectionBox = null;
    this.fogCanvas = null;
    this.fogRevision = -1;
    this.fogOwner = null;
    this.commandMarkers = [];
    this.sprites = new Map();
    this.ground = this.makeGround();
    this.resize();
    this.home();
    window.addEventListener("resize", () => this.resize());
  }
  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = this.width * this.dpr;
    this.canvas.height = this.height * this.dpr;
  }
  home() {
    const t = this.game.town("player");
    if (t) {
      const p = project(t.x + 1.5, t.y + 2);
      this.camera.x = p.x;
      this.camera.y = p.y + 45;
    }
  }
  toScreen(x, y) {
    const p = project(x, y);
    return {
      x: (p.x - this.camera.x) * this.camera.zoom + this.width / 2,
      y: (p.y - this.camera.y) * this.camera.zoom + (this.height - 125) / 2,
    };
  }
  toWorld(x, y) {
    return unproject(
      (x - this.width / 2) / this.camera.zoom + this.camera.x,
      (y - (this.height - 125) / 2) / this.camera.zoom + this.camera.y,
    );
  }
  zoomAt(amount, x = this.width / 2, y = (this.height - 125) / 2) {
    const before = this.toWorld(x, y);
    this.camera.zoom = Math.max(0.55, Math.min(2.2, this.camera.zoom * amount));
    const after = this.toWorld(x, y),
      a = project(before.x, before.y),
      b = project(after.x, after.y);
    this.camera.x += a.x - b.x;
    this.camera.y += a.y - b.y;
    this.clampCamera();
  }
  clampCamera() {
    const w = unproject(this.camera.x, this.camera.y);
    w.x = Math.max(2, Math.min(MAP_SIZE - 2, w.x));
    w.y = Math.max(2, Math.min(MAP_SIZE - 2, w.y));
    const p = project(w.x, w.y);
    this.camera.x = p.x;
    this.camera.y = p.y;
  }
  makeGround() {
    const c = document.createElement("canvas");
    c.width = MAP_SIZE * TILE_W + 100;
    c.height = MAP_SIZE * TILE_H + 140;
    const ctx = c.getContext("2d");
    this.groundOffset = { x: (MAP_SIZE * TILE_W) / 2 + 50, y: 40 };
    ctx.translate(this.groundOffset.x, this.groundOffset.y);
    const rand = seededRandom(6293);
    const grass = [
      "#829365",
      "#829466",
      "#87986a",
      "#8a996c",
      "#86996a",
      "#7e9263",
      "#8b9b6e",
    ];
    // Cut earth along the southern map edges.
    poly(
      ctx,
      [
        p3(0, MAP_SIZE),
        p3(MAP_SIZE, MAP_SIZE),
        p3(MAP_SIZE, MAP_SIZE, -23),
        p3(0, MAP_SIZE, -23),
      ],
      "#635e45",
    );
    poly(
      ctx,
      [
        p3(MAP_SIZE, 0),
        p3(MAP_SIZE, MAP_SIZE),
        p3(MAP_SIZE, MAP_SIZE, -23),
        p3(MAP_SIZE, 0, -23),
      ],
      "#55563f",
    );
    for (let sum = 0; sum < MAP_SIZE * 2; sum++)
      for (let x = 0; x < MAP_SIZE; x++) {
        const y = sum - x;
        if (y < 0 || y >= MAP_SIZE) continue;
        const p = project(x, y),
          water = this.game.terrain[y * MAP_SIZE + x];
        let color = grass[Math.floor(rand() * grass.length)];
        const road =
          Math.abs((x - 14) * 0.92 + (y - 29)) < 1.5 && x > 12 && x < 35;
        const square =
          (x > 10 && x < 18 && y > 28 && y < 36) ||
          (x > 31 && x < 38 && y > 8 && y < 15);
        if (road || square)
          color = ["#a5a17b", "#aaa580", "#a4a07a", "#aea780"][
            Math.floor(rand() * 4)
          ];
        if (water)
          color = ["#689794", "#689b98", "#6c9e9b", "#62938f"][
            Math.floor(rand() * 4)
          ];
        poly(
          ctx,
          [
            [p.x, p.y],
            [p.x + 32, p.y + 16],
            [p.x, p.y + 32],
            [p.x - 32, p.y + 16],
          ],
          color,
        );
        if (water) {
          for (let i = 0; i < 2; i++) {
            const xx = p.x + (rand() - 0.5) * 29,
              yy = p.y + 10 + rand() * 12;
            line(ctx, xx, yy, xx + 5 + rand() * 8, yy, "#a5c2a361", 0.7);
          }
          continue;
        }
        for (let i = 0; i < (road || square ? 2 : 4); i++) {
          const dx = rand(),
            dy = rand(),
            a = project(x + dx, y + dy);
          if (rand() < 0.18) {
            ellipse(ctx, a.x, a.y, 1.5, 0.8, "#b5b28b88");
          } else {
            const h = 1.5 + rand() * 2;
            line(ctx, a.x, a.y, a.x - 0.7, a.y - h, "#627e494d", 0.65);
            line(ctx, a.x, a.y, a.x + 1.4, a.y - h * 0.8, "#bfd09438", 0.7);
          }
        }
        if (!road && !square && rand() < 0.07) {
          const a = project(x + 0.5, y + 0.5);
          for (let i = 0; i < 3; i++)
            ellipse(
              ctx,
              a.x + (rand() - 0.5) * 13,
              a.y + (rand() - 0.5) * 7,
              0.9,
              0.7,
              "#d6cd9a",
            );
        }
      }
    // Reeds give the little lakes a soft, irregular shore.
    for (let y = 1; y < MAP_SIZE - 1; y++)
      for (let x = 1; x < MAP_SIZE - 1; x++)
        if (
          !this.game.terrain[y * MAP_SIZE + x] &&
          [
            [1, 0],
            [-1, 0],
            [0, 1],
            [0, -1],
          ].some(([dx, dy]) => this.game.terrain[(y + dy) * MAP_SIZE + x + dx])
        ) {
          const p = project(x + 0.5, y + 0.5);
          for (let i = 0; i < 6; i++) {
            const xx = p.x + (rand() - 0.5) * 24,
              yy = p.y + (rand() - 0.5) * 10;
            line(
              ctx,
              xx,
              yy,
              xx + (rand() - 0.5) * 4,
              yy - 4 - rand() * 8,
              "#6e8052",
              1,
            );
          }
        }
    return c;
  }
  resourceSprite(r) {
    const cacheKey = `${r.type}-${r.variant}`;
    if (this.sprites.has(cacheKey)) return this.sprites.get(cacheKey);
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 150;
    const c = canvas.getContext("2d");
    c.translate(64, 116);
    const rand = seededRandom(381 + r.variant * 71);
    if (r.type === "wood") {
      const h = 48 + r.variant * 4;
      ellipse(c, 8, 3, 24, 10, "#2e493633");
      poly(
        c,
        [
          [-4, 2],
          [-3, -h * 0.6],
          [3, -h * 0.62],
          [4, 2],
        ],
        "#716546",
      );
      line(c, -1, 0, -1, -h * 0.6, "#a38a5c", 1.4);
      if (r.variant === 0 || r.variant === 3) {
        for (let i = 0; i < 3; i++) {
          const yy = -h * 0.34 - i * h * 0.26,
            w = 24 - i * 5;
          poly(
            c,
            [
              [0, yy - 28],
              [-w, yy + 9],
              [-7, yy + 6],
              [0, yy + 12],
              [w, yy + 5],
            ],
            ["#4c6f48", "#547b4e", "#638759"][i],
          );
          poly(
            c,
            [
              [0, yy - 28],
              [-w, yy + 9],
              [-7, yy + 6],
              [0, yy + 12],
            ],
            ["#3e6241", "#466e46", "#517950"][i],
          );
        }
      } else {
        for (const [x, y, rad] of [
          [-14, -h * 0.64, 20],
          [15, -h * 0.68, 19],
          [0, -h, 24],
          [-11, -h * 0.9, 19],
          [9, -h * 0.93, 20],
        ]) {
          const colors = [
            "#496e47",
            "#5b7e4d",
            "#678a51",
            "#739556",
            "#64874d",
          ];
          const pts = [];
          for (let i = 0; i < 9; i++) {
            const a = (i / 9) * Math.PI * 2,
              rr = rad * (0.79 + rand() * 0.24);
            pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr * 0.83]);
          }
          poly(c, pts, colors[Math.floor(rand() * colors.length)]);
          for (let i = 0; i < 8; i++) {
            const px = x + (rand() - 0.5) * rad * 1.2,
              py = y + (rand() - 0.5) * rad;
            poly(
              c,
              [
                [px - 3, py],
                [px, py - 2],
                [px + 5, py],
                [px + 1, py + 2],
              ],
              "#a4b76a33",
            );
          }
        }
      }
      line(c, -3, 0, -9, 3, "#766b44", 1.2);
      line(c, 3, 0, 8, 2, "#796b45", 1.3);
    } else if (r.type === "food") {
      ellipse(c, 2, 2, 23, 9, "#52684044");
      for (const [x, y, sz] of [
        [-10, -6, 12],
        [10, -9, 13],
        [0, -15, 14],
      ]) {
        ellipse(c, x, y, sz, sz * 0.7, "#557742");
        ellipse(c, x - 2, y - 3, sz * 0.8, sz * 0.5, "#6c8b4b");
      }
      for (let i = 0; i < 17; i++) {
        const x = (rand() - 0.5) * 31,
          y = -4 - rand() * 17;
        ellipse(c, x, y, 1.8, 1.6, i % 3 === 0 ? "#d89b65" : "#b16458");
        ellipse(c, x - 0.5, y - 0.5, 0.5, 0.5, "#efbe84");
      }
    } else {
      ellipse(c, 1, 3, 23, 10, "#52604444");
      for (const [x, y, w, h] of [
        [-12, -2, 13, 17],
        [9, -5, 16, 23],
        [0, 6, 14, 15],
      ]) {
        poly(
          c,
          [
            [x - w, y],
            [x - w * 0.6, y - h * 0.8],
            [x + w * 0.25, y - h],
            [x + w, y - h * 0.35],
            [x + w * 0.8, y + 4],
            [x, y + 7],
          ],
          "#8c8e71",
        );
        poly(
          c,
          [
            [x - w, y],
            [x - w * 0.6, y - h * 0.8],
            [x + w * 0.25, y - h],
            [x + 2, y - 5],
          ],
          "#b5b390",
        );
        poly(
          c,
          [
            [x + 2, y - 5],
            [x + w * 0.25, y - h],
            [x + w, y - h * 0.35],
            [x + w * 0.8, y + 4],
          ],
          "#7c8167",
        );
        poly(
          c,
          [
            [x - 6, y - 5],
            [x - 3, y - 12],
            [x + 4, y - 14],
            [x + 7, y - 8],
            [x + 1, y - 4],
          ],
          "#d0ad5c",
        );
        poly(
          c,
          [
            [x - 3, y - 12],
            [x + 4, y - 14],
            [x + 1, y - 8],
          ],
          "#f1d58b",
        );
      }
    }
    this.sprites.set(cacheKey, canvas);
    return canvas;
  }
  buildingSprite(b) {
    const key = `b-${b.type}-${b.team}-${b.age || 1}`;
    if (this.sprites.has(key)) return this.sprites.get(key);
    const can = document.createElement("canvas");
    can.width = 300;
    can.height = 230;
    const c = can.getContext("2d");
    c.translate(145, 135);
    drawBuilding(c, b.type, b.team, 0, b.age || 1);
    this.sprites.set(key, can);
    return can;
  }
  draw(dt, time) {
    const c = this.ctx,
      z = this.camera.zoom;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.fillStyle = "#203735";
    c.fillRect(0, 0, this.width, this.height);
    c.translate(this.width / 2, (this.height - 125) / 2);
    c.scale(z, z);
    c.translate(-this.camera.x, -this.camera.y);
    c.drawImage(this.ground, -this.groundOffset.x, -this.groundOffset.y);
    const visible = (x, y, margin = 180) => {
      const p = this.toScreen(x, y);
      return (
        p.x > -margin * z &&
        p.x < this.width + margin * z &&
        p.y > -margin * z &&
        p.y < this.height + margin * z
      );
    };
    // Commands and selected footprints are painted underneath the scene.
    for (const b of this.game.buildings)
      if (
        this.game.fog.canSee(b) &&
        (this.selected.has(b.id) || this.hover?.id === b.id)
      )
        this.drawFootprint(
          c,
          b,
          this.selected.has(b.id) ? "#a9d5b8" : "#f0df9a",
          0.9,
        );
    for (const u of this.game.units)
      if (this.selected.has(u.id) && this.game.fog.canSee(u)) {
        const p = project(u.x, u.y);
        c.beginPath();
        c.ellipse(p.x, p.y + 1, 12, 6, 0, 0, Math.PI * 2);
        c.strokeStyle = u.team === "player" ? "#d3ebad" : "#efae91";
        c.lineWidth = 1.5;
        c.stroke();
        c.fillStyle = "#c9e89c21";
        c.fill();
        if (u.path.length) {
          c.save();
          c.setLineDash([3, 5]);
          c.strokeStyle = "#dfedbd4d";
          c.lineWidth = 0.8;
          c.beginPath();
          c.moveTo(p.x, p.y);
          for (const n of u.path) {
            const q = project(n.x, n.y);
            c.lineTo(q.x, q.y);
          }
          c.stroke();
          c.restore();
        }
      }
    for (const ef of this.game.effects)
      if (
        this.game.fog.state(ef.x, ef.y) === 2 &&
        (ef.kind === "rubble" || ef.kind === "fallen")
      ) {
        const p = project(ef.x, ef.y);
        c.save();
        c.translate(p.x, p.y);
        if (ef.kind === "rubble") {
          ellipse(c, 0, 0, 38, 18, "#695f4844");
          for (let i = 0; i < 9; i++)
            poly(
              c,
              [
                [i * 7 - 31, Math.sin(i) * 11],
                [i * 7 - 35, Math.sin(i) * 11 - 6],
                [i * 7 - 24, Math.sin(i) * 11 - 7],
                [i * 7 - 21, Math.sin(i) * 11 + 3],
              ],
              i % 2 ? "#a19b79" : "#86886c",
            );
        } else {
          c.globalAlpha = Math.min(1, ef.life / 3);
          line(c, -5, 1, 6, -2, TEAM[ef.team].dark, 4);
          line(c, -1, 5, 4, -5, "#9d9f87", 1);
        }
        c.restore();
      }
    const entities = this.game.fog
      .knownEntities()
      .filter((e) => visible(e.x, e.y))
      .sort(
        (a, b) =>
          a.x +
          a.y +
          (a.w ? a.w / 2 + a.h / 2 : 0) -
          (b.x + b.y + (b.w ? b.w / 2 + b.h / 2 : 0)),
      );
    for (const e of entities) {
      const p = project(e.x, e.y);
      c.save();
      c.translate(p.x, p.y);
      if (e.kind === "resource") {
        const cp = project(0.5, 0.5);
        if (this.hover?.id === e.id) {
          ellipse(c, cp.x, cp.y + 1, 27, 12, "#f9e9a250");
        }
        const s = this.resourceSprite(e);
        c.drawImage(s, cp.x - 64, cp.y - 116);
      }
      if (e.kind === "building") {
        if (e.complete) c.drawImage(this.buildingSprite(e), -145, -135);
        else {
          c.globalAlpha = 0.2 + e.progress * 0.6;
          c.drawImage(this.buildingSprite(e), -145, -135);
          c.globalAlpha = 1;
          box(c, 0, 0, e.w, e.h, 3, "#a49b72", "#8a825c", "#7d7954");
          for (let i = 0; i < e.w; i++)
            box(
              c,
              0.1 + i,
              0.15,
              0.6,
              0.25,
              6,
              "#ad9867",
              "#8a784d",
              "#796943",
            );
          fence(c, 0, e.h, e.w);
          fence(c, e.w, 0, e.h, "y");
          for (const [xx, yy] of [
            [0, 0],
            [e.w, 0],
            [e.w, e.h],
            [0, e.h],
          ]) {
            const a = p3(xx, yy);
            line(c, a[0], a[1], a[0], a[1] - 33, "#9b8154", 2);
          }
          const a = p3(0, e.h, 30),
            b = p3(e.w, e.h, 30);
          line(c, a[0], a[1], b[0], b[1], "#bda574", 2);
        }
        if (e.hitFlash > 0) {
          c.globalAlpha = 0.22;
          this.drawFootprint(c, { ...e, x: 0, y: 0 }, "#ffe2b2", 1);
          c.globalAlpha = 1;
        }
      }
      if (e.kind === "unit") drawUnit(c, e, time);
      c.restore();
    }
    // Selected units stay readable when behind trees or roofs.
    for (const u of this.game.units)
      if (
        this.selected.has(u.id) &&
        this.game.fog.canSee(u) &&
        visible(u.x, u.y)
      ) {
        const p = project(u.x, u.y);
        c.save();
        c.translate(p.x, p.y);
        c.globalAlpha = 0.75;
        drawUnit(c, u, time);
        c.restore();
      }
    for (const e of [...this.game.units, ...this.game.buildings])
      if (
        this.game.fog.canSee(e) &&
        visible(e.x, e.y) &&
        (this.selected.has(e.id) ||
          this.hover?.id === e.id ||
          e.hp < e.maxHp ||
          (!e.complete && e.kind === "building"))
      )
        this.healthBar(c, e);
    this.drawArrows(c);
    this.drawFog(c);
    for (const b of this.game.buildings)
      if (
        b.type === "tower" &&
        b.team === "player" &&
        b.complete &&
        this.selected.has(b.id)
      ) {
        const p = project(b.x + b.w / 2, b.y + b.h / 2),
          range = this.game.towerStats(b).range;
        c.save();
        c.setLineDash([5, 7]);
        c.strokeStyle = "#e6cc8ba0";
        c.lineWidth = 1.2;
        c.beginPath();
        c.ellipse(p.x, p.y, range * 45.255, range * 22.627, 0, 0, Math.PI * 2);
        c.stroke();
        c.restore();
      }
    for (const m of this.commandMarkers) {
      m.life -= dt;
      const p = project(m.x, m.y);
      c.save();
      c.globalAlpha = m.life;
      c.strokeStyle = m.attack ? "#f1a080" : "#eee6b2";
      c.lineWidth = 1.5;
      const r = 12 + (1 - m.life) * 15;
      c.beginPath();
      c.ellipse(p.x, p.y, r, r / 2, 0, 0, Math.PI * 2);
      c.stroke();
      line(c, p.x - 4, p.y, p.x + 4, p.y, c.strokeStyle, 1);
      line(c, p.x, p.y - 2, p.x, p.y + 2, c.strokeStyle, 1);
      c.restore();
    }
    this.commandMarkers = this.commandMarkers.filter((m) => m.life > 0);
    for (const ef of this.game.effects) {
      if (this.game.fog.state(ef.x, ef.y) !== 2) continue;
      const p = project(ef.x, ef.y);
      if (ef.kind === "hit") {
        c.strokeStyle = "#fce2ae";
        c.lineWidth = 1.5;
        for (let i = 0; i < 5; i++) {
          const a = i * 1.25;
          line(
            c,
            p.x + Math.cos(a) * 3,
            p.y - 15 + Math.sin(a) * 3,
            p.x + Math.cos(a) * 8,
            p.y - 15 + Math.sin(a) * 8,
            "#ffe8b4",
            1.2,
          );
        }
      }
      if (ef.kind === "delivery") {
        c.globalAlpha = Math.min(1, ef.life);
        c.font = "bold 12px Arial";
        c.textAlign = "center";
        c.fillStyle = ef.color;
        c.fillText(ef.text, p.x, p.y - 25 - (1.4 - ef.life) * 15);
        c.globalAlpha = 1;
      }
    }
    if (this.placement) {
      const { type, x, y, valid } = this.placement,
        d = BUILDINGS[type],
        p = project(x, y);
      c.save();
      c.translate(p.x, p.y);
      c.globalAlpha = 0.58;
      drawBuilding(c, type, "player", time, this.game.ages.player);
      c.globalAlpha = 1;
      c.restore();
      this.drawFootprint(
        c,
        { x, y, w: d.w, h: d.h },
        valid ? "#d4e4a2" : "#e29478",
        1,
      );
      for (let yy = y; yy < y + d.h; yy++)
        for (let xx = x; xx < x + d.w; xx++)
          this.drawFootprint(
            c,
            { x: xx, y: yy, w: 1, h: 1 },
            valid ? "#d4e4a2" : "#e29478",
            0.3,
          );
    }
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (this.selectionBox) {
      const { x, y, w, h } = this.selectionBox;
      c.fillStyle = "#d7e8b820";
      c.strokeStyle = "#e4edc4";
      c.lineWidth = 1;
      c.fillRect(x, y, w, h);
      c.strokeRect(x, y, w, h);
    }
    this.drawMinimap();
  }
  drawArrows(c) {
    for (const a of this.game.projectiles) {
      const t = Math.min(1, 1 - a.remaining / a.duration),
        x = a.x + (a.toX - a.x) * t,
        y = a.y + (a.toY - a.y) * t;
      if (this.game.fog.state(x, y) !== 2) continue;
      const p = project(x, y),
        end = project(a.toX, a.toY),
        start = project(a.x, a.y),
        height = 100 * (1 - t) + 14 * t + Math.sin(t * Math.PI) * 18;
      const angle = Math.atan2(end.y - start.y + 75, end.x - start.x);
      c.save();
      c.translate(p.x, p.y - height);
      c.rotate(angle);
      line(c, -9, 0, 2, 0, "#e7ce92", 1.5);
      poly(
        c,
        [
          [5, 0],
          [0, -2],
          [0, 2],
        ],
        "#eee9cd",
      );
      line(c, -8, 0, -10, -2, "#b9cbc0", 1);
      c.restore();
    }
  }
  drawFog(c) {
    const fog = this.game.fog;
    if (this.fogOwner !== fog || this.fogRevision !== fog.revision) {
      this.fogOwner = fog;
      this.fogRevision = fog.revision;
      const raw = document.createElement("canvas");
      raw.width = Math.ceil(this.ground.width / 2);
      raw.height = Math.ceil(this.ground.height / 2);
      const ctx = raw.getContext("2d");
      ctx.scale(0.5, 0.5);
      ctx.translate(this.groundOffset.x, this.groundOffset.y);
      for (let y = 0; y < MAP_SIZE; y++)
        for (let x = 0; x < MAP_SIZE; x++) {
          const state = fog.state(x, y);
          if (state === 2) continue;
          poly(
            ctx,
            [p3(x, y), p3(x + 1, y), p3(x + 1, y + 1), p3(x, y + 1)],
            state === 0 ? "#192e2c" : "#142b2ca8",
            state === 0 ? "#192e2c" : null,
            1.1,
          );
        }
      this.fogCanvas = document.createElement("canvas");
      this.fogCanvas.width = raw.width;
      this.fogCanvas.height = raw.height;
      const softened = this.fogCanvas.getContext("2d");
      softened.filter = "blur(3px)";
      softened.drawImage(raw, 0, 0);
    }
    c.drawImage(
      this.fogCanvas,
      -this.groundOffset.x,
      -this.groundOffset.y,
      this.ground.width,
      this.ground.height,
    );
  }
  drawFootprint(c, b, color, alpha) {
    c.save();
    c.globalAlpha = alpha;
    const ps = [
      p3(b.x, b.y),
      p3(b.x + b.w, b.y),
      p3(b.x + b.w, b.y + b.h),
      p3(b.x, b.y + b.h),
    ];
    poly(c, ps, color + "20", color, 1.5);
    c.restore();
  }
  healthBar(c, e) {
    const p = project(e.x + (e.w || 0) / 2, e.y + (e.h || 0) / 2),
      building = e.kind === "building",
      w = building ? 57 : 23,
      y =
        p.y -
        (building
          ? e.type === "tower"
            ? 126
            : e.type === "town"
              ? 104
              : e.type === "farm"
                ? 21
                : 77
          : 39);
    c.fillStyle = "#20392bc9";
    c.fillRect(p.x - w / 2 - 1, y - 1, w + 2, 5);
    c.fillStyle = e.team === "enemy" ? "#d08068" : "#b4d288";
    c.fillRect(p.x - w / 2, y, w * Math.max(0, e.hp / e.maxHp), 3);
    if (building && !e.complete) {
      c.fillStyle = "#d9b773";
      c.fillRect(p.x - w / 2, y + 7, w * e.progress, 2);
    }
    if (building && this.selected.has(e.id)) {
      c.font = '9px "DM Sans",Arial';
      c.textAlign = "center";
      c.fillStyle = "#f7edcc";
      c.shadowColor = "#233c30";
      c.shadowBlur = 3;
      c.fillText(BUILDINGS[e.type].name, p.x, y - 8);
      c.shadowBlur = 0;
    }
  }
  drawMinimap() {
    const c = this.mc,
      w = this.mini.width,
      h = this.mini.height,
      s = Math.min((w - 14) / (MAP_SIZE * 2), (h - 12) / MAP_SIZE);
    c.clearRect(0, 0, w, h);
    c.fillStyle = "#384e3c";
    c.fillRect(0, 0, w, h);
    const mp = (x, y) => ({ x: w / 2 + (x - y) * s, y: 5 + ((x + y) * s) / 2 });
    const a = mp(0, 0),
      b = mp(MAP_SIZE, 0),
      d = mp(0, MAP_SIZE),
      cc = mp(MAP_SIZE, MAP_SIZE);
    poly(
      c,
      [
        [a.x, a.y],
        [b.x, b.y],
        [cc.x, cc.y],
        [d.x, d.y],
      ],
      "#879363",
    );
    for (let y = 0; y < MAP_SIZE; y++)
      for (let x = 0; x < MAP_SIZE; x++)
        if (this.game.terrain[y * MAP_SIZE + x]) {
          const p = mp(x + 0.5, y + 0.5);
          c.fillStyle = "#79aaa0";
          c.fillRect(p.x - s, p.y - s / 2, s * 2, s);
        }
    for (const r of this.game.fog
      .knownEntities()
      .filter((e) => e.kind === "resource"))
      if (r.amount > 0) {
        const p = mp(r.x + 0.5, r.y + 0.5);
        c.fillStyle =
          r.type === "wood"
            ? "#4c7248"
            : r.type === "gold"
              ? "#dcc16c"
              : "#aa7a58";
        c.fillRect(p.x - 1.3, p.y - 0.7, 2.6, 1.6);
      }
    for (const b of this.game.fog
      .knownEntities()
      .filter((e) => e.kind === "building")) {
      const ps = [
        mp(b.x, b.y),
        mp(b.x + b.w, b.y),
        mp(b.x + b.w, b.y + b.h),
        mp(b.x, b.y + b.h),
      ];
      poly(
        c,
        ps.map((p) => [p.x, p.y]),
        b.team === "player" ? "#b9e0c5" : "#ec967a",
        b.type === "town" ? "#fcf0bf" : null,
        0.7,
      );
    }
    for (const u of this.game.units.filter((e) => this.game.fog.canSee(e))) {
      const p = mp(u.x, u.y);
      c.fillStyle = u.team === "player" ? "#ddedc8" : "#ef8d72";
      c.fillRect(p.x - 1, p.y - 1, 2, 2);
    }
    for (let y = 0; y < MAP_SIZE; y++)
      for (let x = 0; x < MAP_SIZE; x++) {
        const state = this.game.fog.state(x, y);
        if (state === 2) continue;
        const ps = [mp(x, y), mp(x + 1, y), mp(x + 1, y + 1), mp(x, y + 1)];
        poly(
          c,
          ps.map((p) => [p.x, p.y]),
          state === 0 ? "#192e2c" : "#192e2caa",
          state === 0 ? "#192e2c" : null,
          0.7,
        );
      }
    const corners = [
      [0, 0],
      [this.width, 0],
      [this.width, this.height - 180],
      [0, this.height - 180],
    ]
      .map(([x, y]) => this.toWorld(x, y))
      .map((p) => mp(p.x, p.y));
    c.save();
    poly(
      c,
      [
        [a.x, a.y],
        [b.x, b.y],
        [cc.x, cc.y],
        [d.x, d.y],
      ],
      null,
    );
    c.clip();
    poly(
      c,
      corners.map((p) => [p.x, p.y]),
      "#f5eac710",
      "#f0e4ba",
      0.8,
    );
    c.restore();
    this.minimapTransform = { s, w, h };
  }
  minimapClick(x, y) {
    const { s, w } = this.minimapTransform;
    const isoX = (x - w / 2) / s,
      isoY = ((y - 5) / s) * 2;
    const p = project((isoX + isoY) / 2, (isoY - isoX) / 2);
    this.camera.x = p.x;
    this.camera.y = p.y;
    this.clampCamera();
  }
  hitTest(sx, sy) {
    const world = this.toWorld(sx, sy);
    let best = null,
      bestDist = Infinity;
    for (const u of this.game.units.filter((e) => this.game.fog.canSee(e))) {
      const p = this.toScreen(u.x, u.y),
        d = Math.hypot(sx - p.x, (sy - (p.y - 13 * this.camera.zoom)) * 0.8);
      if (d < 17 * this.camera.zoom && d < bestDist) {
        best = u;
        bestDist = d;
      }
    }
    if (best) return best;
    // Ground footprints are authoritative; roof hitboxes are a convenience.
    const entities = [
      ...this.game.buildings,
      ...this.game.resources.filter((r) => r.amount > 0),
    ];
    for (const e of entities)
      if (
        this.game.fog.canSee(e) &&
        world.x >= e.x &&
        world.x < e.x + e.w &&
        world.y >= e.y &&
        world.y < e.y + e.h
      )
        return e;
    const sorted = this.game.buildings
      .filter((e) => this.game.fog.canSee(e))
      .sort((a, b) => b.x + b.y - (a.x + a.y));
    for (const b of sorted) {
      const p = this.toScreen(b.x + b.w / 2, b.y + b.h / 2),
        height =
          (b.type === "tower"
            ? 115
            : b.type === "town"
              ? 91
              : b.type === "farm"
                ? 10
                : 65) * this.camera.zoom;
      if (
        Math.abs(sx - p.x) < b.w * 21 * this.camera.zoom &&
        sy < p.y &&
        sy > p.y - height
      )
        return b;
    }
    for (const r of this.game.resources.filter(
      (r) => r.amount > 0 && r.type === "wood" && this.game.fog.canSee(r),
    )) {
      const p = this.toScreen(r.x + 0.5, r.y + 0.5);
      if (
        Math.abs(sx - p.x) < 19 * this.camera.zoom &&
        sy > p.y - 65 * this.camera.zoom &&
        sy < p.y
      )
        return r;
    }
    return null;
  }
  portrait(canvas, entity) {
    const c = canvas.getContext("2d");
    c.clearRect(0, 0, canvas.width, canvas.height);
    c.save();
    if (!entity) {
      c.translate(47, 65);
      c.scale(0.33, 0.33);
      drawBuilding(c, "town");
    } else if (entity.kind === "unit") {
      c.translate(canvas.width / 2, canvas.height * 0.88);
      c.scale(2.4, 2.4);
      drawUnit(c, {
        ...entity,
        path: [],
        order: { kind: "idle" },
        hitFlash: 0,
      });
    } else if (entity.kind === "building") {
      const d = BUILDINGS[entity.type];
      c.translate(canvas.width / 2, canvas.height * 0.47);
      c.scale(0.45, 0.45);
      drawBuilding(c, entity.type, entity.team, 0, entity.age || 1);
    } else {
      c.translate(canvas.width / 2, canvas.height * 0.85);
      const s = this.resourceSprite(entity);
      c.drawImage(s, -64, -116);
    }
    c.restore();
  }
  actionIcon(canvas, type) {
    const c = canvas.getContext("2d");
    c.clearRect(0, 0, canvas.width, canvas.height);
    c.save();
    if (type === "villager" || type === "soldier") {
      c.translate(canvas.width / 2, canvas.height - 3);
      c.scale(1.25, 1.25);
      drawUnit(c, {
        type,
        team: "player",
        order: { kind: "idle" },
        path: [],
        hp: 100,
      });
    } else {
      const d = BUILDINGS[type];
      c.translate(
        canvas.width / 2,
        canvas.height * (type === "tower" ? 0.75 : 0.49),
      );
      const scale =
        type === "tower"
          ? 0.34
          : type === "barracks"
            ? 0.28
            : type === "town"
              ? 0.26
              : 0.35;
      c.scale(scale, scale);
      drawBuilding(c, type, "player", 0, this.game.ages.player);
    }
    c.restore();
  }
}
