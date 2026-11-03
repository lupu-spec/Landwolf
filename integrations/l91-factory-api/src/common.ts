const bytes = (s:string) => new TextEncoder().encode(s).byteLength;
export class InputError extends Error {status:number; constructor(message:string,status=400){super(message);this.status=status;}}
export async function body(request:Request):Promise<Record<string,unknown>> {
  if(!request.headers.get('content-type')?.includes('application/json')) throw new InputError('Send JSON.',415);
  const reader=request.body?.getReader(); if(!reader)throw new InputError('A request body is required.');
  const chunks:Uint8Array[]=[];let size=0;
  try {for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>900_000){await reader.cancel();throw new InputError('Upload is too large. Maximum combined size: 900 KB.',413);}chunks.push(value);}}finally{reader.releaseLock();}
  const all=new Uint8Array(size);let offset=0;for(const c of chunks){all.set(c,offset);offset+=c.length;}
  try {const parsed=JSON.parse(new TextDecoder().decode(all));if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))throw Error();return parsed;}catch{throw new InputError('Invalid JSON object.');}
}
export function field(input:Record<string,unknown>,key:string,max:number,required=false):string {
  const value=input[key]??'';if(typeof value!=='string'||value.length>max||(required&&!value.trim()))throw new InputError(`${key} ${required?'is required and ':''}must be at most ${max} characters.`);return value.trim();
}

export function validateResult(input:Record<string,unknown>,allowEmpty=false){
const report=input.report as Record<string,unknown>|null;
      if(!report||report.schema!=='l91.coding-run.v1'||typeof report.status!=='string'||!Array.isArray(report.rounds)||report.rounds.length>20)throw new InputError('Select an L91 run.json report (l91.coding-run.v1).');
      if(report.status.length>100)throw new InputError('Invalid report status.');
      for(const round of report.rounds){
        if(!round||typeof round!=='object'||Array.isArray(round))throw new InputError('Invalid model round in report.');
        if(round.attempt!==undefined&&(!Number.isSafeInteger(round.attempt)||round.attempt<1))throw new InputError('Invalid attempt number.');
        for(const name of ['model','provider'])if(round[name]!==undefined&&typeof round[name]!=='string')throw new InputError('Invalid model metadata.');
        if(round.verification!==undefined){
          const v=round.verification;if(!v||typeof v!=='object'||Array.isArray(v))throw new InputError('Invalid verification record.');
          for(const name of ['status','details'])if(v[name]!==undefined&&typeof v[name]!=='string')throw new InputError('Invalid verification text.');
        }
      }
      const reportText=JSON.stringify(report);
      if(bytes(reportText)>256000)throw new InputError('Report exceeds 256 KB.',413);
      const patch=input.patch;if(typeof patch!=='string'||(!allowEmpty&&!patch.trim()))throw new InputError('Select a non-empty review.patch file.');
      if(bytes(patch)>512000)throw new InputError('Patch exceeds 512 KB.',413);
      if((patch.trim()&&!/(^|\n)(diff --git |--- )/.test(patch))||patch.includes('\0'))throw new InputError('The patch must be a text unified diff.');

return {report,reportText,patch};
}
export async function hash(value:string){const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value));return Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");}
