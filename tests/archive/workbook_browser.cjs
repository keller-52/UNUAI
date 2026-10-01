// No live API calls. Start the local server, then run this with Playwright installed.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');const assert=require('node:assert/strict');
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',`
import sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['demo','demo/tests']
from test_workbook import proposal,config
from server import Store,generate
with tempfile.TemporaryDirectory() as folder:
 s=Store(Path(folder)/'test.sqlite3');s.save('students',{'id':'S','label':'Synthetic','grade':'Secondary','diagnostic':{}})
 with patch('server.ai_plan',return_value=(proposal(),{'model':'mock'})):p=generate(s,'S','live',config())
 p['status']='issued';print(json.dumps(p))
`],{encoding:'utf8'}));
(async()=>{const browser=await chromium.launch({headless:true});const output=process.env.PAPER_TEST_OUTPUT||'test-results/workbook';fs.mkdirSync(output,{recursive:true});
 try{
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/bootstrap',r=>r.fulfill({json:{version:'0.4',students:[],packages:[],diagnostic:[],provider:{configured:false,base_url:'https://api.deepseek.com',model:'deepseek-flash'}}}));
  await page.goto(process.env.PAPER_TEST_URL||'http://127.0.0.1:8765');
  assert.equal(await page.locator('nav .nav').count(),3);assert.equal(await page.locator('#custom-topic').count(),0);
  await page.click('#connect-ai-main');await page.waitForSelector('#settings-dialog[open]');
  await page.click('[data-close="settings-dialog"]');
  await page.click('[data-tab="plan"]');assert.equal(await page.locator('#planning-mode').count(),0);
  for(const view of ['booklet','support','record','teacher']){
   const print=await browser.newPage();await print.route('**/api/packages/'+fixture.id,r=>r.fulfill({json:fixture}));
   await print.goto((process.env.PAPER_TEST_URL||'http://127.0.0.1:8765')+'/print.html?id='+fixture.id+'&view='+view);
   await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
   assert.equal(await print.getAttribute('body','data-error'),null,await print.locator('#print-error').innerText());
   const content=await print.locator('#pages').innerText();
   if(view==='booklet'){assert(!content.includes('提示一'));assert(!content.includes('根据背景判断。'));assert(content.includes('先理解教师提供的背景。'));}
   if(view==='record')assert.equal(await print.locator('.record-page').count(),2);
   if(view==='support'){assert(content.includes('提示一'));assert(content.includes('回看本批概念'));}
   await print.pdf({path:output+'/'+view+'.pdf',format:'A4',preferCSSPageSize:true,printBackground:true});await print.close();
  }
  assert.deepEqual(errors,[]);console.log('Workbook browser checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
