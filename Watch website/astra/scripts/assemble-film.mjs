import { spawnSync } from 'node:child_process';
import { access, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const [aspect, version, ...clips] = process.argv.slice(2);
if (!['landscape', 'portrait'].includes(aspect) || !/^v\d+$/.test(version) || clips.length !== 3) {
  throw new Error('Usage: node scripts/assemble-film.mjs landscape|portrait v1 <accepted-clip1> <accepted-clip2> <accepted-clip3>');
}
const run = (command, args) => {
  const result = spawnSync(command, args, { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr);
  return result.stdout;
};
const output = `public/media/originals/${aspect}-${version}.mp4`;
try { await access(output); throw new Error('Version already exists.'); } catch (e) { if (e.code !== 'ENOENT') throw e; }
const metadata = clips.map(input => {
  if (!path.resolve(input).startsWith(path.resolve('.') + path.sep)) throw new Error('Keep input media inside this project.');
  return { input, ...JSON.parse(run('ffprobe', ['-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,r_frame_rate,nb_read_frames:format=duration','-of','json',input])) };
});
const { width, height } = metadata[0].streams[0];
const filters = clips.map((_, i) => `[${i}:v]scale=${width}:${height}:force_original_aspect_ratio=increase,crop=${width}:${height},setsar=1,fps=24,setpts=PTS-STARTPTS[v${i}]`);
filters.push('[v0][v1][v2]concat=n=3:v=1:a=0[out]');
await mkdir('public/media/originals', { recursive: true });
run('ffmpeg', ['-hide_banner','-loglevel','error',...clips.flatMap(c => ['-i',c]),'-filter_complex',filters.join(';'),'-map','[out]','-an','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',output]);
let time = 0;
const boundaries = metadata.map(m => { const start=time; time+=Number(m.format.duration); return { input:m.input,start,end:time,frames:Number(m.streams[0].nb_read_frames) }; });
const result = { output, aspect, version, width, height, duration:time, boundaries, method:'Sequential concatenation. Original generated clips and local finishing sidecars preserved; consult the asset ledger for preview versus storyboard acceptance.' };
await writeFile(output.replace('.mp4','.json'), JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
