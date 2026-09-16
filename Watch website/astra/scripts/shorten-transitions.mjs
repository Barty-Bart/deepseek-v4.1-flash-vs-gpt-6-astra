// Versioned timing edit: keep active motion intact; sample only the two lingering intervals.
// Run once against v1. Originals and the complete source-to-output frame map are retained.
import { readFile, writeFile, mkdir, copyFile, stat } from "node:fs/promises";
import { spawnSync } from "node:child_process";

const path = "public/media/manifest.json";
const manifest = JSON.parse(await readFile(path, "utf8"));
if (manifest.landscape.version !== "v1" || manifest.portrait.version !== "v1")
  throw new Error(
    "This edit expects the preserved v1 sequences; refusing to overwrite a revision.",
  );
await writeFile(
  "docs/manifest-preview-v1.json",
  JSON.stringify(manifest, null, 2) + "\n",
  { flag: "wx" },
);
for (const aspect of ["landscape", "portrait"]) {
  const source = manifest[aspect],
    fps = source.fps;
  const intervals = [
    {
      name: "exploded pause",
      start: aspect === "landscape" ? 4.8 : 5.75,
      end: 8.25,
      keep: 10,
    },
    { name: "abstract blur", start: 13.2, end: 15.2, keep: 8 },
  ].map((part) => ({
    ...part,
    first: Math.round(part.start * fps),
    last: Math.round(part.end * fps),
  }));
  const indices = [];
  for (let i = 0; i < source.frameCount; i++) {
    const part = intervals.find((p) => i >= p.first && i <= p.last);
    if (
      !part ||
      Array.from({ length: part.keep }, (_, n) =>
        Math.round(
          part.first + (n * (part.last - part.first)) / (part.keep - 1),
        ),
      ).includes(i)
    )
      indices.push(i);
  }
  const dir = `public/media/${aspect}-v2`;
  await mkdir(dir); // Intentionally fail if this version exists.
  let bytes = 0;
  for (let i = 0; i < indices.length; i++) {
    const input = source.pattern.replace(
      "{frame}",
      String(indices[i] + 1).padStart(4, "0"),
    );
    const output = `${dir}/frame-${String(i + 1).padStart(4, "0")}.webp`;
    await copyFile(`public${input}`, output);
    bytes += (await stat(output)).size;
  }
  await copyFile(`${dir}/frame-0001.webp`, `${dir}/poster.webp`);
  // Continuous inverse of the frame-selection map, including the sped-up intervals.
  const at = (seconds) => {
    const target = seconds * fps;
    const next = indices.findIndex((n) => n >= target);
    if (next < 0) return 1;
    if (next === 0) return 0;
    return (
      (next -
        1 +
        (target - indices[next - 1]) / (indices[next] - indices[next - 1])) /
      (indices.length - 1)
    );
  };
  const original = `public/media/originals/${aspect}-v2.mp4`;
  const result = spawnSync(
    "ffmpeg",
    [
      "-hide_banner",
      "-loglevel",
      "error",
      "-framerate",
      String(fps),
      "-i",
      `${dir}/frame-%04d.webp`,
      "-c:v",
      "libx264",
      "-crf",
      "18",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      "-n",
      original,
    ],
    { encoding: "utf8" },
  );
  if (result.status !== 0) throw new Error(result.stderr);
  const edit = {
    sourceOriginal: source.original,
    sourcePattern: source.pattern,
    sourceFrameCount: source.frameCount,
    outputFrameCount: indices.length,
    fps,
    duration: indices.length / fps,
    sourceFrameIndices: indices,
    intervals: intervals.map((p) => ({
      ...p,
      beforeFrames: p.last - p.first + 1,
      afterFrames: p.keep,
    })),
    note: "Zero-based source indices. Selected optimized frames copied without re-encoding; review MP4 encoded from those exact frames. Active-motion frames outside the intervals are all retained.",
  };
  await writeFile(
    original.replace(".mp4", ".json"),
    JSON.stringify(edit, null, 2) + "\n",
  );
  manifest[aspect] = {
    ...source,
    version: "v2",
    original,
    sourceOriginal: source.original,
    frameCount: indices.length,
    duration: indices.length / fps,
    poster: `/media/${aspect}-v2/poster.webp`,
    pattern: `/media/${aspect}-v2/frame-{frame}.webp`,
    timeline: [0, at(1.5), at(8.25), at(15.2), 1],
    resolutionCopyAt: at(source.resolutionCopyAt * source.duration),
    mediaExpansion: [at(7.04), at(8.54), at(13.4), at(15.2)],
    sequenceBytes: bytes,
    timingEdit: {
      sidecar: original.replace(".mp4", ".json"),
      removedFrames: source.frameCount - indices.length,
      intervals: edit.intervals,
    },
    inspectedForDecodability: [],
  };
  console.log(
    JSON.stringify({
      aspect,
      before: source.frameCount,
      after: indices.length,
      intervals: edit.intervals,
    }),
  );
}
manifest.version = 2;
await writeFile(path, JSON.stringify(manifest, null, 2) + "\n");
