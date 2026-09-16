// Removes the observed dark rectangular backdrop artifact while retaining generated motion.
// A smooth low-luminance matte blends studio shadows into the brand's midnight background.
import { spawnSync } from 'node:child_process';
import { mkdir, readdir, rm, writeFile, access } from 'node:fs/promises';
import sharp from 'sharp';
const [input, output] = process.argv.slice(2);
if(!input || !output) throw new Error('Usage: node scripts/normalize-studio.mjs <input.mp4> <new-output.mp4>');
try { await access(output); throw new Error('Output exists.'); } catch(e) { if(e.code !== 'ENOENT') throw e; }
const dir=output.replace('.mp4','-processing');await mkdir(dir,{recursive:true});
const run=args=>{const r=spawnSync('ffmpeg',['-hide_banner','-loglevel','error',...args],{encoding:'utf8'});if(r.status!==0)throw new Error(r.stderr);};
run(['-i',input,'-c:v','png',`${dir}/%04d.png`]);
const files=(await readdir(dir)).filter(f=>f.endsWith('.png')).sort();
for(const name of files){
  const file=`${dir}/${name}`;
  const {data,info}=await sharp(file).removeAlpha().raw().toBuffer({resolveWithObject:true});
  for(let i=0;i<data.length;i+=3){
    const maximum=Math.max(data[i],data[i+1],data[i+2]);
    let a=Math.max(0,Math.min(1,(maximum-43)/25));a=a*a*(3-2*a);
    for(let c=0;c<3;c++)data[i+c]=Math.round(data[i+c]*a+[16,24,32][c]*(1-a));
  }
  await sharp(data,{raw:info}).png().toFile(file+'.tmp.png');
  await rm(file);
  const {rename}=await import('node:fs/promises');await rename(file+'.tmp.png',file);
}
run(['-framerate','24','-i',`${dir}/%04d.png`,'-an','-c:v','libx264','-crf','17','-preset','slow','-pix_fmt','yuv420p','-movflags','+faststart',output]);
await writeFile(output.replace('.mp4','.json'),JSON.stringify({input,output,frames:files.length,operation:'Smooth dark-studio matte: maximum RGB <=43 becomes #101820, smooth transition to original RGB at68. No geometric, timing or scene changes.'},null,2)+'\n');
await rm(dir,{recursive:true});console.log(output);
