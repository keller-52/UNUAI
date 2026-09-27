// Optional integration test: npm install --no-save playwright; npx playwright install chromium
// Start demo/server.py first. Uses synthetic learners only. Evidence output stays outside the repo.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const output=process.env.PAPER_TEST_OUTPUT||'/tmp/paper-ai-browser';
fs.mkdirSync(output,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PAPER_TEST_URL||'http://127.0.0.1:8765');
  // Module parse errors otherwise look like an unrelated seed-button timeout.
  assert.deepEqual(errors,[],'Teacher page must load without JavaScript errors');
  await page.click('#seed-button');await page.waitForFunction(()=>document.querySelector('#student-select').options.length>=2);
  await page.selectOption('#student-select','S-DEMO-A');
  await page.screenshot({path:output+'/overview.png',fullPage:true});
  await page.uncheck('#custom-topic');await page.click('#start-button');await page.selectOption('#planning-mode','demo');await page.click('#generate-button');
  await page.waitForSelector('#package-panel:not([hidden])');await page.check('#reviewed');await page.click('#approve-button');
  await page.waitForSelector('#print-controls:not([hidden])');
  const pkg=await page.evaluate(async()=>{const d=await(await fetch('/api/bootstrap')).json();const ps=d.packages.filter(x=>x.student_id==='S-DEMO-A');return(await fetch('/api/packages/'+ps.at(-1).id)).json();});
  for(const view of ['booklet','record','teacher']){
   const print=await browser.newPage();await print.goto(`http://127.0.0.1:8765/print.html?id=${pkg.id}&view=${view}`);
   await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
   assert.equal(await print.getAttribute('body','data-error'),null,await print.locator('#print-error').innerText());
   await print.pdf({path:`${output}/${view}.pdf`,format:'A4',preferCSSPageSize:true,printBackground:true});
   if(view==='booklet')await print.screenshot({path:output+'/print-preview.png',fullPage:true});
   await print.close();
  }
  // Isolated responses exercise the overflow guard without changing issued data.
  for(const field of ['title','coach_note']){
   const oversized=structuredClone(pkg);
   if(field==='title')oversized.plan.title='Long learning title '.repeat(300);
   else oversized.plan.nodes.find(n=>n.type==='explanation').coach_note='Long coaching explanation. '.repeat(500);
   const print=await browser.newPage();
   await print.route('**/api/packages/'+pkg.id,route=>route.fulfill({json:oversized}));
   await print.goto(`http://127.0.0.1:8765/print.html?id=${pkg.id}&view=booklet`);
   await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
   assert.equal(await print.getAttribute('body','data-error'),'1');
   assert.match(await print.locator('#print-error').innerText(),/page/i);
   assert.equal(await print.locator('#print-button').isDisabled(),true);
   await print.close();
  }
  await page.click('#collect-button');await page.click('#sample-scan-button');
  await page.waitForSelector('#scan-canvas[data-loaded]');await page.click('#read-sheet');
  await page.waitForFunction(()=>document.querySelector('#scan-issues').textContent.includes('matched.'));
  assert.match(await page.locator('#scan-issues').innerText(),/0 ambiguous/);
  assert.equal(await page.locator('select[data-task="Q1"][data-field="order"]').inputValue(),'1');
  await page.screenshot({path:output+'/scan.png',fullPage:true});
  await page.check('#trace-confirmed');await page.click('#save-trace');await page.waitForSelector('#results.active');
  assert.match(await page.locator('#results-content').innerText(),/SYNTHETIC DATA/);
  await page.click('#next-round');await page.click('#generate-button');
  await page.waitForFunction(()=>document.querySelector('#package-status').textContent.includes('DRAFT'));
  const next=await page.evaluate(async()=>{const d=await(await fetch('/api/bootstrap')).json();return(await fetch('/api/packages/'+d.packages.filter(x=>x.student_id==='S-DEMO-A').at(-1).id)).json();});
  assert.notDeepEqual(next.proposal.question_ids,pkg.proposal.question_ids);
  assert.ok(next.request.confirmed_evaluations.length);
  // Independent scanner tests use rasterized records, perspective distortion and ambiguous marks.
  const scannerResults=await page.evaluate(async p=>{
   const paper=await import('/paper.js'),scan=await import('/scanner.js');
   const expected=paper.sampleRows(p,'support');
   const base=await scan.loadImage(new Blob([paper.recordSVG(p,expected)],{type:'image/svg+xml'}));
   const corners=scan.autoCorners(base),found=scan.readSheet(base,corners,p);
   const changed=structuredClone(p);changed.sheet_code=p.sheet_code==='FFFFFF'?'000000':'FFFFFF';
   let mismatch=false;try{scan.readSheet(base,corners,changed);}catch(e){mismatch=e.message.includes('expects');}
   const ambiguous=document.createElement('canvas');ambiguous.width=base.width;ambiguous.height=base.height;
   const c=ambiguous.getContext('2d');c.drawImage(base,0,0);
   const first=expected.find(x=>x.task_id==='Q1').first_answer;
   const extra=first==='A'?1:0;c.fillStyle='black';c.beginPath();c.arc(paper.COLS.first_answer[extra],paper.rowY(0),6,0,Math.PI*2);c.fill();
   const unsure=scan.readSheet(ambiguous,corners,p);
   // Build a photograph-like projective warp by inverse-sampling the flat image.
   const photo=document.createElement('canvas');photo.width=1050;photo.height=1400;
   const pts=[{x:160,y:95},{x:955,y:190},{x:855,y:1270},{x:85,y:1180}];
   // Source marker centres -> chosen perspective corners; solve inverse mapping directly.
   const map=scan.homography(pts),src=base.getContext('2d').getImageData(0,0,base.width,base.height);
   const dst=photo.getContext('2d'),im=dst.createImageData(photo.width,photo.height);im.data.fill(255);
   // Forward splat at subpixel steps is sufficient for a synthetic camera integration fixture.
   for(let y=0;y<paper.H;y+=.5)for(let x=0;x<paper.W;x+=.5){const q=map(x,y),xx=Math.round(q.x),yy=Math.round(q.y);if(xx<0||yy<0||xx>=photo.width||yy>=photo.height)continue;const si=(Math.floor(y)*base.width+Math.floor(x))*4,di=(yy*photo.width+xx)*4;for(let k=0;k<3;k++)im.data[di+k]=src.data[si+k];}
   dst.putImageData(im,0,0);
   const warped=scan.readSheet(photo,pts,p);
   return {expected,actual:found.rows,mismatch,ambiguous:unsure.issues.length,unknown:unsure.rows[0].first_answer,warped:warped.rows};
  },pkg);
  assert.deepEqual(scannerResults.actual,scannerResults.expected);
  assert.deepEqual(scannerResults.warped,scannerResults.expected);
  assert.ok(scannerResults.mismatch);assert.ok(scannerResults.ambiguous>0);assert.equal(scannerResults.unknown,null);
  await page.setViewportSize({width:390,height:844});await page.click('[data-tab="overview"]');
  await page.screenshot({path:output+'/mobile.png',fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'Mobile horizontal overflow');
  assert.deepEqual(errors,[]);
  console.log('PASS: teacher UI, approval, 3 PDF views, local scanning, ambiguity/version checks, perspective correction, two rounds, mobile layout');
  console.log('Evidence:',output);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});


