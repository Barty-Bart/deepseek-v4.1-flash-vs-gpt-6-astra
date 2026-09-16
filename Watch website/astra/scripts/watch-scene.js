import * as T from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

const query = new URLSearchParams(location.search);
const variant = query.get("variant") || "midnight";
const mode = query.get("mode") || "product";
const width = innerWidth,
  height = innerHeight;
const renderer = new T.WebGLRenderer({
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(1);
renderer.setSize(width, height);
renderer.setClearColor(0x000000, 0);
renderer.toneMapping = T.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
document.body.appendChild(renderer.domElement);
const scene = new T.Scene();
const pmrem = new T.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.02).texture;
const camera = new T.PerspectiveCamera(32, width / height, 0.1, 100);
const dark = variant === "eclipse";
const steel = new T.MeshStandardMaterial({
  color: dark ? "#45484b" : "#b9c0c6",
  metalness: 1,
  roughness: 0.29,
});
const polished = new T.MeshStandardMaterial({
  color: dark ? "#707274" : "#e9edef",
  metalness: 1,
  roughness: 0.12,
});
const gold = new T.MeshStandardMaterial({
  color: "#c7a76b",
  metalness: 0.85,
  roughness: 0.28,
});
const watch = new T.Group();
scene.add(watch);
function mesh(geo, mat, parent = watch, x = 0, y = 0, z = 0) {
  const m = new T.Mesh(geo, mat);
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}
function cylinder(r, depth, mat, x = 0, y = 0, z = 0, parent = watch) {
  const m = mesh(
    new T.CylinderGeometry(r, r, depth, 128),
    mat,
    parent,
    x,
    y,
    z,
  );
  m.rotation.x = Math.PI / 2;
  return m;
}
function ring(r, t, mat, z, parent = watch) {
  return mesh(new T.TorusGeometry(r, t, 16, 160), mat, parent, 0, 0, z);
}
function box(w, h, d, mat, x, y, z, parent = watch, r = 0.025) {
  return mesh(new RoundedBoxGeometry(w, h, d, 3, r), mat, parent, x, y, z);
}

// One editable case architecture, in local world units (diameter 3 = 40 mm).
cylinder(1.5, 0.34, steel, 0, 0, 0);
cylinder(1.455, 0.09, polished, 0, 0, 0.19);
cylinder(
  1.377,
  0.035,
  new T.MeshStandardMaterial({
    color: "#151a20",
    metalness: 0.5,
    roughness: 0.4,
  }),
  0,
  0,
  0.255,
);
ring(1.405, 0.055, polished, 0.25);
ring(1.47, 0.022, polished, -0.15);
for (const y of [-1, 1])
  for (const x of [-1, 1]) {
    const lug = box(0.33, 0.6, 0.27, steel, x * 0.67, y * 1.4, -0.065);
    lug.rotation.x = y * -0.15;
  }
const crown = cylinder(0.155, 0.23, steel, 1.58, 0, 0.025);
crown.rotation.set(0, 0, Math.PI / 2);
for (let i = 0; i < 25; i++) {
  let a = (i / 25) * Math.PI * 2;
  box(
    0.21,
    0.016,
    0.016,
    polished,
    1.58,
    Math.cos(a) * 0.15,
    0.025 + Math.sin(a) * 0.15,
  );
}

function dialTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 1536;
  const ctx = c.getContext("2d");
  const colors = {
    midnight: ["#132637", "#304c60"],
    ivory: ["#d5cebc", "#f1e9d8"],
    forest: ["#152e25", "#466052"],
    eclipse: ["#292c2f", "#4b4e50"],
    atelier: ["#b5a17a", "#e6d8b6"],
  };
  const [base, light] = colors[variant];
  const g = ctx.createRadialGradient(768, 768, 50, 768, 768, 850);
  g.addColorStop(0, light);
  g.addColorStop(0.8, base);
  g.addColorStop(1, "#101820");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 1536, 1536);
  for (let i = 0; i < 2200; i++) {
    let a = (i / 2200) * Math.PI * 2;
    ctx.strokeStyle = `rgba(230,230,230,${0.012 + 0.022 * (Math.sin(i * 12.3) * 0.5 + 0.5)})`;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(768, 768);
    ctx.lineTo(768 + Math.cos(a) * 760, 768 + Math.sin(a) * 760);
    ctx.stroke();
  }
  const ink = ["ivory", "atelier"].includes(variant) ? "#454c4f" : "#dbe0df";
  ctx.strokeStyle = ink;
  for (let i = 0; i < 60; i++) {
    let a = (i / 60) * Math.PI * 2;
    const r = i % 5 === 0 ? 684 : 699;
    ctx.lineWidth = i % 5 === 0 ? 3 : 2;
    ctx.beginPath();
    ctx.moveTo(768 + Math.sin(a) * r, 768 + Math.cos(a) * r);
    ctx.lineTo(768 + Math.sin(a) * 711, 768 + Math.cos(a) * 711);
    ctx.stroke();
  }
  ctx.fillStyle = ink;
  ctx.textAlign = "center";
  ctx.font = "500 48px Georgia";
  ctx.letterSpacing = "6px";
  ctx.fillText("MERIDIAN", 768, 510);
  ctx.letterSpacing = "4px";
  ctx.font = "22px Arial";
  ctx.fillText("AUTOMATIC", 768, 1065);
  ctx.font = "18px Arial";
  ctx.letterSpacing = "2px";
  ctx.fillText("40 H  /  100 M", 768, 1110);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(768, 366);
  ctx.lineTo(768, 438);
  ctx.moveTo(744, 402);
  ctx.lineTo(792, 402);
  ctx.moveTo(768, 375);
  ctx.lineTo(777, 402);
  ctx.lineTo(768, 429);
  ctx.lineTo(759, 402);
  ctx.closePath();
  ctx.stroke();
  ctx.fillStyle = "#e4e2d9";
  ctx.fillRect(1155, 726, 120, 84);
  ctx.fillStyle = "#242b2e";
  ctx.font = "44px Arial";
  ctx.letterSpacing = "0px";
  ctx.fillText("18", 1215, 785);
  const texture = new T.CanvasTexture(c);
  texture.colorSpace = T.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return texture;
}
mesh(
  new T.CircleGeometry(1.32, 128),
  new T.MeshStandardMaterial({
    map: dialTexture(),
    metalness: 0.48,
    roughness: 0.4,
  }),
  watch,
  0,
  0,
  0.29,
);
for (let i = 0; i < 12; i++) {
  if (i === 3) continue;
  const a = (i / 12) * Math.PI * 2;
  const m = box(
    0.047,
    i === 0 ? 0.23 : 0.2,
    0.027,
    polished,
    Math.sin(a) * 1.105,
    Math.cos(a) * 1.105,
    0.311,
  );
  m.rotation.z = -a;
}
function hand(length, width, angle, z, mat) {
  const group = new T.Group();
  watch.add(group);
  box(width, length, 0.025, mat, 0, length / 2 - 0.08, z, group, 0.012);
  group.rotation.z = angle;
}
hand(0.82, 0.07, (Math.PI / 180) * 55, 0.34, polished);
hand(1.12, 0.049, -Math.PI / 3, 0.375, polished);
hand(1.18, 0.016, (Math.PI / 180) * 190, 0.411, gold);
cylinder(0.055, 0.034, gold, 0, 0, 0.43);
ring(1.335, 0.012, polished, 0.327);

if (variant === "atelier") {
  const leather = new T.MeshStandardMaterial({
    color: "#8c4729",
    roughness: 0.73,
  });
  for (const sign of [-1, 1])
    for (let i = 0; i < 32; i++) {
      const a = sign * (0.6 + i * 0.083);
      const m = box(
        1.4,
        0.24,
        0.075,
        leather,
        0,
        Math.sin(a) * 2.75,
        -1.75 + Math.cos(a) * 1.9,
      );
      m.rotation.x = Math.atan2(-1.9 * Math.sin(a), 2.75 * Math.cos(a));
    }
} else {
  for (const sign of [-1, 1])
    for (let i = 0; i < 18; i++) {
      const a = sign * (0.59 + i * 0.144);
      const y = Math.sin(a) * 2.73,
        z = -1.75 + Math.cos(a) * 1.92;
      const group = new T.Group();
      group.position.set(0, y, z);
      group.rotation.x = Math.atan2(-1.92 * Math.sin(a), 2.73 * Math.cos(a));
      watch.add(group);
      const taper = 1 - Math.min(i, 10) * 0.009;
      box(0.71 * taper, 0.335, 0.15, steel, 0, 0, 0.016, group, 0.035);
      for (const s of [-1, 1]) {
        box(
          0.4 * taper,
          0.35,
          0.16,
          steel,
          s * 0.565 * taper,
          0,
          0,
          group,
          0.035,
        );
        box(
          0.035,
          0.31,
          0.025,
          polished,
          s * 0.36 * taper,
          0,
          0.088,
          group,
          0.007,
        );
      }
    }
  box(1.35, 0.74, 0.1, steel, 0, 0, -3.69);
  box(0.94, 0.57, 0.04, polished, 0, 0, -3.76);
}

const key = new T.DirectionalLight("#fff4e4", 2.2);
key.position.set(-4, 7, 8);
scene.add(key);
const fill = new T.DirectionalLight("#a9c9ed", 1.2);
fill.position.set(6, -1, 4);
scene.add(fill);
const rim = new T.DirectionalLight("#ffffff", 1.8);
rim.position.set(2, 5, -4);
scene.add(rim);

if (mode === "hero") {
  watch.rotation.set(0.08, -0.22, -0.36);
  camera.position.set(4, 3, 10.2);
  camera.lookAt(0, 0, -1.15);
} else if (mode === "portrait") {
  watch.rotation.set(0.04, -0.2, -0.3);
  camera.position.set(3.6, 2.8, 12.8);
  camera.lookAt(0, 0, -1.0);
} else if (mode === "macro") {
  watch.rotation.set(0.04, 0.02, -0.5);
  camera.position.set(1.6, 1.2, 5.1);
  camera.lookAt(0.05, 0.1, 0.1);
} else {
  watch.rotation.z = -0.14;
  camera.position.set(2.4, 3.6, 11.8);
  camera.lookAt(0, 0, -1.25);
}
renderer.render(scene, camera);
window.renderReady = true;
