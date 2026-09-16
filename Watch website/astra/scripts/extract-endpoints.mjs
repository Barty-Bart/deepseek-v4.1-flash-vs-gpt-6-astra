import { spawnSync } from 'node:child_process';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const [input, prefix] = process.argv.slice(2);
if (!input || !prefix) throw new Error('Usage: node scripts/extract-endpoints.mjs <video> <output-prefix>');
const run = (cmd, args) => {
  const result = spawnSync(cmd, args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr);
  return result.stdout;
};
const info = JSON.parse(run('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,nb_read_frames:format=duration', '-of', 'json', input]));
const stream = info.streams[0], count = Number(stream.nb_read_frames);
await mkdir(prefix.substring(0, prefix.lastIndexOf('/')), { recursive: true });
const files = [];
for (const [name, frame] of [['first', 0], ['last', count - 1]]) {
  const path = `${prefix}-${name}.png`;
  run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', input, '-vf', `select=eq(n\\,${frame})`, '-frames:v', '1', '-y', path]);
  files.push({ name, frame, path, sha256: createHash('sha256').update(await readFile(path)).digest('hex') });
}
const output = { input, ...stream, duration: Number(info.format.duration), files };
await writeFile(`${prefix}-metadata.json`, JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify(output));
