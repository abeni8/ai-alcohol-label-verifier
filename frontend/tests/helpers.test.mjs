import test from 'node:test';
import assert from 'node:assert/strict';
import { checkFiles } from '../src/api.mjs';
import { csvCell, resultsCsv } from '../src/export.mjs';
import { runQueue } from '../src/queue.mjs';

for (const value of ['=1+1','+SUM(A1:A2)','-1+2','@SUM(A1:A2)','  =cmd','\t=cmd','\r=cmd']) {
  test(`CSV neutralizes formula prefix ${JSON.stringify(value)}`, () => {
    assert.ok(csvCell(value).startsWith('"\''));
  });
}
for (const [value,expected] of [['Brand','"Brand"'],['A "quoted" name','"A ""quoted"" name"'],['a,b','"a,b"'],[null,'""'],['Line 1\nLine 2','"Line 1\nLine 2"']]) {
  test(`CSV quotes ${JSON.stringify(value)}`, () => assert.equal(csvCell(value),expected));
}

test('CSV export contains real results and failures, not just successes', () => {
  const csv = resultsCsv([{result:{application_id:'X',mode:'demo',filenames:['a.png'],browser_elapsed_ms:12,checks:[{label:'Brand',expected:'=1+1',observed:'Brand',status:'review',reason:'Different'}]}},{application:{application_id:'Y'},filenames:['b.png'],state:'failed',error:'Timeout'}]);
  assert.ok(csv.startsWith('\ufeff'));
  assert.ok(csv.includes("'=1+1"));
  assert.ok(csv.includes('Review needed'));
  assert.ok(csv.includes('failed'));
  assert.ok(csv.includes('demo'));
});

const file = (name='a.png',type='image/png',size=20) => ({name,type,size});
for (const [files,ok] of [[[file()],true],[[file('A.JPG','image/jpeg')],true],[[],false],[[file('x.pdf','application/pdf')],false],[[file('x.png','text/plain')],false],[[file('x.png','image/png',0)],false],[[file('x.png','image/png',5242881)],false],[[file(),file()],false],[[file('1.png'),file('2.png'),file('3.png'),file('4.png')],false]]) {
  test(`Upload rules ${JSON.stringify(files.map(f=>[f.name,f.type,f.size]))}`,()=>assert.equal(checkFiles(files)==='',ok));
}

test('Queue respects concurrency and completes every item exactly once', async () => {
  let active=0,maxActive=0;
  const seen=[];
  const updates=[];
  const items=Array.from({length:30},(_,i)=>i);
  const out=await runQueue(items,async item=>{active++;maxActive=Math.max(maxActive,active);seen.push(item);await new Promise(r=>setTimeout(r,2));active--;return item;},(i,u)=>updates.push([i,u.state]),{concurrency:2});
  assert.equal(maxActive,2);
  assert.equal(seen.length,30);
  assert.equal(new Set(seen).size,30);
  assert.ok(out.every(r=>r.state==='completed'));
  assert.equal(updates.length,60);
});

test('One failed application does not stop the batch',async()=>{
  const out=await runQueue([0,1,2],async item=>{if(item===1)throw new Error('Timeout');return item;},()=>{}, {concurrency:2});
  assert.deepEqual(out.map(x=>x.state),['completed','failed','completed']);
  assert.equal(out[1].error,'Timeout');
});

test('Cancellation stops scheduling queued items',async()=>{
  const controller=new AbortController();let calls=0;
  const out=await runQueue([0,1,2,3],async()=>{calls++;controller.abort();return {};},()=>{}, {concurrency:1,signal:controller.signal});
  assert.equal(calls,1);
  assert.ok(out.every(x=>x.state==='cancelled'));
});

test('Already-aborted queue submits nothing',async()=>{
  const controller=new AbortController();controller.abort();
  const out=await runQueue([0,1],async()=>{throw new Error('Should not be called');},()=>{}, {signal:controller.signal});
  assert.ok(out.every(x=>x.state==='cancelled'));
});

test('Queue supports the 300-row limit without losing items',async()=>{
  const out=await runQueue(Array.from({length:300},(_,i)=>i),async item=>item,()=>{}, {concurrency:2});
  assert.equal(out.length,300);
  assert.equal(out[299].result,299);
});

test('Queue rejects invalid concurrency',async()=>{
  await assert.rejects(runQueue([1],async()=>1,()=>{},{concurrency:0}));
});
