// Explicit opt-in: two live generations, each with at most one JSON repair.
// Configure the server privately; this script never accepts or outputs API keys.
if(!process.argv.includes('--run'))throw Error('Pass --run to authorize paid live verification');
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765';
const output=process.env.PAPER_TEST_OUTPUT||path.join(require('node:os').tmpdir(),'paper-live');
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch();const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(120000);
 const report={synthetic:true,rounds:[]};const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const response=await page.request.post(base+'/api/students',{headers:{'X-PaperAI':'local-teacher'},data:{label:'Synthetic live acceptance '+Date.now(),synthetic:true,class_name:'Live acceptance',diagnostic:{}}});assert.equal(response.status(),201);const learner=await response.json();
  await page.goto(base);await page.waitForSelector(`#student-select option[value="${learner.id}"]`,{state:'attached'});await page.selectOption('#student-select',learner.id);
  assert.equal(await page.inputValue('#planning-mode'),'live');await page.uncheck('#custom-topic');await page.click('#start-button');
  for(let round=1;round<=2;round++){
   await page.selectOption('[name="language"]',round===1?'en':'zh');await page.selectOption('[name="question_count"]',round===1?'3':'4');await page.selectOption('#planning-mode','live');
   const done=page.waitForResponse(r=>r.url()===base+'/api/generate'&&r.request().method()==='POST');await page.click('#generate-button');const generated=await done;const p=await generated.json();
   assert.equal(generated.status(),201,p.error);assert.equal(p.mode,'live');assert.ok(p.audit.model);assert.equal(p.round,round);
   if(round===2){assert.ok(p.request.confirmed_evaluations.length);assert.ok(p.proposal.evidence_refs.length);}
   await page.waitForFunction(n=>document.querySelector('#package-title').textContent.startsWith('Round '+n+' /'),round);
   const approved=page.waitForResponse(r=>r.url().endsWith('/approve'));await page.check('#reviewed');await page.click('#approve-button');assert.equal((await approved).status(),200);await page.waitForSelector('#print-controls:not([hidden])');
   for(const view of ['booklet','record','teacher']){
    const print=await browser.newPage();await print.goto(`${base}/print.html?id=${p.id}&view=${view}`);await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
    assert.equal(await print.getAttribute('body','data-error'),null,await print.locator('#print-error').innerText());
    await print.pdf({path:path.join(output,`live-${round}-${view}.pdf`),format:'A4',preferCSSPageSize:true,printBackground:true});await print.close();
   }
   report.rounds.push({round,language:p.config.language,question_ids:p.proposal.question_ids,model:p.audit.model,evidence_refs:p.proposal.evidence_refs,attempts:p.audit.attempts.length,elapsed_seconds:p.audit.elapsed_seconds});
   fs.writeFileSync(path.join(output,'live-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report.rounds.at(-1)));
   if(round===1){await page.click('#collect-button');await page.click('#sample-ready-button');await page.check('#trace-confirmed');const saved=page.waitForResponse(r=>r.url().endsWith('/trace'));await page.click('#save-trace');assert.equal((await saved).status(),200);await page.waitForSelector('#results.active');await page.click('#next-round');}
  }
  assert.deepEqual(errors,[]);console.log('PASS: live default, two live UI generations, synthetic confirmed evidence, teacher approvals and six PDF views');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});

