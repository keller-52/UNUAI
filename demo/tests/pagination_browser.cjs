// Isolated synthetic print responses; no issued package is changed.
const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765';const output=process.env.PAPER_TEST_OUTPUT||require('node:os').tmpdir();
(async()=>{const browser=await chromium.launch();try{
 const context=await browser.newContext();const data=await(await context.request.get(base+'/api/bootstrap')).json();
 const item=data.packages.find(x=>x.status!=='draft');assert.ok(item,'Run browser acceptance first');
 const original=await(await context.request.get(base+'/api/packages/'+item.id)).json();let fixture;
 const inspect=async(p,view)=>{
  const page=await context.newPage();await page.route('**/api/packages/'+p.id,r=>r.fulfill({json:p}));await page.goto(`${base}/print.html?id=${p.id}&view=${view}`);
  await page.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
  return page;
 };
 for(const length of [30,50,70,90,110]){
  const p=structuredClone(original);p.config.max_pages=12;p.plan.nodes.find(n=>n.type==='explanation').coach_note='Keep both sides balanced and check the result. '.repeat(length);
  const page=await inspect(p,'booklet');const count=await page.locator('.print-page').count();
  if(await page.getAttribute('body','data-ready')&&count>p.proposal.question_ids.length){fixture=p;fs.mkdirSync(output,{recursive:true});await page.pdf({path:output+'/continuation.pdf',format:'A4',printBackground:true,preferCSSPageSize:true});}
  await page.close();if(fixture)break;
 }
 assert.ok(fixture,'A block that fits alone must move to a continuation page');
 const targets=[];
 for(const view of ['booklet','teacher']){
  const page=await inspect(fixture,view);assert.equal(await page.getAttribute('body','data-error'),null);
  targets.push(await page.locator('[data-target]').evaluateAll(nodes=>Object.fromEntries(nodes.map(n=>[n.dataset.target,n.textContent]))));await page.close();
 }
 for(const [id,text] of Object.entries(targets[1]))assert.equal(text,targets[0][id]);
 fixture.config.max_pages=fixture.proposal.question_ids.length;
 const blocked=await inspect(fixture,'booklet');assert.match(await blocked.locator('#print-error').innerText(),/budget exceeded/i);assert.equal(await blocked.locator('#print-button').isDisabled(),true);await blocked.close();
 console.log('PASS: successful continuation, teacher/booklet route agreement after repagination, page-budget rejection');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1);});
