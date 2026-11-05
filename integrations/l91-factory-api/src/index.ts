import {handlePortal} from './portal.ts';
import {handleMachine,handleRunnerSettings} from './runners.ts';
import {createRemoteJWKSet, jwtVerify} from 'jose';
import {handleTasks} from './tasks.ts';
interface Env {DATABASE:D1Database; CLERK_JWKS_URL:string; CLERK_ISSUER:string; ALLOWED_ORIGIN:string;}
const json=(value:unknown,status=200,origin='')=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','access-control-allow-origin':origin,'vary':'Origin','cache-control':'no-store'}});
export default {async fetch(request:Request,env:Env):Promise<Response>{
  const origin=request.headers.get('Origin')||'';
  const allowed=(env.ALLOWED_ORIGIN||'').split(',').map(s=>s.trim());
  const cors=allowed.includes(origin)?origin:'';
  if(request.method==='OPTIONS')return new Response(null,{status:cors?204:403,headers:{'access-control-allow-origin':cors,'access-control-allow-headers':'Authorization, Content-Type','access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS','vary':'Origin'}});
  if(origin&&!cors)return json({error:'origin forbidden'},403);
  const url=new URL(request.url);
  if(url.pathname==='/health')return json({ok:true,version:"0.5.1"},200,cors);
  if(url.pathname.startsWith('/portal/'))return handlePortal(request,env.DATABASE);
  if(url.pathname.startsWith('/runner/'))return handleMachine(request,env.DATABASE);
  if(!url.pathname.startsWith('/api/runners') && !url.pathname.startsWith('/api/notes') && !/^\/api\/tasks(?:\/|$)/.test(url.pathname))return json({error:'not found'},404,cors);
  const auth=request.headers.get('authorization');
  if(!auth?.startsWith('Bearer ')||!env.CLERK_JWKS_URL||!env.CLERK_ISSUER)return json({error:'unauthorized'},401,cors);
  let user:string;
  try{const {payload}=await jwtVerify(auth.slice(7),createRemoteJWKSet(new URL(env.CLERK_JWKS_URL)),{issuer:env.CLERK_ISSUER});if(typeof payload.sub!=='string'||!payload.sub)throw new Error('no user');user=payload.sub;}
  catch{return json({error:'unauthorized'},401,cors);}
  if(/^\/api\/runners(?:\/|$)/.test(url.pathname))return handleRunnerSettings(request,env.DATABASE,user,cors);
  if(/^\/api\/tasks(?:\/|$)/.test(url.pathname)) return handleTasks(request,env.DATABASE,user,cors);
  if(url.pathname==='/api/notes'&&request.method==='GET'){
    const rows=await env.DATABASE.prepare('SELECT id,content,created_at FROM notes WHERE owner_id=? ORDER BY id DESC LIMIT 100').bind(user).all();return json({notes:rows.results},200,cors);
  }
  if(url.pathname==='/api/notes'&&request.method==='POST'){
    let body:unknown;try{body=await request.json();}catch{return json({error:'invalid JSON'},400,cors);}
    const content=(body as {content?:unknown})?.content;
    if(typeof content!=='string'||!content.trim()||content.length>500)return json({error:'content must be 1-500 characters'},400,cors);
    await env.DATABASE.prepare('INSERT INTO notes(owner_id,content) VALUES(?,?)').bind(user,content.trim()).run();return json({ok:true},201,cors);
  }
  const match=/^\/api\/notes\/(\d+)$/.exec(url.pathname);
  if(match&&request.method==='DELETE'){
    await env.DATABASE.prepare('DELETE FROM notes WHERE id=? AND owner_id=?').bind(Number(match[1]),user).run();return json({ok:true},200,cors);
  }
  return json({error:'not found'},404,cors);
}};
