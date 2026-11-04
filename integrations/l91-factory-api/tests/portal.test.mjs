import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes,createHash} from 'node:crypto';
import {database} from './db.mjs';
import {handlePortal} from '../src/portal.ts';
import {handleMachine,handleRunnerSettings} from '../src/runners.ts';
import {handleTasks} from '../src/tasks.ts';
const projects=[{id:'new',name:'NEW PROJECT',runtimes:['python'],checks:'syntax'}];
const req=(path,method='GET',data,token)=>new Request('https://test.local'+path,{method,headers:{'content-type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(data?{body:JSON.stringify(data)}:{})});
const digest=t=>createHash('sha256').update(t).digest('hex');
async function setup(){
 const db=database(),machine=randomBytes(48).toString('base64url'),token=randomBytes(48).toString('base64url');
 const r=await(await handleMachine(req('/runner/register','POST',{name:'Fixture',token_hash:digest(machine)}),db)).json();
 await handleRunnerSettings(req('/api/runners/pair','POST',{code:r.code}),db,'owner','');
 await handleMachine(req('/runner/poll','POST',{projects,ready:true},machine),db);
 await db.prepare('INSERT INTO portal_connections(id,token_hash,owner_id,runner_id) VALUES(?,?,?,?)').bind('portal',digest(token),'owner',r.id).run();
 return {db,token,machine,runner:r.id};
}
const payload={title:'Approved request',goal:'Return a small helper.',runtime:'python',project_key:'new',acceptance:'No external services.'};
const call=(s,path,method='GET',data,token=s.token)=>handlePortal(req(path,method,data,token),s.db);
test('server-only credential cannot access other factory APIs or cross connection jobs',async()=>{
 const s=await setup(),id=crypto.randomUUID();
 assert.equal((await call(s,'/portal/targets','GET',undefined,'bad')).status,401);
 const browser=req('/portal/targets','GET',undefined,s.token);browser.headers.set('Origin','https://landwolf.ai');
 assert.equal((await handlePortal(browser,s.db)).status,403);
 assert.equal((await call(s,'/portal/jobs/'+id,'PUT',{...payload,owner_id:'attacker'})).status,400);
 assert.equal((await call(s,'/portal/jobs/'+id,'PUT',payload)).status,201);
 const other=randomBytes(48).toString('base64url');
 await s.db.prepare('INSERT INTO portal_connections(id,token_hash,owner_id,runner_id) VALUES(?,?,?,?)').bind('other',digest(other),'owner',s.runner).run();
 assert.equal((await call(s,'/portal/jobs/'+id,'GET',undefined,other)).status,404);
 await s.db.prepare('UPDATE portal_connections SET revoked=1 WHERE id=?').bind('portal').run();
 assert.equal((await call(s,'/portal/targets')).status,401);
});
test('delivery replay creates exactly one task and run; changed content is rejected',async()=>{
 const s=await setup(),id=crypto.randomUUID(),path='/portal/jobs/'+id;
 const first=await(await call(s,path,'PUT',payload)).json();
 const second=await(await call(s,path,'PUT',payload)).json();
 assert.equal(first.task_id,second.task_id);
 assert.equal((await s.db.prepare('SELECT COUNT(*) AS n FROM task_runs').first()).n,1);
 assert.equal((await call(s,path,'PUT',{...payload,goal:'Different'})).status,409);
 const polled=await(await handleMachine(req('/runner/poll','POST',{projects,ready:true},s.machine),s.db)).json();
 assert.equal(polled.run.task.id,first.task_id);
 assert.equal((await(await call(s,path)).json()).state,'running');
 assert.equal((await call(s,path+'/cancel','POST',{})).status,200);
 assert.equal((await(await call(s,path)).json()).state,'cancelled');
 assert.equal((await call(s,path,'PUT',payload)).status,200);
 assert.equal((await s.db.prepare('SELECT COUNT(*) AS n FROM task_runs').first()).n,1);
});
test('target, owner, runtime and queue limits are enforced before dispatch',async()=>{
 const s=await setup();
 for(const change of [{project_key:'../../etc'},{runtime:'bash'},{project_key:'unregistered'}])assert.equal((await call(s,'/portal/jobs/'+crypto.randomUUID(),'PUT',{...payload,...change})).ok,false);
 for(let i=0;i<20;i++)assert.equal((await call(s,'/portal/jobs/'+crypto.randomUUID(),'PUT',payload)).status,201);
 assert.equal((await call(s,'/portal/jobs/'+crypto.randomUUID(),'PUT',payload)).status,409);
 await s.db.prepare('UPDATE runners SET revoked=1 WHERE id=?').bind(s.runner).run();
 assert.equal((await call(s,'/portal/targets')).status,401);
});
test('result is private and returned without runner leases or credentials',async()=>{
 const s=await setup(),id=crypto.randomUUID(),path='/portal/jobs/'+id;
 const created=await(await call(s,path,'PUT',payload)).json();
 const {run}=await(await handleMachine(req('/runner/poll','POST',{projects,ready:true},s.machine),s.db)).json();
 const report={schema:'l91.coding-run.v1',status:'SYNTAX_CHECKED',rounds:[]};
 assert.equal((await handleMachine(req('/runner/runs/'+run.id+'/finish','POST',{lease:run.lease,report,patch:'--- a/main.py\n+++ b/main.py\n@@ -1 +1 @@\n-pass\n+print(1)\n'},s.machine),s.db)).status,200);
 const result=await(await call(s,path)).json();
 assert.equal(result.state,'completed');assert.equal(result.result.report.status,'SYNTAX_CHECKED');
 assert.equal(JSON.stringify(result).includes(run.lease),false);
 assert.equal(JSON.stringify(result).includes(s.token),false);
 assert.equal((await handleTasks(req('/api/tasks/'+created.task_id),s.db,'other','')).status,404);
});
