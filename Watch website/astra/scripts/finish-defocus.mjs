// Author the specified full-frame optical-blur transition over the generated macro footage.
import { spawnSync } from 'node:child_process';
import { writeFile, unlink, access } from 'node:fs/promises';
const [input,output,start='5',end='6.75'] = process.argv.slice(2);
if(!input||!output)throw new Error('Usage: node scripts/finish-defocus.mjs <input.mp4> <new-output.mp4> [start] [end]');
try { await access(output); throw new Error('Output exists.'); } catch(e) { if(e.code!=='ENOENT')throw e; }
const commands=[],from=Number(start),to=Number(end);
for(let n=Math.round(from*24);n<=Math.round(to*24);n++){
  const t=n/24,p=Math.min(1,(t-from)/(to-from)),ease=p*p*(3-2*p);
  commands.push(`${t.toFixed(6)} gblur@defocus sigma ${(120*ease).toFixed(3)}, gblur@defocus sigmaV ${(120*ease).toFixed(3)};`);
}
const file=output.replace('.mp4','-commands.txt');await writeFile(file,commands.join('\n'));
const result=spawnSync('ffmpeg',['-hide_banner','-loglevel','error','-i',input,'-vf',`sendcmd=f=${file},gblur@defocus=sigma=0:steps=3`,'-an','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',output],{encoding:'utf8'});
if(result.status!==0)throw new Error(result.stderr);
await unlink(file);
await writeFile(output.replace('.mp4','.json'),JSON.stringify({input,output,operation:'Locally authored continuous Gaussian defocus ramp over the same generated macro shot, no scene replacement.',start:from,end:to,sigma:120,commandRate:24},null,2)+'\n');console.log(output);
