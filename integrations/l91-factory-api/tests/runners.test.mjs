import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes,createHash} from 'node:crypto';
import {database} from './db.mjs';
import {handleMachine,handleRunnerSettings} from '../src/runners.ts';
import {handleTasks} from '../src/tasks.ts';
const projects=[{id:'new',name:'NEW PROJECT',runtimes:['python','node'],checks:'syntax'}];
const report={schema:'l91.coding-run.v1',status:'SYNTAX_CHECKED',rounds:[{attempt:1,model:'test fixture',verification:{status:'PASSED',details:'Fixture for API tests'}}]};
const patch='--- a/src/main.py\n+++ b/src/main.py\n@@ -1 +1 @@\n-pass\n+print(1)\n';
function req(path,method='POST',input={},token){return new Request('https://test.local'+path,{method,headers:{'content-type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(method==='GET'?{}:{body:JSON.stringify(input)})});}
const machine=(db,token,path,input={})=>handleMachine(req(path,'POST',input,token),db);
const settings=(db,user,path,method='GET',input={})=>handleRunnerSettings(req(path,method,input),db,user,'https://test.local');
const task=(db,user,path='/api/tasks',method='GET',input={})=>handleTasks(req(path,method,input),db,user,'https://test.local');
async function register(db,name='IMAC'){const token=randomBytes(48).toString('base64url');const res=await machine(db,null,'/runner/register',{name,token_hash:createHash('sha256').update(token).digest('hex')});assert.equal(res.status,201);return {token,...await res.json()};}
async function paired(db,user='alice'){const r=await register(db);assert.equal((await settings(db,user,'/api/runners/pair','POST',{code:r.code})).status,200);await machine(db,r.token,'/runner/poll',{projects,ready:true});return r;}
async function create(db,r,user='alice'){const res=await task(db,user,'/api/tasks','POST',{title:'Runner task',goal:'Write a helper.',runtime:'python',runner_id:r.id,project_key:'new'});assert.equal(res.status,201);return (await res.json()).id;}
async function poll(db,r){return (await machine(db,r.token,'/runner/poll',{projects,ready:true})).json();}
async function detail(db,id){return (await task(db,'alice','/api/tasks/'+id)).json();}
const finish=(db,r,run,extra={})=>machine(db,r.token,`/runner/runs/${run.id}/finish`,{lease:run.lease,report,patch,...extra});
test('pairing is expiring, single-use, owner-scoped and hides credentials',async()=>{
 const db=database(),r=await register(db);
 assert.equal((await poll(db,r)).error,'Pair this machine from the website.');
 assert.equal((await settings(db,'alice','/api/runners/pair','POST',{code:r.code})).status,200);
 assert.equal((await settings(db,'bob','/api/runners/pair','POST',{code:r.code})).status,409);
 const visible=await(await settings(db,'alice','/api/runners')).json();
 assert.equal(visible.runners[0].id,r.id);assert.equal(JSON.stringify(visible).includes(r.token),false);assert.equal(visible.runners[0].token_hash,undefined);
 assert.equal((await(await settings(db,'bob','/api/runners')).json()).runners.length,0);
 const expired=await register(db);await db.prepare("UPDATE runners SET pair_expires='2000-01-01' WHERE id=?").bind(expired.id).run();
 assert.equal((await settings(db,'alice','/api/runners/pair','POST',{code:expired.code})).status,409);
 assert.equal((await machine(db,'bad','/runner/poll',{projects,ready:true})).status,401);
});
test('only explicit tasks for this owner and registered project can run',async()=>{
 const db=database(),r=await paired(db);
 await task(db,'alice','/api/tasks','POST',{title:'Old task',goal:'Do not run',runtime:'python'});
 for(const [user,project_key] of [['bob','new'],['alice','../../home']])assert.equal((await task(db,user,'/api/tasks','POST',{title:'Bad',goal:'No',runtime:'python',runner_id:r.id,project_key})).status,409);
 assert.equal((await poll(db,r)).run,null);
 const id=await create(db,r),run=(await poll(db,r)).run;assert.equal(run.task.id,id);assert.equal(run.task.project_key,'new');
 assert.equal((await poll(db,r)).run,null);
 const d=await detail(db,id);assert.equal(d.task.execution.state,'running');assert.equal(d.task.execution.lease,undefined);
});
test('one runner claims only one job even when polled concurrently',async()=>{
 const db=database(),r=await paired(db);await create(db,r);await create(db,r);
 const runs=await Promise.all([poll(db,r),poll(db,r),poll(db,r)]);
 assert.equal(runs.filter(x=>x.run).length,1);
});
test('heartbeat renews a lease and cancellation rejects late output',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r),run=(await poll(db,r)).run;
 const heartbeat=()=>machine(db,r.token,`/runner/runs/${run.id}/heartbeat`,{lease:run.lease,stage:'testing'});
 assert.equal((await heartbeat()).status,200);assert.equal((await detail(db,id)).task.execution.stage,'testing');
 assert.equal((await task(db,'alice',`/api/tasks/${id}`,'PATCH',{revision:1,status:'cancelled'})).status,200);
 assert.equal((await heartbeat()).status,409);assert.equal((await finish(db,r,run)).status,409);assert.equal((await detail(db,id)).results.length,0);
});
test('active runs cannot be archived or overwritten by manual uploads',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r);
 assert.equal((await task(db,'alice',`/api/tasks/${id}`,'PATCH',{revision:1,archived:true})).status,409);
 assert.equal((await task(db,'alice',`/api/tasks/${id}/results`,'POST',{revision:1,report,patch})).status,409);
});
test('expired lease fails visibly; old output cannot replace a retry',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r),old=(await poll(db,r)).run;
 await db.prepare("UPDATE task_runs SET lease_until='2000-01-01' WHERE id=?").bind(old.id).run();
 assert.equal((await detail(db,id)).task.execution.state,'failed');
 assert.equal((await task(db,'alice',`/api/tasks/${id}/run`,'POST',{revision:1})).status,201);
 const current=(await poll(db,r)).run;assert.notEqual(current.id,old.id);
 assert.equal((await finish(db,r,old)).status,409);assert.equal((await finish(db,r,current)).status,200);
});
test('result transfer is idempotent and stores provenance, exact code and review event',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r),run=(await poll(db,r)).run;
 assert.equal((await finish(db,r,run)).status,200);assert.equal((await finish(db,r,run)).status,200);
 const d=await detail(db,id);assert.equal(d.task.status,'review_ready');assert.equal(d.task.revision,2);assert.equal(d.results.length,1);assert.equal(d.results[0].source,'local_runner');assert.equal(d.results[0].patch,patch);assert.deepEqual(d.results[0].report,report);assert.equal(d.events.at(-1).kind,'runner_result');
 assert.equal((await finish(db,r,run,{patch:patch+'extra'})).status,409);
});
test('malformed results do not consume a lease or corrupt task state',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r),run=(await poll(db,r)).run;
 for(const extra of [{report:{}},{patch:'not a patch'},{report:{...report,rounds:[{verification:{details:{bad:true}}}]}}])assert.equal((await finish(db,r,run,extra)).status,400);
 assert.equal((await detail(db,id)).task.execution.state,'running');
 assert.equal((await finish(db,r,run)).status,200);
});
test('failure without code remains retryable with diagnostic evidence',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r),run=(await poll(db,r)).run;
 assert.equal((await finish(db,r,run,{patch:'',report:{...report,status:'FAILED_OR_BLOCKED'}})).status,200);
 const d=await detail(db,id);assert.equal(d.task.status,'queued');assert.equal(d.task.execution.state,'failed');assert.equal(d.results[0].report.status,'FAILED_OR_BLOCKED');
 assert.equal((await task(db,'alice',`/api/tasks/${id}/run`,'POST',{revision:2})).status,201);
});
test('revocation is owner-scoped, cancels jobs and invalidates the credential',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r);await poll(db,r);
 assert.equal((await settings(db,'bob',`/api/runners/${r.id}`,'DELETE')).status,404);
 assert.equal((await settings(db,'alice',`/api/runners/${r.id}`,'DELETE')).status,200);
 assert.equal((await machine(db,r.token,'/runner/poll',{projects,ready:true})).status,401);
 assert.equal((await detail(db,id)).task.execution.state,'cancelled');
});
test('another runner cannot heartbeat or finish another machine job',async()=>{
 const db=database(),a=await paired(db),b=await paired(db,'bob');await create(db,a);const run=(await poll(db,a)).run;
 assert.equal((await machine(db,b.token,`/runner/runs/${run.id}/heartbeat`,{lease:run.lease,stage:'testing'})).status,404);
 assert.equal((await finish(db,b,run)).status,404);
});
test('review feedback reaches the next explicit run; unhealthy runners leave work queued',async()=>{
 const db=database(),r=await paired(db),id=await create(db,r);
 assert.equal((await(await machine(db,r.token,'/runner/poll',{projects,ready:false,issue:'DOCKER UNAVAILABLE'})).json()).run,null);
 const run=(await poll(db,r)).run;await finish(db,r,run);
 await task(db,'alice',`/api/tasks/${id}`,'PATCH',{revision:2,status:'changes_requested',note:'Handle empty input.'});
 assert.equal((await poll(db,r)).run,null);
 assert.equal((await task(db,'alice',`/api/tasks/${id}/run`,'POST',{revision:3})).status,201);
 assert.match((await poll(db,r)).run.feedback,/Handle empty input/);
});
