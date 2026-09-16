import sharp from 'sharp';
import { writeFile } from 'node:fs/promises';
const [outgoing, incoming, output] = process.argv.slice(2);
if (!outgoing || !incoming || !output) throw new Error('Usage: node scripts/compare-seam.mjs <outgoing.png> <incoming.png> <output.jpg>');
const meta = await sharp(outgoing).metadata();
const inputs = await Promise.all([outgoing,incoming].map(file => sharp(file).resize(meta.width,meta.height,{fit:'fill'}).removeAlpha().raw().toBuffer()));
let absolute=0, squared=0;
for(let i=0;i<inputs[0].length;i++){const difference=inputs[0][i]-inputs[1][i];absolute+=Math.abs(difference);squared+=difference*difference;}
const width=640, height=Math.round(meta.height/meta.width*width);
const panels=await Promise.all([outgoing,incoming].map(file=>sharp(file).resize(width,height,{fit:'fill'}).png().toBuffer()));
await sharp({create:{width:width*2,height:height+32,channels:3,background:'#101820'}}).composite([
  {input:panels[0],left:0,top:32},{input:panels[1],left:width,top:32},
  {input:Buffer.from(`<svg width="1280" height="32"><text x="12" y="21" fill="#f2efe8" font-family="sans-serif" font-size="14">OUTGOING — exact final frame</text><text x="652" y="21" fill="#f2efe8" font-family="sans-serif" font-size="14">INCOMING — exact first frame</text></svg>`),left:0,top:0}
]).jpeg({quality:94}).toFile(output);
const report={outgoing,incoming,comparedDimensions:{width:meta.width,height:meta.height},meanAbsoluteRgbError:absolute/inputs[0].length,rootMeanSquareRgbError:Math.sqrt(squared/inputs[0].length),note:'Pixel errors use 0–255 channels after dimension alignment. These measurements support, but do not replace, visual seam inspection.'};
await writeFile(output.replace(/\.[^.]+$/,'.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
