import { spawnSync } from 'node:child_process';
import { mkdir, readdir, rm } from 'node:fs/promises';
import sharp from 'sharp';
import path from 'node:path';
const [input,output,step='1'] = process.argv.slice(2);
if(!input||!output)throw new Error('Usage: node scripts/media-contact-sheet.mjs <video> <contact-sheet.jpg> [seconds-between-frames]');
const dir=path.join('artifacts/media-qa',path.basename(output,path.extname(output))+'-frames');await mkdir(dir,{recursive:true});
const probe=spawnSync('ffprobe',['-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','json',input],{encoding:'utf8'});if(probe.status!==0)throw new Error(probe.stderr);
const [numerator,denominator]=JSON.parse(probe.stdout).streams[0].r_frame_rate.split('/').map(Number), fps=numerator/denominator, every=Math.max(1,Math.round(Number(step)*fps));
const result=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-i',input,'-vf',`select=not(mod(n\\,${every})),scale=480:-2`,'-fps_mode','vfr','-frames:v','30','-y',`${dir}/%03d.png`],{encoding:'utf8'});if(result.status!==0)throw new Error(result.stderr);
const files=(await readdir(dir)).filter(f=>f.endsWith('.png')).sort();const columns=Math.min(4,files.length),tileW=480;const meta=await sharp(path.join(dir,files[0])).metadata(),tileH=meta.height+28;
const layers=[];for(let i=0;i<files.length;i++){const x=(i%columns)*tileW,y=Math.floor(i/columns)*tileH;layers.push({input:await sharp(path.join(dir,files[i])).png().toBuffer(),left:x,top:y});layers.push({input:Buffer.from(`<svg width="480" height="28"><rect width="480" height="28" fill="#101820"/><text x="10" y="19" font-family="sans-serif" font-size="14" fill="#eee">${(i*Number(step)).toFixed(1)} s</text></svg>`),left:x,top:y+meta.height});}
await sharp({create:{width:columns*tileW,height:Math.ceil(files.length/columns)*tileH,channels:3,background:'#101820'}}).composite(layers).jpeg({quality:92}).toFile(output);console.log(output);
