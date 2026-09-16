// Process a reviewed local film or explicitly labelled preview. Does not generate or spend credits.
// Usage: node scripts/extract-sequence.mjs landscape public/media/originals/landscape-v1.mp4 v1
import { spawnSync } from "node:child_process";
import {
  readFile,
  writeFile,
  mkdir,
  readdir,
  copyFile,
  access,
  rm,
} from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
const [aspect, input, version = "v1"] = process.argv.slice(2);
if (
  !["landscape", "portrait"].includes(aspect) ||
  !input ||
  !/^v[1-9]\d*$/.test(version)
)
  throw new Error(
    "Usage: node scripts/extract-sequence.mjs landscape|portrait <accepted-local-video> v1",
  );
const resolved = path.resolve(input);
if (!resolved.startsWith(path.resolve(".") + path.sep))
  throw new Error("Keep original videos within this project.");
await access(resolved);
const output = `public/media/${aspect}-${version}`;
try {
  await access(output);
  throw new Error("That version already exists; select a new version.");
} catch (e) {
  if (e.code !== "ENOENT") throw e;
}
const probe = spawnSync(
  "ffprobe",
  [
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-show_entries",
    "stream=width,height:format=duration",
    "-of",
    "json",
    resolved,
  ],
  { encoding: "utf8" },
);
if (probe.status !== 0) throw new Error(probe.stderr);
const info = JSON.parse(probe.stdout),
  original = info.streams[0];
const expected = aspect === "landscape" ? 16 / 9 : 9 / 16;
if (Math.abs(original.width / original.height - expected) > 0.03)
  throw new Error(
    "Wrong aspect ratio. Recompose/generated portrait footage is required, not a desktop crop.",
  );
await mkdir(output, { recursive: true });
await mkdir(`${output}/.png-frames`);
const width = aspect === "landscape" ? 1440 : 720;
const result = spawnSync(
  "ffmpeg",
  [
    "-hide_banner",
    "-loglevel",
    "error",
    "-i",
    resolved,
    "-vf",
    `fps=18,scale=${width}:-2:flags=lanczos`,
    "-c:v",
    "png",
    `${output}/.png-frames/frame-%04d.png`,
  ],
  { encoding: "utf8" },
);
if (result.status !== 0) {
  await rm(output, { recursive: true });
  throw new Error(result.stderr);
}
// Sharp supplies WebP encoding even when the installed ffmpeg lacks libwebp.
// Encode sequentially to bound working memory; remove intermediate PNGs afterwards.
for (const file of (await readdir(`${output}/.png-frames`)).sort()) {
  await sharp(`${output}/.png-frames/${file}`)
    .webp({ quality: 78, effort: 5 })
    .toFile(`${output}/${file.replace(/\.png$/, ".webp")}`);
}
await rm(`${output}/.png-frames`, { recursive: true });
const files = (await readdir(output))
  .filter((f) => /^frame-\d{4}\.webp$/.test(f))
  .sort();
if (!files.length) throw new Error("No frames extracted.");
const meta = await sharp(`${output}/${files[0]}`).metadata();
const inspected = [];
let transitionIndices = [];
try {
  const assembly = JSON.parse(await readFile(resolved.replace(/\.mp4$/, ".json"), "utf8"));
  transitionIndices = (assembly.boundaries || []).slice(0, -1).flatMap(({ end }) => {
    const next = Math.round(end * 18);
    return [next - 1, next];
  });
} catch { /* A standalone source may not have an assembly sidecar. */ }
for (const index of [
  0,
  ...transitionIndices,
  Math.floor(files.length / 2),
  files.length - 1,
]) {
  const file = files[Math.max(0, index)];
  await sharp(`${output}/${file}`).stats();
  inspected.push(file);
}
await copyFile(`${output}/${files[0]}`, `${output}/poster.webp`);
const manifest = JSON.parse(
  await readFile("public/media/manifest.json", "utf8"),
);
manifest[aspect] = {
  frameCount: files.length,
  width: meta.width,
  height: meta.height,
  fps: 18,
  poster: `/media/${aspect}-${version}/poster.webp`,
  posterType: "full",
  pattern: `/media/${aspect}-${version}/frame-{frame}.webp`,
  startIndex: 1,
  padding: 4,
  original: path.relative(".", resolved),
  version,
  inspectedForDecodability: inspected,
  visualAcceptance: "REQUIRES HUMAN/VISUAL INSPECTION",
};
manifest.status = "requires-visual-acceptance";
await writeFile(
  "public/media/manifest.json",
  JSON.stringify(manifest, null, 2) + "\n",
);
console.log(
  JSON.stringify(
    {
      aspect,
      frameCount: files.length,
      width: meta.width,
      height: meta.height,
      checked: inspected,
      reminder:
        "Inspect identity, exact clip seams, edges and wrist anatomy, then record acceptance in ASSETS.json. Decodability is not a visual pass.",
    },
    null,
    2,
  ),
);
