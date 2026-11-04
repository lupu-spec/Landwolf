import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {handleTasks} from '../src/tasks.ts';
function database(){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../migrations/0001_init.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0002_tasks.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0003_revision_order.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0004_runner.sql',import.meta.url),'utf8'));
 // Run statements against real SQLite rather than matching SQL strings in a mock.
 const db={prepare(sql){const stmt=sqlite.prepare(sql);let values=[];return {bind(...v){values=v;return this;},async first(){return stmt.get(...values)||null;},async all(){return {results:stmt.all(...values)};},async run(){const r=stmt.run(...values);return {success:true,meta:{changes:Number(r.changes)}};}};},async batch(statements){sqlite.exec('BEGIN');try{const out=[];for(const stmt of statements)out.push(await stmt.run());sqlite.exec('COMMIT');return out;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
 return db;
}
const initial={title:'Clamp values',goal:'Keep input within bounds.',runtime:'python',project:'test-project',acceptance:'Reject invalid bounds.'};
const report={schema:'l91.coding-run.v1',status:'VERIFIED_SANDBOX',rounds:[{attempt:1,model:'test fixture',verification:{status:'PASSED',details:'Synthetic test fixture'}}]};
const patch='--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-return value\n+return min(value, maximum)\n';
async function request(db,user,path='/api/tasks',method='GET',input){return handleTasks(new Request('https://test.local'+path,{method,headers:{'content-type':'application/json'},...(input===undefined?{}:{body:JSON.stringify(input)})}),db,user,'https://test.local');}
async function create(db,user='alice'){const r=await request(db,user,'/api/tasks','POST',initial);assert.equal(r.status,201);return (await r.json()).id;}
async function detail(db,id,user='alice'){return (await request(db,user,'/api/tasks/'+id)).json();}
async function importResult(db,id,revision=1){return request(db,'alice',`/api/tasks/${id}/results`,'POST',{report,patch,revision});}
test('new task persists queued with honest event and no runner connection',async()=>{const db=database(),id=await create(db);const x=await detail(db,id);assert.equal(x.task.status,'queued');assert.equal(x.task.owner_id,undefined);assert.match(x.events[0].message,/execution has not started/);assert.deepEqual(x.results,[]);const list=await(await request(db,'alice')).json();assert.equal(list.tasks[0].id,id);assert.equal(list.runner.connected,false);});
test('cross-user listing, reading, reviewing and importing are denied',async()=>{const db=database(),id=await create(db);assert.equal((await(await request(db,'bob')).json()).tasks.length,0);for(const [method,path,payload] of [['GET',`/api/tasks/${id}`],['PATCH',`/api/tasks/${id}`,{status:'cancelled',revision:1}],['POST',`/api/tasks/${id}/results`,{report,patch,revision:1}]]){assert.equal((await request(db,'bob',path,method,payload)).status,404);}assert.equal((await detail(db,id)).task.revision,1);});
test('valid import preserves original artifacts and hashes them; approval records review only',async()=>{const db=database(),id=await create(db);assert.equal((await importResult(db,id)).status,201);let x=await detail(db,id);assert.equal(x.task.status,'review_ready');assert.equal(x.task.revision,2);assert.deepEqual(x.results[0].report,report);assert.equal(x.results[0].patch,patch);assert.match(x.results[0].sha256,/^[0-9a-f]{64}$/);assert.equal(x.results[0].source,'manual_import');assert.match(x.events.at(-1).message,/not been independently verified/);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'approved',revision:2})).status,200);x=await detail(db,id);assert.equal(x.task.status,'approved');assert.match(x.events.at(-1).message,/No code was applied/);});
test('cannot claim running/completed or approve task without result',async()=>{const db=database(),id=await create(db);for(const status of ['running','complete','approved','review_ready'])assert.ok((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status,revision:1})).status>=400);assert.equal((await detail(db,id)).task.status,'queued');});
test('revision feedback, re-import, cancellation, archive and restore are recorded',async()=>{const db=database(),id=await create(db);await importResult(db,id);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'changes_requested',revision:2})).status,400);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'changes_requested',revision:2,note:'Add an edge-case test.'})).status,200);assert.equal((await importResult(db,id,3)).status,201);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{archived:true,revision:4})).status,200);assert.equal((await importResult(db,id,5)).status,409);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{archived:false,revision:5})).status,200);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'cancelled',revision:6})).status,200);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'queued',revision:7})).status,200);const x=await detail(db,id);assert.equal(x.task.status,'queued');assert.equal(x.task.archived,0);assert.ok(x.events.some(e=>e.message.includes('edge-case')));});
test('stale changes fail without adding events or replacing result',async()=>{const db=database(),id=await create(db);await importResult(db,id);const before=await detail(db,id);assert.equal((await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'cancelled',revision:1})).status,409);assert.equal((await importResult(db,id,1)).status,409);assert.deepEqual(await detail(db,id),before);});
test('validates task fields and runtime',async()=>{const db=database();for(const bad of [{...initial,title:' '},{...initial,runtime:'shell'},{...initial,goal:'x'.repeat(12001)},{...initial,project:{url:'bad'}}])assert.equal((await request(db,'alice','/api/tasks','POST',bad)).status,400);assert.equal((await(await request(db,'alice')).json()).tasks.length,0);});
test('rejects malformed and oversized imports and structured verifier text',async()=>{const db=database(),id=await create(db);for(const bad of [{report:{},patch},{report,patch:'<script>bad</script>'},{report:{...report,rounds:[{verification:{details:{bad:true}}}]},patch},{report,patch:'--- a\n'+'x'.repeat(513000)}]){const r=await request(db,'alice',`/api/tasks/${id}/results`,'POST',{...bad,revision:1});assert.ok([400,413].includes(r.status));}assert.equal((await detail(db,id)).results.length,0);assert.equal((await request(db,'alice','/api/tasks','POST',{...initial,goal:'x'.repeat(901000)})).status,413);});
test('pagination is bounded, sorted and non-overlapping',async()=>{const db=database();for(let i=0;i<53;i++)await create(db);const a=await(await request(db,'alice')).json(),b=await(await request(db,'alice','/api/tasks?offset=50')).json();assert.equal(a.tasks.length,50);assert.equal(a.has_more,true);assert.equal(b.tasks.length,3);assert.equal(b.has_more,false);assert.equal(new Set([...a.tasks,...b.tasks].map(t=>t.id)).size,53);assert.equal((await request(db,'alice','/api/tasks?offset=-1')).status,400);});
test('existing notes are preserved by migration',async()=>{const db=database();await db.prepare('INSERT INTO notes(owner_id,content) VALUES(?,?)').bind('alice','Existing note').run();await create(db);assert.equal((await db.prepare('SELECT content FROM notes').first()).content,'Existing note');});
test('equal timestamps and reverse UUID order preserve review chronology and the latest result',async()=>{
 const db=database(),id=await create(db);
 await importResult(db,id);
 await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'changes_requested',revision:2,note:'Review another result.'});
 const latest={...report,status:'LATEST_RESULT'};
 assert.equal((await request(db,'alice',`/api/tasks/${id}/results`,'POST',{report:latest,patch,revision:3})).status,201);
 await request(db,'alice',`/api/tasks/${id}`,'PATCH',{status:'approved',revision:4});
 for(const table of ['task_events','task_results'])await db.prepare(`UPDATE ${table} SET created_at='2026-11-03T00:00:00.000Z',id=printf('%06d',10000-rowid)`).run();
 const saved=await detail(db,id);
 assert.deepEqual(saved.events.map(e=>e.kind),['submitted','result_imported','changes_requested','result_imported','approved']);
 assert.equal(saved.results.length,1);
 assert.equal(saved.results[0].report.status,'LATEST_RESULT');
});
test('revision-order migration preserves legacy event and result insertion order',()=>{
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../migrations/0001_init.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0002_tasks.sql',import.meta.url),'utf8'));
 sqlite.exec("INSERT INTO tasks(id,owner_id,title,goal,runtime,created_at,updated_at) VALUES('old','alice','Old','Goal','python','same','same')");
 const e=sqlite.prepare('INSERT INTO task_events(id,task_id,kind,message,created_at) VALUES(?,?,?,?,?)');
 e.run('z','old','submitted','Saved','same');e.run('b','old','result_imported','First','same');e.run('a','old','result_imported','Second','same');
 const r=sqlite.prepare('INSERT INTO task_results(id,task_id,report,patch,sha256,created_at) VALUES(?,?,?,?,?,?)');
 r.run('z','old','{}','first','hash','same');r.run('a','old','{}','second','hash','same');
 sqlite.exec(readFileSync(new URL('../migrations/0003_revision_order.sql',import.meta.url),'utf8'));
 assert.deepEqual(sqlite.prepare('SELECT id FROM task_events ORDER BY task_revision').all().map(x=>x.id),['z','b','a']);
 assert.equal(sqlite.prepare('SELECT patch FROM task_results ORDER BY task_revision DESC LIMIT 1').get().patch,'second');
 sqlite.close();
});
