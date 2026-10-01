// Formal UI/API integration. Fixtures exercise the workflow without paid model calls.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {loadImage,createCanvas}=require('@napi-rs/canvas');
const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765';
const out=process.env.PAPER_TEST_OUTPUT||'test-results/release';fs.mkdirSync(out,{recursive:true});
const portable=JSON.parse(process.env.PAPER_FIXTURE?fs.readFileSync(process.env.PAPER_FIXTURE,'utf8'):execFileSync(process.env.PYTHON||'python',['app/tests/build_fixture.py'],{encoding:'utf8'}));
fs.writeFileSync(out+'/learning-package.json',JSON.stringify(portable));
(async()=>{
 const browser=process.env.PAPER_BROWSER_CDP?await chromium.connectOverCDP(process.env.PAPER_BROWSER_CDP):await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.waitForFunction(()=>document.body.dataset.appReady==='1');
  assert.equal(await page.locator('.showcase-panel,#sample-scan-button,#seed-button,#planning-mode').count(),0);
  const noDemo=async()=>assert.doesNotMatch(await page.locator('body').innerText(),/demo|prototype|rehearsal|showcase question banks|预制题库|规则演示/i);
  for(const lang of ['en','zh','en']){await page.selectOption('#ui-language',lang);assert.equal(await page.locator('#ai-connection-label').innerText(),lang==='zh'?'AI 未配置':'AI not configured');await noDemo();}
  await page.screenshot({path:out+'/home-en.png',fullPage:true});
  // Import without an existing learner: creation resumes the pending import.
  await page.setInputFiles('#package-file',out+'/learning-package.json');
  await page.waitForSelector('#student-dialog[open]');await page.fill('#student-form [name=label]','Reader 01');
  await page.click('#student-form button[type=submit]');await page.waitForSelector('#package-panel:not([hidden])');
  assert.match(await page.locator('#package-status').innerText(),/IMPORTED PACKAGE.*DRAFT/);
  assert.equal(await page.locator('#print-controls').isVisible(),false);
  await page.setInputFiles('#package-file',out+'/learning-package.json');
  await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('already in your workspace'));
  const packages=await (await page.request.get(base+'/api/bootstrap')).json();assert.equal(packages.packages.length,1);
  const id=portable.package.id;
  await page.locator('#teacher-review').evaluate(e=>e.parentElement.open=true);
  await page.fill('#draft-title','Reviewed reading with evidence');await page.click('#draft-save');
  await page.waitForFunction(()=>document.querySelector('#package-title').textContent.includes('Reviewed reading with evidence'));
  await page.check('#reviewed');await page.click('#approve-button');await page.waitForSelector('#print-controls:not([hidden])');
  for(const lang of ['zh','en']){await page.selectOption('#ui-language',lang);await noDemo();await page.screenshot({path:out+'/studio-'+lang+'.png',fullPage:true});}
  const [exported]=await Promise.all([page.waitForEvent('download'),page.click('#package-export')]);
  await exported.saveAs(out+'/exported-package.json');const payload=JSON.parse(fs.readFileSync(out+'/exported-package.json','utf8'));
  assert.equal(payload.format,'paper-ai-learning-package');assert(!('student_id' in payload.package));assert(!('trace' in payload.package));
  for(const view of ['booklet','support','record','teacher']){
   const print=await browser.newPage();await print.goto(base+'/print.html?id='+id+'&view='+view);
   await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
   assert.equal(await print.getAttribute('body','data-error'),null,await print.locator('#print-error').innerText());
   await print.pdf({path:out+'/'+view+'.pdf',format:'A4',preferCSSPageSize:true,printBackground:true});
   if(view==='booklet'){assert.equal(await print.locator('.answer-slot').count(),12);await print.screenshot({path:out+'/booklet.png',fullPage:true});}
   if(view==='support')assert.equal(await print.locator('.hint-check').count(),24);
   await print.close();
  }
  // Use the real image upload path and actual OMR, then confirm a genuine structured trace.
  const svg=await page.evaluate(async id=>{
   const {recordPacket,recordSVG,sampleRows}=await import('/paper.js');
   const p=await(await fetch('/api/packages/'+id)).json();return recordSVG(recordPacket(p,0),sampleRows(p,'support'));
  },id);
  const image=await loadImage(Buffer.from(svg));const canvas=createCanvas(794,1123);canvas.getContext('2d').drawImage(image,0,0,794,1123);fs.writeFileSync(out+'/filled-record.png',canvas.toBuffer('image/png'));
  await page.click('[data-tab=scan]');await page.setInputFiles('#scan-file',out+'/filled-record.png');await page.waitForSelector('#scan-canvas[data-loaded]');await page.click('#read-sheet');
  await page.waitForFunction(()=>document.querySelector('#scan-issues').textContent.includes('matched.'));
  await page.check('#trace-confirmed');await page.click('#save-trace');await page.waitForSelector('#results.active');
  assert.match(await page.locator('#results-content').innerText(),/Observations/);await noDemo();
  await page.screenshot({path:out+'/records.png',fullPage:true});
  // Generation stays real-AI-only. Mock a response, never ship a generation fallback.
  await page.route('**/api/bootstrap',async route=>{const response=await route.fetch(),data=await response.json();data.provider.configured=true;data.provider.model='fixture';await route.fulfill({json:data});});
  let called=false;
  await page.route('**/api/generate',route=>{const b=route.request().postDataJSON();assert.equal(b.mode,'live');assert.equal(b.config.custom_topic,true);assert.equal(b.config.include_reference_bank,false);called=true;return route.fulfill({status:201,json:portable.package});});
  await page.reload();await page.click('[data-tab=plan]');
  await page.fill('[name=topic]','Reading with evidence');await page.fill('[name=background]','Read a passage and use direct evidence.');await page.fill('[name=goal]','Distinguish observations from assumptions.');await page.click('#generate-button');await page.waitForFunction(()=>document.querySelector('#package-panel').hidden===false);assert(called);
  // Both languages at phone, tablet and desktop sizes must avoid horizontal overflow.
  for(const width of [360,390,768,1440])for(const lang of ['en','zh']){
   await page.setViewportSize({width,height:1000});await page.selectOption('#ui-language',lang);
   for(const tab of ['plan','scan','results']){await page.click('[data-tab='+tab+']');const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);if(overflow){await page.screenshot({path:out+'/overflow-'+tab+'-'+width+'-'+lang+'.png',fullPage:true});console.log(await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth).map(e=>({tag:e.tagName,id:e.id,class:e.className,right:e.getBoundingClientRect().right})).slice(0,20)));}assert.equal(overflow,false,`${tab} ${width} ${lang}`);await noDemo();}
   await page.click('#home-button');if(width===390||width===1440)await page.screenshot({path:out+'/home-'+width+'-'+lang+'.png',fullPage:true});
  }
  assert.deepEqual(errors,[]);console.log('PASS: package import/export, learner creation, idempotence, review, four PDFs, actual OMR upload, records, AI-only generation, bilingual layouts and clean formal text');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
