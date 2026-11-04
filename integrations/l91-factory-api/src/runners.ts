import {body,field,hash,InputError,validateResult} from './common.ts';

type Runner={id:string;owner_id:string|null;name:string;token_hash:string;pair_hash:string|null;pair_expires:string|null;last_seen:string|null;capabilities:string;ready:number;issue:string;revoked:number};
type Project={id:string;name:string;runtimes:string[];checks:string};
export type Run={id:string;task_id:string;owner_id:string;runner_id:string;state:string;stage:string;message:string;lease:string|null;lease_until:string|null;deadline:string|null;result_hash:string|null;created_at:string;started_at:string|null;finished_at:string|null;sequence:number};
type Task={id:string;owner_id:string;runner_id:string|null;project_key:string;runtime:string;status:string;archived:number;revision:number;goal:string};
const now=()=>new Date().toISOString();
const after=(seconds:number)=>new Date(Date.now()+seconds*1000).toISOString();
const reply=(value:unknown,status=200,origin='')=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','cache-control':'no-store','access-control-allow-origin':origin,'vary':'Origin'}});
export function publicRun(r:Run|null){if(!r)return null;const {owner_id,lease,lease_until,deadline,result_hash,...visible}=r;return visible;}
export async function expireRuns(db:D1Database){await db.prepare("UPDATE task_runs SET state='failed',stage='stopped',message='CONNECTION LOST OR TIME LIMIT REACHED. RETRY THE TASK.',finished_at=? WHERE state='running' AND (lease_until<? OR deadline<?)").bind(now(),now(),now()).run();}
export async function runnerList(db:D1Database,user:string){
 const rows=await db.prepare('SELECT * FROM runners WHERE owner_id=? AND revoked=0 ORDER BY created_at').bind(user).all<Runner>();
 return rows.results.map(r=>({id:r.id,name:r.name,last_seen:r.last_seen,connected:!!r.last_seen&&Date.parse(r.last_seen)>Date.now()-45000,ready:!!r.ready,issue:r.issue,projects:JSON.parse(r.capabilities) as Project[]}));
}
export async function validateTarget(db:D1Database,user:string,runnerId:string,projectKey:string,runtime:string){
 const r=await db.prepare('SELECT * FROM runners WHERE id=? AND owner_id=? AND revoked=0').bind(runnerId,user).first<Runner>();
 if(!r)throw new InputError('Connect your local runner first.',409);
 const project=(JSON.parse(r.capabilities) as Project[]).find(p=>p.id===projectKey&&p.runtimes.includes(runtime));
 if(!project)throw new InputError('This project or runtime is not available on the selected runner.',409);
 const count=await db.prepare("SELECT COUNT(*) AS count FROM task_runs WHERE runner_id=? AND state IN ('queued','running')").bind(runnerId).first<{count:number}>();
 if((count?.count||0)>=20)throw new InputError('This runner has 20 waiting tasks. Finish or cancel some first.',409);
}
export function newRun(db:D1Database,taskId:string,user:string,runnerId:string,revision:number,timestamp:string){return db.prepare("INSERT INTO task_runs(id,task_id,owner_id,runner_id,state,created_at,sequence) VALUES(?,?,?,?,'queued',?,?)").bind(crypto.randomUUID(),taskId,user,runnerId,timestamp,revision);}
export async function queueRun(db:D1Database,user:string,task:Task,input:Record<string,unknown>){
 if(input.revision!==task.revision)throw new InputError('This task changed. Refresh and retry.',409);
 if(task.archived||!['queued','changes_requested'].includes(task.status)||!task.runner_id)throw new InputError('This task cannot be run. Create a new task with a connected runner.',409);
 await validateTarget(db,user,task.runner_id,task.project_key,task.runtime);
 const active=await db.prepare("SELECT id FROM task_runs WHERE task_id=? AND state IN ('queued','running')").bind(task.id).first();
 if(active)throw new InputError('This task is already queued or running.',409);
 const count=await db.prepare('SELECT COUNT(*) AS count FROM task_results WHERE task_id=?').bind(task.id).first<{count:number}>();
 if((count?.count||0)>=20)throw new InputError('Create a new task after 20 results.',409);
 const timestamp=now(),revision=task.revision+1;
 const result=await db.batch([
  db.prepare("UPDATE tasks SET status='queued',revision=revision+1,updated_at=? WHERE id=? AND owner_id=? AND revision=?").bind(timestamp,task.id,user,task.revision),
  db.prepare("INSERT INTO task_runs(id,task_id,owner_id,runner_id,state,created_at,sequence) SELECT ?,?,?,?,'queued',?,? WHERE changes()=1").bind(crypto.randomUUID(),task.id,user,task.runner_id,timestamp,revision),
  db.prepare("INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) SELECT ?,?,'queued','QUEUED FOR YOUR LOCAL RUNNER.',?,? WHERE changes()=1").bind(crypto.randomUUID(),task.id,timestamp,revision)
 ]);
 if(result[0].meta.changes!==1)throw new InputError('This task changed. Refresh and retry.',409);
}
function capabilities(value:unknown):Project[]{
 if(!Array.isArray(value)||value.length>20)throw new InputError('Invalid projects.');
 const seen=new Set();
 return value.map(p=>{if(!p||typeof p!=='object'||Array.isArray(p)||!/^[a-z0-9][a-z0-9-]{0,49}$/.test(p.id)||seen.has(p.id)||typeof p.name!=='string'||!p.name.trim()||p.name.length>100||!Array.isArray(p.runtimes)||!p.runtimes.length||p.runtimes.some((r:unknown)=>!['python','node','rust'].includes(String(r)))||!['syntax','acceptance'].includes(p.checks))throw new InputError('Invalid project.');seen.add(p.id);return {id:p.id,name:p.name,runtimes:[...new Set<string>(p.runtimes)],checks:p.checks};});
}
// Clerk-authenticated user controls. Runner credentials are never returned here.
export async function handleRunnerSettings(request:Request,db:D1Database,user:string,origin:string){
 try{
  const path=new URL(request.url).pathname;
  if(path==='/api/runners'&&request.method==='GET'){await expireRuns(db);return reply({runners:await runnerList(db,user)},200,origin);}
  if(path==='/api/runners/pair'&&request.method==='POST'){
   const input=await body(request),code=field(input,'code',30,true).replace(/[-\s]/g,'').toUpperCase();
   if(!/^[A-F0-9]{16}$/.test(code))throw new InputError('Enter the 16-character code shown by the local runner.');
   const count=await db.prepare('SELECT COUNT(*) AS count FROM runners WHERE owner_id=? AND revoked=0').bind(user).first<{count:number}>();
   if((count?.count||0)>=5)throw new InputError('Disconnect an unused runner before adding another.',409);
   const r=await db.prepare('UPDATE runners SET owner_id=?,pair_hash=NULL,pair_expires=NULL WHERE pair_hash=? AND owner_id IS NULL AND revoked=0 AND pair_expires>? RETURNING id,name').bind(user,await hash(code),now()).first();
   if(!r)throw new InputError('Pairing code expired or already used. Generate a new code on the machine.',409);
   return reply({runner:r},200,origin);
  }
  const m=/^\/api\/runners\/([a-f0-9-]+)$/.exec(path);
  if(m&&request.method==='DELETE'){
   const result=await db.batch([
    db.prepare('UPDATE runners SET revoked=1,ready=0 WHERE id=? AND owner_id=? AND revoked=0').bind(m[1],user),
    db.prepare("UPDATE task_runs SET state='cancelled',stage='stopped',message='RUNNER DISCONNECTED.',finished_at=? WHERE runner_id=? AND owner_id=? AND state IN ('queued','running') AND EXISTS(SELECT 1 FROM runners WHERE id=? AND revoked=1)").bind(now(),m[1],user,m[1])
   ]);
   return reply(result[0].meta.changes?{ok:true}:{error:'Runner not found.'},result[0].meta.changes?200:404,origin);
  }
  return reply({error:'Not found.'},404,origin);
 }catch(e){return failure(e,origin);}
}
function failure(e:unknown,origin=''){if(e instanceof InputError)return reply({error:e.message},e.status,origin);console.error('Runner request failed',e instanceof Error?e.name:'Unknown');return reply({error:'Runner request failed. Please retry.'},500,origin);}
// Machine endpoints use a separate, revocable credential scoped to one owner and runner.
export async function handleMachine(request:Request,db:D1Database){
 try{
  const path=new URL(request.url).pathname;
  if(path==='/runner/register'&&request.method==='POST'){
   const input=await body(request),name=field(input,'name',80,true),tokenHash=field(input,'token_hash',64,true);
   if(!/^[a-f0-9]{64}$/.test(tokenHash))throw new InputError('Invalid registration.');
   const ip=await hash(request.headers.get('CF-Connecting-IP')||'unknown');
   await db.prepare('DELETE FROM runners WHERE owner_id IS NULL AND created_at<?').bind(after(-86400)).run();
   const count=await db.prepare('SELECT COUNT(*) AS count FROM runners WHERE registration_ip=? AND created_at>?').bind(ip,after(-3600)).first<{count:number}>();
   if((count?.count||0)>=10)throw new InputError('Too many pairing attempts. Try again in one hour.',429);
   const code=Array.from(crypto.getRandomValues(new Uint8Array(8)),b=>b.toString(16).padStart(2,'0')).join('').toUpperCase(),id=crypto.randomUUID();
   await db.prepare('INSERT INTO runners(id,name,token_hash,pair_hash,pair_expires,created_at,registration_ip) VALUES(?,?,?,?,?,?,?)').bind(id,name,tokenHash,await hash(code),after(600),now(),ip).run();
   return reply({id,code,expires_in:600},201);
  }
  const token=request.headers.get('Authorization')?.replace(/^Bearer /,'')||'';
  if(!/^[A-Za-z0-9_-]{64}$/.test(token))throw new InputError('Runner authentication required.',401);
  const runner=await db.prepare('SELECT * FROM runners WHERE token_hash=? AND revoked=0').bind(await hash(token)).first<Runner>();
  if(!runner)throw new InputError('Runner disconnected. Pair this machine again.',401);
  if(!runner.owner_id)throw new InputError(runner.pair_expires&&runner.pair_expires>now()?'Pair this machine from the website.':'Pairing expired. Generate a new code.',403);
  if(request.method!=='POST')return reply({error:'Method not allowed.'},405);
  const input=await body(request);
  if(path==='/runner/poll'){
   const projects=capabilities(input.projects),issue=field(input,'issue',200);
   if(typeof input.ready!=='boolean')throw new InputError('Invalid health.');
   await db.prepare('UPDATE runners SET last_seen=?,capabilities=?,ready=?,issue=? WHERE id=? AND revoked=0').bind(now(),JSON.stringify(projects),input.ready?1:0,issue,runner.id).run();
   await expireRuns(db);
   if(!input.ready)return reply({run:null});
   const lease=crypto.randomUUID();
   const run=await db.prepare("UPDATE task_runs SET state='running',stage='generating',message='WRITING CODE ON YOUR MACHINE.',lease=?,lease_until=?,deadline=?,started_at=? WHERE id=(SELECT j.id FROM task_runs j JOIN tasks t ON t.id=j.task_id WHERE j.runner_id=? AND j.owner_id=? AND j.state='queued' AND t.status='queued' AND t.archived=0 AND NOT EXISTS(SELECT 1 FROM task_runs WHERE runner_id=? AND state='running') ORDER BY j.created_at,j.id LIMIT 1) AND state='queued' AND EXISTS(SELECT 1 FROM runners WHERE id=? AND revoked=0) RETURNING *").bind(lease,after(90),after(900),now(),runner.id,runner.owner_id,runner.id,runner.id).first<Run>();
   if(!run)return reply({run:null});
   const task=await db.prepare('SELECT id,title,goal,acceptance,runtime,project,project_key FROM tasks WHERE id=? AND owner_id=?').bind(run.task_id,runner.owner_id).first();
   const feedback=await db.prepare("SELECT message FROM task_events WHERE task_id=? AND kind='changes_requested' ORDER BY task_revision DESC LIMIT 1").bind(run.task_id).first();
   return reply({run:{id:run.id,lease,task,feedback:feedback?.message||''}});
  }
  const m=/^\/runner\/runs\/([a-f0-9-]+)\/(heartbeat|finish)$/.exec(path);
  if(!m)return reply({error:'Not found.'},404);
  const run=await db.prepare('SELECT * FROM task_runs WHERE id=? AND runner_id=? AND owner_id=?').bind(m[1],runner.id,runner.owner_id).first<Run>();
  if(!run||input.lease!==run.lease)throw new InputError('Run not found.',404);
  if(m[2]==='heartbeat'){
   if(!['generating','testing','uploading'].includes(String(input.stage)))throw new InputError('Invalid stage.');
   const messages:Record<string,string>={generating:'WRITING CODE ON YOUR MACHINE.',testing:'RUNNING CHECKS ON YOUR MACHINE.',uploading:'SENDING RESULTS TO THE WEBSITE.'};
   const updated=await db.batch([
    db.prepare("UPDATE task_runs SET lease_until=?,stage=?,message=? WHERE id=? AND state='running' AND lease_until>? AND deadline>? AND EXISTS(SELECT 1 FROM tasks WHERE id=? AND owner_id=? AND status='queued' AND archived=0)").bind(after(90),input.stage,messages[String(input.stage)],run.id,now(),now(),run.task_id,runner.owner_id),
    db.prepare('UPDATE runners SET last_seen=? WHERE id=?').bind(now(),runner.id)
   ]);
   if(!updated[0].meta.changes)throw new InputError('Run cancelled or lease expired.',409);
   return reply({ok:true});
  }
  const {report,reportText,patch}=validateResult(input,true),resultHash=await hash(JSON.stringify({report,patch}));
  if(['completed','failed'].includes(run.state)&&run.result_hash===resultHash)return reply({ok:true});
  if(run.state!=='running'||!run.lease_until||run.lease_until<=now()||!run.deadline||run.deadline<=now())throw new InputError('Run cancelled or lease expired.',409);
  const task=await db.prepare("SELECT * FROM tasks WHERE id=? AND owner_id=? AND status='queued' AND archived=0").bind(run.task_id,runner.owner_id).first<Task>();
  if(!task)throw new InputError('Task changed. Result was not saved.',409);
  const timestamp=now(),hasPatch=!!patch.trim();
  const message=hasPatch?'RESULT RETURNED FROM YOUR LOCAL RUNNER. REVIEW THE CODE AND CHECKS.':'RUN STOPPED WITHOUT CODE CHANGES. OPEN CODE FOR DETAILS OR RETRY.';
  const changed=await db.batch([
   db.prepare("UPDATE task_runs SET state=?,stage='finished',message=?,finished_at=?,result_hash=? WHERE id=? AND state='running' AND lease=? AND lease_until>? AND EXISTS(SELECT 1 FROM tasks WHERE id=? AND revision=? AND status='queued' AND archived=0) AND EXISTS(SELECT 1 FROM runners WHERE id=? AND revoked=0)").bind(hasPatch?'completed':'failed',message,timestamp,resultHash,run.id,run.lease,timestamp,task.id,task.revision,runner.id),
   db.prepare('UPDATE tasks SET status=?,revision=revision+1,updated_at=? WHERE id=? AND revision=? AND changes()=1').bind(hasPatch?'review_ready':'queued',timestamp,task.id,task.revision),
   db.prepare("INSERT INTO task_results(id,task_id,report,patch,sha256,created_at,task_revision,source) SELECT ?,?,?,?,?,?,?,'local_runner' WHERE changes()=1").bind(run.id,task.id,reportText,patch,resultHash,timestamp,task.revision+1),
   db.prepare("INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) SELECT ?,?,'runner_result',?,?,? WHERE changes()=1").bind(crypto.randomUUID(),task.id,message,timestamp,task.revision+1)
  ]);
  if(changed[0].meta.changes!==1)throw new InputError('Task changed. Result was not saved.',409);
  return reply({ok:true});
 }catch(e){return failure(e);}
}
