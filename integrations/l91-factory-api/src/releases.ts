import {body,field,hash,InputError} from './common.ts';

export type Release={id:string;task_id:string;owner_id:string;runner_id:string;project_key:string;result_id:string;result_sha256:string;task_revision:number;version:string;selected_files:string;target:string;state:string;operation:string;stage:string;message:string;revision:number;lease:string|null;lease_until:string|null;deadline:string|null;artifact_sha256:string|null;source_sha256:string|null;source_base64:string|null;manifest:string;report:string;preview_url:string|null;production_url:string|null;operation_seq:number;previous_sha256:string|null;previous_id:string|null;previous_version:string|null;finish_hash:string|null;delivered_at:string|null;created_at:string;updated_at:string};
type OwnerTask={id:string;owner_id:string;runner_id:string;project_key:string;status:string;archived:number;revision:number};
export type ReleaseProfile={target:string;files:string[]};
const running=['building','publishing','rolling_back'];
const stamp=()=>new Date().toISOString();
const later=(seconds:number)=>new Date(Date.now()+seconds*1000).toISOString();
const reply=(data:unknown,status=200,origin='')=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json','cache-control':'no-store','access-control-allow-origin':origin,'vary':'Origin'}});
const digest=/^[a-f0-9]{64}$/;
export const safeFile=(name:unknown):name is string=>typeof name==='string'&&name.length<180&&/^[a-zA-Z0-9_-][a-zA-Z0-9_./-]*$/.test(name)&&!name.split('/').some(p=>!p||p.startsWith('.'));
export function releaseProfile(value:unknown):ReleaseProfile|undefined{
 if(value===undefined)return undefined;
 const p=value as ReleaseProfile;
 if(!p||typeof p!=='object'||!/^[a-z0-9][a-z0-9-]{0,49}$/.test(p.target)||!Array.isArray(p.files)||!p.files.length||p.files.length>20||p.files.some(f=>!safeFile(f)))throw new InputError('Invalid release profile.');
 return {target:p.target,files:[...new Set(p.files)]};
}
export function publicRelease(r:Release){
 const {owner_id,lease,lease_until,deadline,source_base64,finish_hash,...visible}=r;
 return {...visible,selected_files:JSON.parse(r.selected_files),manifest:JSON.parse(r.manifest),report:JSON.parse(r.report),has_source:!!r.source_base64};
}
export async function expireReleases(db:D1Database){
 await db.prepare("UPDATE releases SET state='cancelled',message='APPROVAL CHANGED. CREATE A NEW RELEASE.',updated_at=? WHERE state IN ('queued','publish_queued') AND NOT EXISTS(SELECT 1 FROM tasks t WHERE t.id=releases.task_id AND t.owner_id=releases.owner_id AND t.status='approved' AND t.archived=0 AND t.revision=releases.task_revision)").bind(stamp()).run();
 await db.prepare("UPDATE releases SET state='failed',stage='stopped',message='RUNNER CONNECTION LOST. RETRY TO RECOVER THE SAME RELEASE.',updated_at=? WHERE state IN ('building','publishing','rolling_back') AND (lease_until<? OR deadline<?)").bind(stamp(),stamp(),stamp()).run();
}
export async function activeRelease(db:D1Database,taskId:string){return db.prepare("SELECT id FROM releases WHERE task_id=? AND state IN ('queued','building','publish_queued','publishing','rollback_queued','rolling_back')").bind(taskId).first();}
async function current(db:D1Database,r:Release){
 const t=await db.prepare("SELECT * FROM tasks WHERE id=? AND owner_id=? AND status='approved' AND archived=0 AND revision=?").bind(r.task_id,r.owner_id,r.task_revision).first();
 const latest=await db.prepare('SELECT id,sha256 FROM task_results WHERE task_id=? ORDER BY task_revision DESC LIMIT 1').bind(r.task_id).first<{id:string;sha256:string}>();
 if(!t||latest?.id!==r.result_id||latest.sha256!==r.result_sha256)throw new InputError('Approval changed. Review the latest result and create a new release.',409);
}
async function event(db:D1Database,r:Release,state:string,message:string){
 return db.prepare('INSERT INTO release_events(id,release_id,revision,state,message,created_at) SELECT ?,?,?,?,?,? WHERE changes()=1').bind(crypto.randomUUID(),r.id,r.revision+1,state,message,stamp());
}
export async function listReleases(db:D1Database,taskId:string,user:string){
 await expireReleases(db);
 const rows=await db.prepare('SELECT * FROM releases WHERE task_id=? AND owner_id=? ORDER BY created_at DESC,id DESC LIMIT 30').bind(taskId,user).all<Release>();
 return rows.results.map(publicRelease);
}
export async function releaseBundle(db:D1Database,id:string,user:string){
 const r=await db.prepare('SELECT * FROM releases WHERE id=? AND owner_id=?').bind(id,user).first<Release>();
 if(!r?.source_base64)throw new InputError('Source package not available.',404);
 return {name:`source-${r.version}.zip`,base64:r.source_base64,sha256:r.source_sha256};
}
export async function handleReleases(request:Request,db:D1Database,user:string,task:OwnerTask,action:string|undefined,origin:string){
 try{
  await expireReleases(db);
  const path=new URL(request.url).pathname.split('/').filter(Boolean),releaseId=path[4],verb=path[5];
  if(path.length>6)throw new InputError('Not found.',404);
  const runner=await db.prepare('SELECT capabilities FROM runners WHERE id=? AND owner_id=? AND revoked=0').bind(task.runner_id,user).first<{capabilities:string}>();
  const profile=runner?(JSON.parse(runner.capabilities) as Array<{id:string;release?:ReleaseProfile}>).find(p=>p.id===task.project_key)?.release:undefined;
  if(request.method==='GET'&&!releaseId)return reply({releases:await listReleases(db,task.id,user),profile:profile||null},200,origin);
  if(request.method==='POST'&&!releaseId){
   const input=await body(request),version=field(input,'version',40,true),files=input.files;
   if(!/^\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(version))throw new InputError('Use a version such as 1.0.2.');
   if(!profile)throw new InputError('Configure a release target on the local runner first.',409);
   if(task.status!=='approved'||task.archived||input.revision!==task.revision)throw new InputError('Approve the latest result before building a release.',409);
   if(!Array.isArray(files)||!files.length||files.length>20||files.some(f=>!safeFile(f)||!profile.files.includes(f))||new Set(files).size!==files.length)throw new InputError('Select only registered release files.');
   const result=await db.prepare('SELECT * FROM task_results WHERE task_id=? ORDER BY task_revision DESC LIMIT 1').bind(task.id).first<{id:string;sha256:string;source:string;report:string}>();
   const report=result?JSON.parse(result.report):null;
   if(!result||result.source!=='local_runner'||report.status!=='VERIFIED_SANDBOX'||report.independent_verification!==true||report.verification_scope!=='acceptance')throw new InputError('A verified local runner result with acceptance tests is required.',409);
   const prior=await db.prepare('SELECT * FROM releases WHERE owner_id=? AND runner_id=? AND project_key=? AND version=?').bind(user,task.runner_id,task.project_key,version).first<Release>();
   if(prior){if(prior.task_id===task.id&&prior.result_sha256===result.sha256&&prior.selected_files===JSON.stringify(files))return reply({release:publicRelease(prior)},200,origin);throw new InputError('Version already belongs to another release.',409);}
   if(await activeRelease(db,task.id))throw new InputError('A release is already running.',409);
   const projectBusy=await db.prepare("SELECT id FROM releases WHERE runner_id=? AND project_key=? AND state IN ('queued','building','publish_queued','publishing','rollback_queued','rolling_back')").bind(task.runner_id,task.project_key).first();
   if(projectBusy)throw new InputError('Another release for this project is active.',409);
   const count=await db.prepare('SELECT COUNT(*) AS n FROM releases WHERE task_id=?').bind(task.id).first<{n:number}>();
   if((count?.n||0)>=30)throw new InputError('This task has reached 30 releases.',409);
   const previous=await db.prepare("SELECT id,version FROM releases WHERE runner_id=? AND project_key=? AND state IN ('published','delivered') ORDER BY updated_at DESC LIMIT 1").bind(task.runner_id,task.project_key).first<{id:string;version:string}>();
   const id=crypto.randomUUID(),now=stamp();
   const inserted=await db.prepare("INSERT INTO releases(id,task_id,owner_id,runner_id,project_key,result_id,result_sha256,task_revision,version,selected_files,target,previous_id,previous_version,created_at,updated_at) SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM tasks WHERE id=? AND owner_id=? AND revision=? AND status='approved' AND archived=0)").bind(id,task.id,user,task.runner_id,task.project_key,result.id,result.sha256,task.revision,version,JSON.stringify(files),profile.target,previous?.id||null,previous?.version||null,now,now,task.id,user,task.revision).run();
   if(!inserted.meta.changes)throw new InputError('Approval changed. Refresh and retry.',409);
   return reply({release:publicRelease((await db.prepare('SELECT * FROM releases WHERE id=?').bind(id).first<Release>())!)},201,origin);
  }
  const r=await db.prepare('SELECT * FROM releases WHERE id=? AND task_id=? AND owner_id=?').bind(releaseId||'',task.id,user).first<Release>();
  if(!r)throw new InputError('Release not found.',404);
  if(request.method==='GET'&&verb==='source')return reply(await releaseBundle(db,r.id,user),200,origin);
  if(request.method!=='POST')throw new InputError('Not found.',404);
  const input=await body(request);
  if(input.revision!==r.revision)throw new InputError('Release changed. Refresh before continuing.',409);
  let state='',operation=r.operation,message='';
  if(verb==='publish'){
   await current(db,r);
   if(r.state!=='preview_ready'||!r.artifact_sha256||input.artifact_sha256!==r.artifact_sha256)throw new InputError('A tested preview and matching artifact are required.',409);
   if(!profile||profile.target!==r.target)throw new InputError('Release target changed.',409);
   const live=await db.prepare("SELECT id FROM releases WHERE runner_id=? AND project_key=? AND state IN ('published','delivered') ORDER BY updated_at DESC LIMIT 1").bind(r.runner_id,r.project_key).first<{id:string}>();
   if((live?.id||null)!==r.previous_id)throw new InputError('Another release was published after this preview. Build a new version.',409);
   state='publish_queued';operation='publish';message='WAITING TO PUBLISH';
  }else if(verb==='deliver'){
   await current(db,r);
   if(r.state==='delivered')return reply({ok:true},200,origin);
   if(r.state!=='published'||!r.production_url)throw new InputError('Verify the published release before delivery.',409);
   state='delivered';message='DELIVERED';
  }else if(verb==='rollback'){
   if(!['published','delivered'].includes(r.state)||!r.previous_version)throw new InputError('No previous release is available.',409);
   const newer=await db.prepare("SELECT id FROM releases WHERE runner_id=? AND project_key=? AND id<>? AND state IN ('published','delivered') AND updated_at>?").bind(r.runner_id,r.project_key,r.id,r.updated_at).first();
   if(newer)throw new InputError('A newer release is live. Open that release to roll back.',409);
   state='rollback_queued';operation='rollback';message='WAITING TO RESTORE PREVIOUS RELEASE';
  }else if(verb==='retry'){
   await current(db,r);
   if(r.state!=='failed')throw new InputError('Only failed releases can be retried.',409);
   state=operation==='build'?'queued':operation==='publish'?'publish_queued':'rollback_queued';message='WAITING FOR RUNNER';
  }else if(verb==='cancel'){
   if(!['queued','building','preview_ready','publish_queued'].includes(r.state))throw new InputError('This release cannot be cancelled during publication.',409);
   state='cancelled';message='CANCELLED';
  }else throw new InputError('Not found.',404);
  if(['queued','publish_queued','rollback_queued'].includes(state)){const busy=await db.prepare("SELECT id FROM releases WHERE runner_id=? AND project_key=? AND id<>? AND state IN ('queued','building','publish_queued','publishing','rollback_queued','rolling_back')").bind(r.runner_id,r.project_key,r.id).first();if(busy)throw new InputError('Another release for this project is active.',409);}
  const changes=await db.batch([
   db.prepare('UPDATE releases SET state=?,operation=?,message=?,stage=?,revision=revision+1,operation_seq=?,finish_hash=NULL,updated_at=?,delivered_at=CASE WHEN ?=\'delivered\' THEN ? ELSE delivered_at END WHERE id=? AND owner_id=? AND revision=?').bind(state,operation,message,state,verb==='retry'?r.operation_seq:r.revision+1,stamp(),state,stamp(),r.id,user,r.revision),
   await event(db,r,state,message)
  ]);
  if(changes[0].meta.changes!==1)throw new InputError('Release changed. Refresh and retry.',409);
  return reply({ok:true},200,origin);
 }catch(e){return failure(e,origin);}
}
function failure(e:unknown,origin=''){if(e instanceof InputError)return reply({error:e.message},e.status,origin);console.error('Release operation failed',e instanceof Error?e.name:'Unknown');return reply({error:'Release could not be saved. Refresh before retrying.'},503,origin);}
function checkedURL(value:unknown,target:string,production=false){
 if(typeof value!=='string')throw new InputError('Missing deployment URL.');
 let u:URL;try{u=new URL(value);}catch{throw new InputError('Invalid deployment URL.');}
 if(u.protocol!=='https:'||u.username||u.password||u.port||u.search||u.hash||u.pathname!=='/'||!(production?u.hostname===target+'.pages.dev':new RegExp('^[a-f0-9]{8,64}\\.'+target+'\\.pages\\.dev$').test(u.hostname)))throw new InputError('Unexpected deployment URL.');
 return u.origin;
}
export async function handleReleaseMachine(request:Request,db:D1Database,runner:{id:string;owner_id:string},input:Record<string,unknown>){
 try{
  await expireReleases(db);const path=new URL(request.url).pathname;
  if(path==='/runner/releases/poll'){
   const r=await db.prepare("SELECT * FROM releases WHERE runner_id=? AND owner_id=? AND state IN ('queued','publish_queued','rollback_queued') ORDER BY created_at LIMIT 1").bind(runner.id,runner.owner_id).first<Release>();
   if(!r)return reply({release:null});
   if(r.operation!=='rollback')await current(db,r);
   const lease=crypto.randomUUID(),state=r.operation==='build'?'building':r.operation==='publish'?'publishing':'rolling_back';
   const claimed=await db.prepare("UPDATE releases SET state=?,stage=?,lease=?,lease_until=?,deadline=?,updated_at=? WHERE id=? AND revision=? AND state=? AND NOT EXISTS(SELECT 1 FROM task_runs WHERE runner_id=? AND state='running') AND NOT EXISTS(SELECT 1 FROM releases WHERE runner_id=? AND state IN ('building','publishing','rolling_back')) RETURNING *").bind(state,state,lease,later(90),later(1200),stamp(),r.id,r.revision,r.state,runner.id,runner.id).first<Release>();
   if(!claimed)return reply({release:null});
   const result=await db.prepare('SELECT report,patch FROM task_results WHERE id=? AND task_id=? AND sha256=?').bind(r.result_id,r.task_id,r.result_sha256).first();
   return reply({release:{...publicRelease(claimed),lease,result}});
  }
  const match=/^\/runner\/releases\/([a-f0-9-]+)\/(heartbeat|finish)$/.exec(path);
  if(!match)throw new InputError('Not found.',404);
  const r=await db.prepare('SELECT * FROM releases WHERE id=? AND owner_id=? AND runner_id=?').bind(match[1],runner.owner_id,runner.id).first<Release>();
  if(!r||input.lease!==r.lease||input.revision!==r.revision)throw new InputError('Release not found.',404);
  const finishHash=match[2]==='finish'?await hash(JSON.stringify(input)):null;
  if(finishHash&&r.finish_hash===finishHash)return reply({ok:true});
  if(!running.includes(r.state)||!r.lease_until||r.lease_until<stamp()||!r.deadline||r.deadline<stamp())throw new InputError('Release lease expired or cancelled.',409);
  if(r.operation!=='rollback')await current(db,r);
  if(match[2]==='heartbeat'){
   const stage=field(input,'stage',40,true);
   if(!['building','testing','deploying_preview','checking_preview','publishing','checking_production','rolling_back','uploading'].includes(stage))throw new InputError('Invalid stage.');
   const heartbeat=await db.batch([db.prepare('UPDATE releases SET lease_until=?,stage=?,message=?,updated_at=? WHERE id=? AND revision=? AND state=? AND lease=? AND lease_until>? AND deadline>?').bind(later(90),stage,stage.replaceAll('_',' ').toUpperCase(),stamp(),r.id,r.revision,r.state,r.lease,stamp(),stamp()),db.prepare('UPDATE runners SET last_seen=? WHERE id=?').bind(stamp(),runner.id)]);
   if(heartbeat[0].meta.changes!==1)throw new InputError('Release changed or expired.',409);
   return reply({ok:true});
  }
  const success=input.ok===true;let state='failed',preview=r.preview_url,production=r.production_url,artifact=r.artifact_sha256,source=r.source_base64,sourceHash=r.source_sha256,manifest=r.manifest,report=r.report,previousVersion=r.previous_version,previousHash=r.previous_sha256;
  const message=success?(r.operation==='build'?'PREVIEW CHECKED':r.operation==='publish'?'PUBLISHED AND CHECKED':'PREVIOUS RELEASE RESTORED'):field(input,'message',300,true);
  if(success){
   const evidence=input.report as Record<string,unknown>;
   if(!evidence||evidence.schema!=='l91.release-checks.v1'||evidence.passed!==true||evidence.operation!==r.operation||typeof evidence.artifact_sha256!=='string'||!digest.test(evidence.artifact_sha256)||JSON.stringify(evidence).length>64000)throw new InputError('Verified release evidence is required.');
   report=JSON.stringify(evidence);
   if(r.operation==='build'){
    const m=input.manifest as Record<string,string>;
    if(!m||typeof m!=='object'||Array.isArray(m)||!Object.keys(m).length||Object.keys(m).length>500||Object.entries(m).some(([k,v])=>!safeFile(k)||!digest.test(v)))throw new InputError('Invalid artifact manifest.');
    manifest=JSON.stringify(m);artifact=evidence.artifact_sha256;
    if(await hash(JSON.stringify(Object.fromEntries(Object.entries(m).sort(([a],[b])=>a<b?-1:a>b?1:0))))!==artifact)throw new InputError('Artifact manifest hash mismatch.');
    preview=checkedURL(input.preview_url,r.target);
    source=field(input,'source_base64',700000,true);sourceHash=field(input,'source_sha256',64,true);
    if(!digest.test(sourceHash)||!/^[A-Za-z0-9+/]+={0,2}$/.test(source))throw new InputError('Invalid source package.');
    const bytes=Uint8Array.from(atob(source),c=>c.charCodeAt(0));const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(actual!==sourceHash||bytes[0]!==80||bytes[1]!==75)throw new InputError('Source package hash mismatch.');
    previousVersion=r.previous_version||(typeof input.previous_version==='string'&&/^\d+\.\d+\.\d+$/.test(input.previous_version)?input.previous_version:null);
    if(r.previous_id){const old=await db.prepare('SELECT artifact_sha256 FROM releases WHERE id=? AND owner_id=?').bind(r.previous_id,r.owner_id).first<{artifact_sha256:string}>();previousHash=old?.artifact_sha256||null;}else if(previousVersion){if(typeof input.previous_sha256!=='string'||!digest.test(input.previous_sha256))throw new InputError('Previous release fingerprint required.');previousHash=input.previous_sha256;}
    state='preview_ready';
   }else{
    if(r.operation==='publish'&&evidence.artifact_sha256!==r.artifact_sha256)throw new InputError('Published artifact differs from the checked preview.');
    if(r.operation==='rollback'&&evidence.artifact_sha256!==r.previous_sha256)throw new InputError('Restored artifact differs from the previous release.');
    production=checkedURL(input.production_url,r.target,true);state=r.operation==='publish'?'published':'rolled_back';
   }
  }
  const finished=await db.prepare('UPDATE releases SET state=?,stage=?,message=?,artifact_sha256=?,source_sha256=?,source_base64=?,manifest=?,report=?,preview_url=?,production_url=?,previous_version=?,previous_sha256=?,finish_hash=?,updated_at=? WHERE id=? AND revision=? AND lease=? AND state=? AND lease_until>? AND deadline>?').bind(state,state,message,artifact,sourceHash,source,manifest,report,preview,production,previousVersion,previousHash,finishHash,stamp(),r.id,r.revision,r.lease,r.state,stamp(),stamp()).run();
  if(finished.meta.changes!==1)throw new InputError('Release changed or expired.',409);
  return reply({ok:true});
 }catch(e){return failure(e);}
}
