import {body,field,InputError,validateResult} from './common.ts';
import type {Run} from './runners.ts';
import {expireRuns,publicRun,queueRun,runnerList,validateTarget,newRun} from './runners.ts';
type Task = {id:string; owner_id:string; status:string; archived:number; revision:number; title:string; goal:string; project:string; runtime:string; acceptance:string; created_at:string; updated_at:string;runner_id:string|null;project_key:string};
const statuses = ['queued','review_ready','changes_requested','approved','cancelled'];
function publicTask(t:Task){const {owner_id,...visible}=t;return visible;}
function event(db:D1Database,id:string,kind:string,message:string,now:string){return db.prepare('INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) VALUES(?,?,?,?,?,1)').bind(crypto.randomUUID(),id,kind,message,now);}

// Authentication is performed by the entry point. Every task lookup includes owner_id.
export async function handleTasks(request:Request,db:D1Database,user:string,origin:string):Promise<Response>{
  const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json','access-control-allow-origin':origin,'vary':'Origin','cache-control':'no-store'}});
  try {
    const url=new URL(request.url),parts=url.pathname.split('/').filter(Boolean),id=parts[2],action=parts[3];
    if(parts.length>4)return reply({error:'Not found.'},404);
    if(!id&&request.method==='GET'){
      const offset=Number(url.searchParams.get('offset')||0);
      if(!Number.isSafeInteger(offset)||offset<0||offset>100000)throw new InputError('Invalid offset.');
      await expireRuns(db);
      const rows=await db.prepare('SELECT * FROM tasks WHERE owner_id=? ORDER BY created_at DESC,id DESC LIMIT 51 OFFSET ?').bind(user,offset).all<Task>();
      const tasks=rows.results.slice(0,50),ids=tasks.map(t=>t.id);
      const runs=ids.length?await db.prepare(`SELECT * FROM task_runs WHERE task_id IN (${ids.map(()=>'?').join(',')}) AND sequence=(SELECT MAX(x.sequence) FROM task_runs x WHERE x.task_id=task_runs.task_id)`).bind(...ids).all<Run>():{results:[]};
      const runners=await runnerList(db,user);
      return reply({tasks:tasks.map(t=>({...publicTask(t),execution:publicRun(runs.results.find(r=>r.task_id===t.id)||null)})),has_more:rows.results.length>50,runner:{connected:runners.some(r=>r.connected)}});
    }
    if(!id&&request.method==='POST'){
      const input=await body(request);const title=field(input,'title',120,true),goal=field(input,'goal',12000,true),project=field(input,'project',500),acceptance=field(input,'acceptance',6000),runtime=field(input,'runtime',10,true);
      if(!['python','node','rust'].includes(runtime))throw new InputError('Choose Python, Node.js, or Rust.');
      const taskId=crypto.randomUUID(),now=new Date().toISOString();
      const runnerId=field(input,'runner_id',50),projectKey=field(input,'project_key',50);
      if(runnerId)await validateTarget(db,user,runnerId,projectKey,runtime);
      await db.batch([db.prepare('INSERT INTO tasks(id,owner_id,title,goal,project,runtime,acceptance,created_at,updated_at,runner_id,project_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)').bind(taskId,user,title,goal,project,runtime,acceptance,now,now,runnerId||null,projectKey),event(db,taskId,'submitted',runnerId?'TASK SAVED AND QUEUED FOR YOUR LOCAL RUNNER.':'Task saved. Waiting for a local runner connection; execution has not started.',now),...(runnerId?[newRun(db,taskId,user,runnerId,1,now)]:[])]);
      return reply({id:taskId},201);
    }
    if(!id)return reply({error:'Method not allowed.'},405);
    await expireRuns(db);
    const task=await db.prepare('SELECT * FROM tasks WHERE id=? AND owner_id=?').bind(id,user).first<Task>();
    if(!task)return reply({error:'Task not found.'},404);
    const execution=await db.prepare('SELECT * FROM task_runs WHERE task_id=? ORDER BY sequence DESC LIMIT 1').bind(id).first<Run>();
    const active=execution&&['queued','running'].includes(String(execution.state));
    if(action==='run'&&request.method==='POST'){await queueRun(db,user,task,await body(request));return reply({ok:true},201);}
    if(!action&&request.method==='GET'){
      const [events,results]=await Promise.all([
        db.prepare('SELECT kind,message,created_at FROM task_events WHERE task_id=? ORDER BY task_revision').bind(id).all(),
        db.prepare('SELECT id,report,patch,sha256,created_at,source FROM task_results WHERE task_id=? ORDER BY task_revision DESC LIMIT 1').bind(id).all<{id:string;report:string;patch:string;sha256:string;created_at:string}>()
      ]);
      return reply({task:{...publicTask(task),execution:publicRun(execution)},events:events.results,results:results.results.map(r=>({...r,report:JSON.parse(r.report)}))});
    }
    if(action==='results'&&request.method==='POST'){
      if(active)throw new InputError('Cancel the current run before importing a result.',409);
      if(task.archived||!['queued','changes_requested','review_ready'].includes(task.status))throw new InputError('Reopen this task before importing a result.',409);
      const input=await body(request);
      if(input.revision!==task.revision)throw new InputError('This task changed. Refresh before importing.',409);
      const {report,reportText,patch}=validateResult(input);
      const count=await db.prepare('SELECT COUNT(*) AS count FROM task_results WHERE task_id=?').bind(id).first<{count:number}>();
      if((count?.count??0)>=20)throw new InputError('This task already has 20 result versions. Create a new task.',409);
      const now=new Date().toISOString(),resultId=crypto.randomUUID();
      const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify({report,patch})));
      const sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
      // Optimistic revision guard prevents an import from racing a cancel/review action.
      const changed=await db.batch([
        db.prepare("UPDATE tasks SET status='review_ready',revision=revision+1,updated_at=? WHERE id=? AND owner_id=? AND revision=?").bind(now,id,user,task.revision),
        db.prepare('INSERT INTO task_results(id,task_id,report,patch,sha256,created_at,task_revision) SELECT ?,?,?,?,?,?,? WHERE changes()=1').bind(resultId,id,reportText,patch,sha256,now,task.revision+1),
        db.prepare("INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) SELECT ?,?,'result_imported',?,?,? WHERE changes()=1").bind(crypto.randomUUID(),id,'Local result uploaded by you. Its claims have not been independently verified by this workspace.',now,task.revision+1)
      ]);
      if(changed[0].meta.changes!==1)throw new InputError('This task changed. Refresh and try again.',409);
      return reply({id:resultId},201);
    }
    if(!action&&request.method==='PATCH'){
      const input=await body(request);
      if(input.revision!==task.revision)throw new InputError('This task changed. Refresh and try again.',409);
      let status=task.status,archived=task.archived,message='',kind='';
      if(typeof input.archived==='boolean'){
        if(active)throw new InputError('Cancel the run before archiving this task.',409);
        if('status' in input)throw new InputError('Change status and archive separately.');
        archived=input.archived?1:0;message=archived?'Task archived.':'Task restored.';kind=archived?'archived':'restored';
      }else{
        if(task.archived)throw new InputError('Restore this task before changing it.',409);
        const next=input.status;if(typeof next!=='string'||!statuses.includes(next))throw new InputError('Invalid status.');
        const transitions:Record<string,string[]>={queued:['cancelled'],review_ready:['approved','changes_requested','cancelled'],changes_requested:['cancelled'],approved:['changes_requested'],cancelled:['queued']};
        if(!transitions[task.status]?.includes(next))throw new InputError('That status transition is not allowed.',409);
        if(next==='approved'||next==='changes_requested'){
          const hasResult=await db.prepare('SELECT id FROM task_results WHERE task_id=? LIMIT 1').bind(id).first();
          if(!hasResult)throw new InputError('A result is required before review.',409);
        }
        const note=field(input,'note',2000,next==='changes_requested');
        status=next;kind=next;message=next==='approved'?'Review approved by you. No code was applied, merged, or deployed.':next==='changes_requested'?`Changes requested: ${note}`:next==='queued'?'Task reopened. Waiting for runner.':'Task cancelled.';
      }
      const now=new Date().toISOString();
      const changed=await db.batch([
        db.prepare('UPDATE tasks SET status=?,archived=?,revision=revision+1,updated_at=? WHERE id=? AND owner_id=? AND revision=?').bind(status,archived,now,id,user,task.revision),
        db.prepare('INSERT INTO task_events(id,task_id,kind,message,created_at,task_revision) SELECT ?,?,?,?,?,? WHERE changes()=1').bind(crypto.randomUUID(),id,kind,message,now,task.revision+1),
        ...status==='cancelled'?[db.prepare("UPDATE task_runs SET state='cancelled',stage='stopped',message='TASK CANCELLED.',finished_at=? WHERE task_id=? AND owner_id=? AND state IN ('queued','running') AND EXISTS(SELECT 1 FROM tasks WHERE id=? AND status='cancelled')").bind(now,id,user,id)]:[]
      ]);
      if(changed[0].meta.changes!==1)throw new InputError('This task changed. Refresh and try again.',409);
      return reply({ok:true});
    }
    return reply({error:'Not found.'},404);
  }catch(error){if(error instanceof InputError)return reply({error:error.message},error.status);console.error('Task request failed',error instanceof Error?error.name:'Unknown');return reply({error:'Could not save or load the task. Please retry.'},500);}
}
