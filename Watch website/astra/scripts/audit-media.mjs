import { readFile, writeFile, readdir, stat } from "node:fs/promises";
import sharp from "sharp";
const manifest = JSON.parse(
  await readFile("public/media/manifest.json", "utf8"),
);
for (const name of ["landscape", "portrait"]) {
  const s = manifest[name],
    assembly = JSON.parse(
      await readFile(s.original.replace(".mp4", ".json"), "utf8"),
    );
  const dir = `public/media/${name}-${s.version}`,
    files = (await readdir(dir))
      .filter((f) => /^frame-\d+\.webp$/.test(f))
      .sort();
  if (files.length !== s.frameCount) throw new Error("Count mismatch");
  s.sequenceBytes = 0;
  for (const file of files)
    s.sequenceBytes += (await stat(`${dir}/${file}`)).size;
  s.decodedCacheBytes = s.width * s.height * 4 * 13;
  const seams = assembly.sourceFrameIndices
    ? assembly.intervals.flatMap((p) => [
        assembly.sourceFrameIndices.indexOf(p.first),
        assembly.sourceFrameIndices.indexOf(p.last),
      ])
    : (assembly.boundaries || []).slice(0, -1).flatMap((b) => {
        const i = Math.round(b.end * s.fps);
        return [i - 1, i];
      });
  const indices = [
    ...new Set([0, ...seams, Math.floor(files.length / 2), files.length - 1]),
  ];
  if (indices.some((i) => i < 0 || i >= files.length))
    throw new Error("Invalid boundary frame");
  s.inspectedForDecodability = indices.map((i) => files[i]);
  const panels = [],
    tileW = 320,
    tileH = Math.round((s.height / s.width) * tileW) + 24;
  for (let n = 0; n < indices.length; n++) {
    const file = files[indices[n]];
    await sharp(`${dir}/${file}`).stats();
    const x = (n % 4) * tileW,
      y = Math.floor(n / 4) * tileH;
    panels.push({
      input: await sharp(`${dir}/${file}`)
        .resize(tileW, tileH - 24)
        .png()
        .toBuffer(),
      left: x,
      top: y,
    });
    panels.push({
      input: Buffer.from(
        `<svg width="320" height="24"><text x="8" y="17" fill="#f2efe8" font-family="sans-serif" font-size="12">${name} / ${file}</text></svg>`,
      ),
      left: x,
      top: y + tileH - 24,
    });
  }
  await sharp({
    create: {
      width: tileW * 4,
      height: tileH * Math.ceil(indices.length / 4),
      channels: 3,
      background: "#101820",
    },
  })
    .composite(panels)
    .jpeg({ quality: 92 })
    .toFile(`artifacts/media-qa/${name}-${s.version}-optimized-check.jpg`);
}
await writeFile(
  "public/media/manifest.json",
  JSON.stringify(manifest, null, 2) + "\n",
);
console.log(
  JSON.stringify(
    Object.fromEntries(
      ["landscape", "portrait"].map((k) => [
        k,
        {
          frames: manifest[k].frameCount,
          bytes: manifest[k].sequenceBytes,
          duration: manifest[k].duration,
        },
      ]),
    ),
  ),
);
