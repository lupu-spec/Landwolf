import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash,randomBytes} from 'node:crypto';
import {database} from './db.mjs';
import {handleMachine,handleRunnerSettings} from '../src/runners.ts';
import {handleTasks} from '../src/tasks.ts';
const hash=s=>createHash('sha256').update(s).digest('hex');
const req=(path,method,input,token)=>new Request('https://test.local'+path,{method,headers:{'content-type':'application/json',...(token?{authorization:'Bearer '+token}:{})},...(method==='GET'?{}:{body:JSON.stringify(input)})});
const task=(db,id='',method='GET',input={},user='alice')=>handleTasks(req('/api/tasks'+id,method,input),db,user,'https://test.local');
const machine=(db,token,path,input={})=>handleMachine(req(path,'POST',input,token),db);
async function setup(){
 const db=database(),token=randomBytes(48).toString('base64url');
 const r=await(await machine(db,null,'/runner/register',{name:'TEST',token_hash:hash(token)})).json();
 await handleRunnerSettings(req('/api/runners/pair','POST',{code:r.code}),db,'alice','');
 const health={ready:true,projects:[{id:'site',name:'SITE',runtimes:['node'],checks:'acceptance',release:{target:'release-test',files:['src/main.js']}}]};
 await machine(db,token,'/runner/poll',health);
 const t=await(await task(db,'','POST',{title:'TEST',goal:'TEST',runtime:'node',runner_id:r.id,project_key:'site'})).json();
 const {run}=await(await machine(db,token,'/runner/poll',health)).json();
 await machine(db,token,`/runner/runs/${run.id}/finish`,{lease:run.lease,report:{schema:'l91.coding-run.v1',status:'VERIFIED_SANDBOX',independent_verification:true,verification_scope:'acceptance',rounds:[]},patch:'--- a/src/main.js\n+++ b/src/main.js\n@@ -1 +1 @@\n-old\n+new\n'});
 assert.equal((await task(db,'/'+t.id,'PATCH',{revision:2,status:'approved'})).status,200);
 const endpoint='/'+t.id+'/releases';
 return {db,token,taskId:t.id,endpoint,health};
}
async function build(s){const response=await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.0',files:['src/main.js']});assert.equal(response.status,201);return (await response.json()).release;}
async function claim(s){return (await(await machine(s.db,s.token,'/runner/releases/poll')).json()).release;}
function evidence(job,extra={}){
 const manifest={'index.html':hash('HTML'),'_headers':hash('HEADERS')},source=Buffer.from('PK-test-zip-fixture');
 return {lease:job.lease,revision:job.revision,ok:true,preview_url:'https://aabbccdd.release-test.pages.dev',source_base64:source.toString('base64'),source_sha256:hash(source),manifest,report:{schema:'l91.release-checks.v1',passed:true,operation:job.operation,artifact_sha256:hash(JSON.stringify(Object.fromEntries(Object.entries(manifest).sort())))},previous_version:'0.9.0',previous_sha256:hash('previous'),...extra};
}
const finish=(s,job,input)=>machine(s.db,s.token,`/runner/releases/${job.id}/finish`,input||evidence(job));
test('approved release builds once, pins artifacts, publishes, delivers and privately downloads',async()=>{
 const s=await setup(),r=await build(s);
 const duplicate=await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.0',files:['src/main.js']});assert.equal(duplicate.status,200);assert.equal((await duplicate.json()).release.id,r.id);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:1})).status,409);
 const job=await claim(s);assert.equal((await claim(s)),null);
 assert.equal((await task(s.db,'/'+s.taskId,'PATCH',{revision:3,status:'changes_requested',note:'Change'})).status,409);
 assert.equal((await finish(s,job)).status,200);assert.equal((await finish(s,job)).status,200);
 let item=(await(await task(s.db,s.endpoint)).json()).releases[0];assert.equal(item.state,'preview_ready');assert.equal(item.lease,undefined);assert.equal(item.source_base64,undefined);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:item.revision,artifact_sha256:'0'.repeat(64)})).status,409);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:item.revision,artifact_sha256:item.artifact_sha256})).status,200);
 const publish=await claim(s);assert.equal(publish.operation,'publish');
 const proof=evidence(publish,{production_url:'https://release-test.pages.dev'});
 assert.equal((await finish(s,publish,{...proof,report:{...proof.report,artifact_sha256:'0'.repeat(64)}})).status,400);
 assert.equal((await finish(s,publish,proof)).status,200);
 item=(await(await task(s.db,s.endpoint)).json()).releases[0];assert.equal(item.state,'published');
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/deliver','POST',{revision:item.revision})).status,200);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/source')).status,200);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/source','GET',{},'bob')).status,404);
 assert.equal((await task(s.db,s.endpoint,'GET',{},'bob')).status,404);
 assert.equal((await(await task(s.db,s.endpoint)).json()).releases[0].state,'delivered');
});
test('failed checks and expired leases cannot publish; changed approval blocks a checked candidate',async()=>{
 const s=await setup(),r=await build(s),job=await claim(s);
 assert.equal((await finish(s,job,{lease:job.lease,revision:job.revision,ok:false,message:'CHECK FAILED'})).status,200);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:1})).status,409);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/retry','POST',{revision:1})).status,200);
 const retried=await claim(s);assert.equal(retried.id,r.id);assert.notEqual(retried.lease,job.lease);
 assert.equal((await finish(s,job)).status,404);
 await s.db.prepare("UPDATE releases SET lease_until='2000-01-01' WHERE id=?").bind(r.id).run();
 assert.equal((await finish(s,retried)).status,409);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/retry','POST',{revision:2})).status,200);
 const last=await claim(s);await finish(s,last);
 await task(s.db,'/'+s.taskId,'PATCH',{revision:3,status:'changes_requested',note:'New feedback'});
 const item=(await(await task(s.db,s.endpoint)).json()).releases[0];
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:item.revision,artifact_sha256:item.artifact_sha256})).status,409);
});
test('release input rejects arbitrary paths, targets, versions, files and unverified imported results',async()=>{
 const s=await setup();
 for(const change of [{version:'../main'},{files:['../secret']},{files:['package.json']},{files:[]},{revision:1}])assert.ok([400,409].includes((await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.0',files:['src/main.js'],...change})).status));
 await s.db.prepare("UPDATE task_results SET source='manual_import' WHERE task_id=?").bind(s.taskId).run();
 assert.equal((await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.0',files:['src/main.js']})).status,409);
});
test('hostile URLs and packages cannot become successful release evidence',async()=>{
 const s=await setup();await build(s);const job=await claim(s);
 for(const extra of [{preview_url:'https://evil.example/'},{preview_url:'https://release-test.pages.dev/'},{source_sha256:'0'.repeat(64)},{report:{schema:'l91.release-checks.v1',passed:false}},{manifest:{'../secret':'0'.repeat(64)}}])assert.equal((await finish(s,job,evidence(job,extra))).status,400);
 assert.equal((await finish(s,job)).status,200);
});
test('cancellation invalidates an in-flight build and rollback pins the earlier artifact',async()=>{
 const s=await setup(),r=await build(s),job=await claim(s);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/cancel','POST',{revision:1})).status,200);
 assert.equal((await finish(s,job)).status,404);
 assert.equal((await(await task(s.db,s.endpoint)).json()).releases[0].state,'cancelled');
 const s2=await setup(),r2=await build(s2),j2=await claim(s2);await finish(s2,j2);
 let item=(await(await task(s2.db,s2.endpoint)).json()).releases[0];
 await task(s2.db,s2.endpoint+'/'+r2.id+'/publish','POST',{revision:1,artifact_sha256:item.artifact_sha256});const pub=await claim(s2);await finish(s2,pub,evidence(pub,{production_url:'https://release-test.pages.dev'}));
 await task(s2.db,s2.endpoint+'/'+r2.id+'/rollback','POST',{revision:2});const undo=await claim(s2);
 assert.equal(undo.operation,'rollback');
 assert.equal((await finish(s2,undo,evidence(undo,{production_url:'https://release-test.pages.dev'}))).status,400);
 const ev=evidence(undo,{production_url:'https://release-test.pages.dev'});ev.report.artifact_sha256=hash('previous');
 assert.equal((await finish(s2,undo,ev)).status,200);
 assert.equal((await(await task(s2.db,s2.endpoint)).json()).releases[0].state,'rolled_back');
 assert.equal((await task(s2.db,s2.endpoint+'/'+r2.id+'/deliver','POST',{revision:3})).status,409);
});

test('a failed publication cannot retry over a newer published release',async()=>{
 const s=await setup(),old=await build(s);await finish(s,await claim(s));
 let r=(await(await task(s.db,s.endpoint)).json()).releases.find(x=>x.id===old.id);
 await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:r.revision,artifact_sha256:r.artifact_sha256});
 const j=await claim(s);await finish(s,j,{lease:j.lease,revision:j.revision,ok:false,message:'NETWORK FAILED'});
 const next=await(await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.1',files:['src/main.js']})).json();
 await finish(s,await claim(s));
 r=(await(await task(s.db,s.endpoint)).json()).releases.find(x=>x.id===next.release.id);
 await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:r.revision,artifact_sha256:r.artifact_sha256});
 const pub=await claim(s);await finish(s,pub,evidence(pub,{production_url:'https://release-test.pages.dev'}));
 assert.equal((await task(s.db,s.endpoint+'/'+old.id+'/retry','POST',{revision:2})).status,409);
 assert.equal(await claim(s),null);
});

test('source archive byte limit matches the customer download limit',async()=>{
 const s=await setup();await build(s);const job=await claim(s);
 for(const length of [500001,510000]){
  const source=Buffer.alloc(length,1);source.write('PK');
  assert.equal((await finish(s,job,evidence(job,{source_base64:source.toString('base64'),source_sha256:hash(source)}))).status,400);
  assert.equal((await(await task(s.db,s.endpoint)).json()).releases[0].state,'building');
 }
 const source=Buffer.alloc(500000,1);source.write('PK');
 assert.equal((await finish(s,job,evidence(job,{source_base64:source.toString('base64'),source_sha256:hash(source)}))).status,200);
});

test('portal delivery history retains delivered and rolled-back versions behind a queued attempt',async()=>{
 const {handlePortal}=await import('../src/portal.ts');
 const s=await setup(),r=await build(s),token=randomBytes(48).toString('base64url'),dispatch=crypto.randomUUID();
 const runner=await s.db.prepare('SELECT runner_id FROM releases WHERE id=?').bind(r.id).first();
 await s.db.prepare('INSERT INTO portal_connections(id,token_hash,owner_id,runner_id) VALUES(?,?,?,?)').bind('history-portal',hash(token),'alice',runner.runner_id).run();
 await s.db.prepare('INSERT INTO portal_dispatches(connection_id,id,task_id,payload_hash,created_at) VALUES(?,?,?,?,?)').bind('history-portal',dispatch,s.taskId,hash('request'),new Date().toISOString()).run();
 const detail=async()=>{const response=await handlePortal(req('/portal/jobs/'+dispatch,'GET',{},token),s.db);assert.equal(response.status,200);return response.json();};
 await finish(s,await claim(s));
 let item=(await(await task(s.db,s.endpoint)).json()).releases[0];
 await task(s.db,s.endpoint+'/'+r.id+'/publish','POST',{revision:item.revision,artifact_sha256:item.artifact_sha256});
 const pub=await claim(s);await finish(s,pub,evidence(pub,{production_url:'https://release-test.pages.dev'}));
 await task(s.db,s.endpoint+'/'+r.id+'/deliver','POST',{revision:2});
 const next=await(await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.1',files:['src/main.js']})).json();
 let data=await detail();assert.equal(data.release.id,next.release.id);assert.equal(data.release.state,'queued');
 assert.deepEqual(data.releases.map(x=>[x.id,x.state]),[[r.id,'delivered']]);
 for(const key of ['source_base64','lease','manifest','selected_files','runner_id'])assert.equal(key in data.releases[0],false);
 assert.equal((await task(s.db,s.endpoint+'/'+next.release.id+'/cancel','POST',{revision:1})).status,200);
 assert.equal((await task(s.db,s.endpoint+'/'+r.id+'/rollback','POST',{revision:3})).status,200);
 const undo=await claim(s),proof=evidence(undo,{production_url:'https://release-test.pages.dev'});proof.report.artifact_sha256=hash('previous');
 assert.equal((await finish(s,undo,proof)).status,200);
 assert.equal((await task(s.db,s.endpoint,'POST',{revision:3,version:'1.0.2',files:['src/main.js']})).status,201);
 data=await detail();assert.equal(data.release.state,'queued');assert.deepEqual(data.releases.map(x=>[x.id,x.state]),[[r.id,'rolled_back']]);
 assert.equal((await handlePortal(req('/portal/jobs/'+dispatch+'/releases/'+r.id+'/source','GET',{},token),s.db)).status,404);
});
