import { readFile, writeFile } from 'node:fs/promises';
const entry = JSON.parse(process.argv[2]);
if(!entry.jobId || !entry.id) throw new Error('Expected stable asset id and jobId');
const path = 'ASSETS.json';
const data = JSON.parse(await readFile(path,'utf8'));
data.generation.jobs ??= [];
let job = data.generation.jobs.find(j=>j.jobId===entry.jobId);
if(job) Object.assign(job,entry); else {job={...entry};data.generation.jobs.push(job);}
data.generation.jobsSubmitted=data.generation.jobs.length;
data.generation.estimatedCreditsSubmitted=data.generation.jobs.reduce((n,j)=>n+(j.estimatedCredits||0),0);
const planned=data.planned.find(a=>a.id===entry.id);
if(planned){planned.jobId=entry.jobId;planned.status=entry.status; if(entry.accepted) planned.acceptedVersion=entry.version||1;}
data.generation.referenceIds=data.generation.jobs.filter(j=>j.id==='identity'&&j.accepted).map(j=>j.jobId);
data.generation.acceptedVersions=data.generation.jobs.filter(j=>j.accepted).map(j=>({id:j.id,jobId:j.jobId,version:j.version||1,local: j.local}));
await writeFile(path,JSON.stringify(data,null,2)+'\n');
console.log(JSON.stringify({id:job.id,jobId:job.jobId,status:job.status,submitted:data.generation.jobsSubmitted,estimatedCreditsSubmitted:data.generation.estimatedCreditsSubmitted}));
