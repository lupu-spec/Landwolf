import {publicRelease,releaseBundle} from './releases.ts';
import type {Release} from './releases.ts';
/** Narrow server-to-server bridge. No browser token, customer identity or host path. */
import {body,field,hash,InputError} from './common.ts';
import {expireRuns,runnerList,validateTarget} from './runners.ts';
import {handleTasks} from './tasks.ts';
type Connection={id:string;owner_id:string;runner_id:string};
type Dispatch={id:string;task_id:string;payload_hash:string};
const reply=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
async function detail(db:D1Database,c:Connection,d:Dispatch){
 const response=await handleTasks(new Request('https://factory.internal/api/tasks/'+d.task_id),db,c.owner_id,'');
 if(!response.ok)throw new InputError('Factory task unavailable.',502);
 const data=await response.json() as {task:{execution:{state:string;stage:string;message:string}|null;status:string};results:unknown[]};
 const release=await db.prepare('SELECT * FROM releases WHERE task_id=? AND owner_id=? ORDER BY created_at DESC LIMIT 1').bind(d.task_id,c.owner_id).first<Release>();
 // Delivery decisions survive newer queued/failed attempts. Keep the projection small:
 // full reports, manifests and source bytes are available only through their own routes.
 const history=await db.prepare("SELECT * FROM releases WHERE task_id=? AND owner_id=? AND state IN ('delivered','rolled_back') ORDER BY updated_at ASC,id ASC LIMIT 30").bind(d.task_id,c.owner_id).all<Release>();
 const releases=history.results.map(r=>{const report=JSON.parse(r.report);return {id:r.id,state:r.state,version:r.version,target:r.target,production_url:r.production_url,has_source:!!r.source_base64,source_sha256:r.source_sha256,artifact_sha256:r.artifact_sha256,report:{schema:report.schema,passed:report.passed,operation:report.operation,artifact_sha256:report.artifact_sha256}};});
 return {releases,release:release?publicRelease(release):null,id:d.id,task_id:d.task_id,state:data.task.execution?.state||data.task.status,stage:data.task.execution?.stage||'',message:data.task.execution?.message||'',result:data.results[0]||null};
}
export async function handlePortal(request:Request,db:D1Database):Promise<Response>{
 try{
  // These credentials are for servers only, never allowed in browser CORS flows.
  if(request.headers.has('Origin'))throw new InputError('Server connection required.',403);
  const token=request.headers.get('Authorization')?.match(/^Bearer ([A-Za-z0-9_-]{64})$/)?.[1];
  if(!token)throw new InputError('Unauthorized.',401);
  const c=await db.prepare('SELECT c.id,c.owner_id,c.runner_id FROM portal_connections c JOIN runners r ON r.id=c.runner_id AND r.owner_id=c.owner_id WHERE c.token_hash=? AND c.revoked=0 AND r.revoked=0').bind(await hash(token)).first<Connection>();
  if(!c)throw new InputError('Unauthorized.',401);
  const path=new URL(request.url).pathname;
  if(path==='/portal/targets'&&request.method==='GET'){
   const runners=(await runnerList(db,c.owner_id)).filter(r=>r.id===c.runner_id);
   return reply({runners});
  }
  const bundle=/^\/portal\/jobs\/([a-f0-9-]+)\/releases\/([a-f0-9-]+)\/source$/.exec(path);
  if(bundle&&request.method==='GET'){
   const r=await db.prepare("SELECT r.id FROM releases r JOIN portal_dispatches d ON d.task_id=r.task_id WHERE d.connection_id=? AND d.id=? AND r.id=? AND r.owner_id=? AND r.state='delivered'").bind(c.id,bundle[1],bundle[2],c.owner_id).first<{id:string}>();
   if(!r)throw new InputError('Delivered release not found.',404);
   return reply(await releaseBundle(db,r.id,c.owner_id));
  }
  const match=/^\/portal\/jobs\/([a-f0-9-]+)(\/cancel)?$/.exec(path);
  if(!match||!uuid.test(match[1]))throw new InputError('Not found.',404);
  const id=match[1];
  let existing=await db.prepare('SELECT id,task_id,payload_hash FROM portal_dispatches WHERE connection_id=? AND id=?').bind(c.id,id).first<Dispatch>();
  if(request.method==='PUT'&&!match[2]){
   const input=await body(request);
   if(Object.keys(input).some(k=>!['title','goal','acceptance','runtime','project_key'].includes(k)))throw new InputError('Unknown job field.');
   const title=field(input,'title',120,true),goal=field(input,'goal',12000,true),acceptance=field(input,'acceptance',6000),runtime=field(input,'runtime',10,true),project=field(input,'project_key',50,true);
   if(!['python','node','rust'].includes(runtime))throw new InputError('Invalid runtime.');
   const digest=await hash(JSON.stringify({title,goal,acceptance,runtime,project}));
   if(existing){if(existing.payload_hash!==digest)throw new InputError('Request already exists with different contents.',409);return reply(await detail(db,c,existing));}
   await expireRuns(db);
   await validateTarget(db,c.owner_id,c.runner_id,project,runtime);
   const taskId=crypto.randomUUID(),runId=crypto.randomUUID(),now=new Date().toISOString();
   await db.batch([
    db.prepare("INSERT INTO tasks(id,owner_id,title,goal,project,runtime,acceptance,created_at,updated_at,runner_id,project_key) SELECT ?,?,?,?,?,?,?,?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM portal_dispatches WHERE connection_id=? AND id=?) AND EXISTS(SELECT 1 FROM runners WHERE id=? AND owner_id=? AND revoked=0) AND (SELECT COUNT(*) FROM task_runs WHERE runner_id=? AND state IN ('queued','running'))<20 AND EXISTS(SELECT 1 FROM portal_connections WHERE id=? AND owner_id=? AND runner_id=? AND revoked=0)").bind(taskId,c.owner_id,title,goal,'CUSTOMER REQUEST',runtime,acceptance,now,now,c.runner_id,project,c.id,id,c.runner_id,c.owner_id,c.runner_id,c.id,c.owner_id,c.runner_id),
    db.prepare('INSERT INTO portal_dispatches(connection_id,id,task_id,payload_hash,created_at) SELECT ?,?,?,?,? WHERE changes()=1').bind(c.id,id,taskId,digest,now),
    db.prepare("INSERT INTO task_runs(id,task_id,owner_id,runner_id,state,created_at,sequence) SELECT ?,?,?,?,'queued',?,1 WHERE changes()=1").bind(runId,taskId,c.owner_id,c.runner_id,now),
    db.prepare("INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) SELECT ?,?,'submitted','OWNER-APPROVED CUSTOMER REQUEST.',?,1 WHERE changes()=1").bind(crypto.randomUUID(),taskId,now)
   ]);
   existing=await db.prepare('SELECT id,task_id,payload_hash FROM portal_dispatches WHERE connection_id=? AND id=?').bind(c.id,id).first<Dispatch>();
   if(!existing)throw new InputError('Runner unavailable or queue full.',409);
   if(existing.payload_hash!==digest)throw new InputError('Request already exists with different contents.',409);
   return reply(await detail(db,c,existing),201);
  }
  if(!existing)throw new InputError('Not found.',404);
  if(request.method==='GET'&&!match[2])return reply(await detail(db,c,existing));
  if(request.method==='POST'&&match[2]){
   const task=await db.prepare('SELECT status,revision FROM tasks WHERE id=? AND owner_id=?').bind(existing.task_id,c.owner_id).first<{status:string;revision:number}>();
   if(!task)throw new InputError('Not found.',404);
   if(task.status!=='cancelled'){
    const r=await handleTasks(new Request('https://factory.internal/api/tasks/'+existing.task_id,{method:'PATCH',headers:{'content-type':'application/json'},body:JSON.stringify({revision:task.revision,status:'cancelled'})}),db,c.owner_id,'');
    if(!r.ok)throw new InputError('Task changed. Refresh before cancelling.',409);
   }
   return reply(await detail(db,c,existing));
  }
  throw new InputError('Method not allowed.',405);
 }catch(e){if(e instanceof InputError)return reply({error:e.message},e.status);console.error('Portal bridge failed',e instanceof Error?e.name:'Unknown');return reply({error:'Factory unavailable. Retry the same request.'},503);}
}
