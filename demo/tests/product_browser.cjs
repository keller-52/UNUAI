// Run against an isolated server. Only synthetic learners and rules mode are used.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765';
const output=process.env.PAPER_TEST_OUTPUT||path.join(require('node:os').tmpdir(),'paper-product');
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const errors=[];context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const page=await context.newPage();
 const request=async(url,body)=>{const r=body===undefined?await context.request.get(base+url):await context.request.post(base+url,{data:body,headers:{'X-PaperAI':'local-teacher'}});return {status:r.status(),data:await r.json()};};
 const get=async url=>(await request(url)).data;
 const open=async(p,id,sid)=>{await p.goto(base);await p.waitForSelector(`#student-select option[value="${sid}"]`,{state:'attached'});await p.selectOption('#student-select',sid);await p.click(`[data-open="${id}"]`);await p.waitForSelector('#package-panel:not([hidden])');};
 const generate=async()=>{const done=page.waitForResponse(r=>r.url()===base+'/api/generate'&&r.request().method()==='POST');await page.click('#generate-button');const r=await done;assert.equal(r.status(),201);const p=await r.json();await page.waitForFunction(round=>document.querySelector('#package-title').textContent.startsWith('Round '+round+' /'),p.round);await page.waitForSelector('#package-panel:not([hidden])');return p;};
 const approve=async()=>{const done=page.waitForResponse(r=>r.url().endsWith('/approve'));await page.check('#reviewed');await page.click('#approve-button');assert.equal((await done).status(),200);await page.waitForSelector('#print-controls:not([hidden])');};
 const save=async p=>{await p.check('#trace-confirmed');const done=p.waitForResponse(r=>r.url().endsWith('/trace'));await p.click('#save-trace');return done;};
 const packets=[];
 try{
  await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/bootstrap')),page.goto(base)]);
  await page.click('#add-student');const alias='Acceptance '+Date.now();
  await page.fill('#student-form [name="label"]',alias);await page.fill('#student-form [name="class_name"]','Acceptance');
  const created=page.waitForResponse(r=>r.url().endsWith('/api/students'));
  await page.click('#student-form button[type="submit"]');const learner=await(await created).json();
  assert.equal(learner.state.status,'unknown');await page.reload();
  await page.waitForSelector(`#student-select option[value="${learner.id}"]`,{state:'attached'});
  assert.equal(await page.inputValue('#student-select'),learner.id);
  await page.click('#start-button');await page.uncheck('#custom-topic');await page.fill('[name="goal"]','Preserve this teaching goal');
  await page.selectOption('[name="language"]','en');await page.selectOption('#ui-language','zh');
  assert.equal(await page.inputValue('[name="goal"]'),'Preserve this teaching goal');assert.equal(await page.inputValue('[name="language"]'),'en');
  await page.selectOption('#ui-language','en');
  for(const language of ['en','zh'])for(const count of [2,3,4]){
   await page.selectOption('[name="language"]',language);await page.selectOption('[name="question_count"]',String(count));await page.selectOption('#planning-mode','demo');
   const p=await generate();packets.push(p);assert.equal(p.plan.nodes.length,count*2);assert.equal(p.config.language,language);
   await approve();
   let bookletTargets;
   for(const view of ['booklet','record','teacher']){
    const print=await context.newPage();await print.goto(`${base}/print.html?id=${p.id}&view=${view}`);
    await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
    assert.equal(await print.getAttribute('body','data-error'),null,await print.locator('#print-error').innerText());
    const layout=await print.evaluate(()=>{
     const pages=[...document.querySelectorAll('.print-page')],positions={};pages.forEach((p,i)=>p.querySelectorAll('[data-node]').forEach(n=>positions[n.dataset.node]=i+1));
     return {pages:pages.length,targets:[...document.querySelectorAll('[data-target]')].map(n=>({id:n.dataset.target,text:n.textContent,page:positions[n.dataset.target]}))};
    });
    if(view==='booklet'){assert.ok(layout.pages>=count&&layout.pages<=p.config.max_pages);for(const t of layout.targets)assert.ok(t.text.includes(String(t.page)),JSON.stringify(t));}
    if(view==='booklet')bookletTargets=new Map(layout.targets.map(t=>[t.id,t.text]));
    if(view==='teacher')for(const t of layout.targets)assert.equal(t.text,bookletTargets.get(t.id),'Teacher routes must match student booklet pages');
    if(view==='record')assert.equal(layout.pages,1);
    await print.pdf({path:path.join(output,`${language}-${count}-${view}.pdf`),format:'A4',printBackground:true,preferCSSPageSize:true});
    await print.close();
   }
  }
  console.log('PASS: new learner, persistence, language independence, bilingual 2/3/4-question PDFs and route pages');
  const p=packets.at(-1);await page.click('#collect-button');await page.click('#sample-scan-button');await page.waitForSelector('#scan-canvas[data-loaded]');await page.click('#read-sheet');
  await page.waitForFunction(()=>document.querySelector('#scan-issues').textContent.includes('matched.'));
  await page.selectOption('[data-task="Q1"][data-field="hint_level"]','2');assert.equal((await save(page)).status(),200);await page.waitForSelector('#results.active');
  const first=await get('/api/packages/'+p.id);assert.equal(first.trace_revision,1);assert.ok(first.trace.scan_review.corrected_fields.some(x=>x.field==='hint_level'&&x.to===2));
  await page.click('[data-tab="scan"]');await page.selectOption('[data-task="Q1"][data-field="hint_level"]','1');await page.reload();
  await page.click(`[data-open="${p.id}"]`);await page.click('#collect-button');assert.equal(await page.inputValue('[data-task="Q1"][data-field="hint_level"]'),'1');assert.equal(await page.isChecked('#trace-confirmed'),false);
  const other=await context.newPage();await open(other,p.id,learner.id);await other.click('#collect-button');
  await other.selectOption('[data-task="Q1"][data-field="hint_level"]','0');assert.equal((await save(other)).status(),200);await other.waitForSelector('#results.active');
  assert.equal((await save(page)).status(),400);assert.match(await page.locator('#notice').innerText(),/another tab/);
  await page.reload();await page.click(`[data-open="${p.id}"]`);await page.click('#collect-button');assert.equal(await page.inputValue('[data-task="Q1"][data-field="hint_level"]'),'0');
  const before=await get('/api/packages/'+p.id);const duplicate=await request('/api/packages/'+p.id+'/trace',{trace:before.trace,expected_revision:before.trace_revision});assert.equal(duplicate.data.duplicate,true);
  await page.selectOption('#scan-package-select',packets[0].id);await page.waitForFunction(()=>document.querySelector('#trace-body').children.length===4);assert.equal(await page.locator('#scan-canvas').getAttribute('data-loaded'),null);
  await other.close();console.log('PASS: scan correction audit, correction recovery, two-tab conflict, stale-draft rejection and historical round switch');
  await page.click('[data-tab="overview"]');const download=page.waitForEvent('download');await page.click('#backup-download');await(await download).saveAs(path.join(output,'synthetic-backup.json'));
  const exported=JSON.parse(fs.readFileSync(path.join(output,'synthetic-backup.json'),'utf8'));assert.ok(exported.trace_history.filter(x=>x.package_id===p.id).length>=2);assert.ok(!JSON.stringify(exported).includes('api_key'));
  const two=[];for(let i=0;i<2;i++){const r=await request('/api/students',{label:`Batch ${Date.now()} ${i}`,class_name:'Batch acceptance',synthetic:true});two.push(r.data.id);}
  await page.reload();await page.waitForSelector(`[data-batch][value="${two[0]}"]`);for(const id of two)await page.check(`[data-batch][value="${id}"]`);
  await page.click('[data-tab="plan"]');await page.selectOption('#planning-mode','demo');await page.click('[data-tab="overview"]');await page.click('#batch-generate');await page.waitForFunction(()=>document.querySelector('#batch-status').textContent==='2 / 2');
  const all=await get('/api/bootstrap');const batch=two.map(id=>all.packages.filter(p=>p.student_id===id).at(-1));
  for(const item of batch){await open(page,item.id,item.student_id);await approve();}
  await page.click('[data-tab="overview"]');for(const id of two)await page.check(`[data-batch][value="${id}"]`);
  for(const [button,view] of [['#batch-booklets','booklet'],['#batch-records','record']]){
   const opening=context.waitForEvent('page');await page.click(button);const print=await opening;await print.waitForLoadState();await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);assert.equal(await print.getAttribute('body','data-error'),null);
   assert.equal(await print.locator('[data-package]').evaluateAll(nodes=>new Set(nodes.map(n=>n.dataset.package)).size),2);
   await print.pdf({path:path.join(output,`batch-${view}.pdf`),format:'A4',printBackground:true,preferCSSPageSize:true});await print.close();
  }
  await page.selectOption('#ui-language','zh');await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'mobile-zh.png'),fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.deepEqual(errors,[]);console.log('PASS: backup download includes history, batch generation/review/combined PDFs, Chinese mobile layout');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

