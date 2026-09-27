// Start a separate, empty target server; set PAPER_RESTORE_URL and PAPER_BACKUP_FILE.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const base=process.env.PAPER_RESTORE_URL||'http://127.0.0.1:8766';
const file=process.env.PAPER_BACKUP_FILE;
if(!file)throw Error('Set PAPER_BACKUP_FILE to a synthetic acceptance backup');
(async()=>{
 const source=JSON.parse(fs.readFileSync(file,'utf8')),browser=await chromium.launch();
 try{
  const page=await browser.newPage();page.on('dialog',d=>d.accept());
  await page.goto(base);
  for(let pass=0;pass<2;pass++){
   const result=page.waitForResponse(r=>r.url().endsWith('/api/restore'));
   await page.setInputFiles('#backup-file',file);const response=await result;
   assert.equal(response.status(),200);const body=await response.json();assert.equal(body.merged,pass===0?source.students.length+source.packages.length:0);
   await page.waitForFunction(()=>document.querySelector('#backup-file').value==='');
  }
  const restored=await(await page.request.get(base+'/api/backup')).json();
  for(const key of ['students','packages','traces','trace_history']){
   const sort=rows=>rows.map(r=>JSON.stringify(r)).sort();assert.deepEqual(sort(restored[key]),sort(source[key]),key+' must round-trip exactly');
  }
  const p=source.packages.find(p=>p.status!=='draft');
  const issued=await(await page.request.get(base+'/api/packages/'+p.id)).json();assert.ok(issued.student_token);
  await page.goto(base+'/learn.html?id='+p.id+'&token='+issued.student_token);
  assert.equal((await page.request.get(base+'/api/learn/'+p.id+'?token='+issued.student_token)).status(),200);
  console.log('PASS: browser backup upload, empty-database restore, duplicate restore, exact data/history preservation and restored student link');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
