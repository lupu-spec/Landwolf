import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
export function database(){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../migrations/0001_init.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0002_tasks.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0003_revision_order.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0004_runner.sql',import.meta.url),'utf8'));
 sqlite.exec(readFileSync(new URL('../migrations/0005_portal.sql',import.meta.url),'utf8'));
 // Run statements against real SQLite rather than matching SQL strings in a mock.
 const db={prepare(sql){const stmt=sqlite.prepare(sql);let values=[];return {bind(...v){values=v;return this;},async first(){return stmt.get(...values)||null;},async all(){return {results:stmt.all(...values)};},async run(){const r=stmt.run(...values);return {success:true,meta:{changes:Number(r.changes)}};}};},async batch(statements){sqlite.exec('BEGIN');try{const out=[];for(const stmt of statements)out.push(await stmt.run());sqlite.exec('COMMIT');return out;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
 return db;
}
