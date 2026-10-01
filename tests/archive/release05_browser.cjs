// Requires a running local server + Playwright. Uses fixtures, no paid calls.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {execFileSync}=require('node:child_process');const assert=require('node:assert/strict');
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',`
import sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['demo','demo/tests']
from test_workbook import proposal,config
from server import Store,generate
from providers import PRESETS
with tempfile.TemporaryDirectory() as f:
 s=Store(Path(f)/'t.sqlite3');s.save('students',{'id':'S','label':'Synthetic','diagnostic':{},'synthetic':True})
 p=proposal()
 for b in p['batch_feedback']:b.pop('rules');b['guidance']='## Next steps\\n1. **Review** the explanation.\\n2. Finish at END.'
 p['lesson'][0]['text']='## Explanation\\n1. **Read** the rule.\\n2. Apply it.'
 with patch('server.ai_plan',return_value=(p,{'model':'mock'})):packet=generate(s,'S','live',config())
 packet['status']='issued';packet['config']['language']='en'
 print(json.dumps({'packet':packet,'presets':PRESETS}))
`],{encoding:'utf8'}));
(async()=>{const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765',browser=await chromium.launch();
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/bootstrap',r=>r.fulfill({json:{version:'0.5',students:[],packages:[],diagnostic:[],units:[],provider_presets:fixture.presets,provider:{configured:false,provider:'deepseek',protocol:'chat',base_url:'https://api.deepseek.com',model:'deepseek-flash'}}}));
  await page.goto(base);await page.selectOption('#ui-language','en');
  assert.equal(await page.locator('#connect-ai-main').innerText(),'Configure AI');
  await page.click('#connect-ai-main');await page.selectOption('#provider-select','gemini');
  assert.equal(await page.inputValue('[name=protocol]'),'gemini');assert.equal(await page.inputValue('[name=api_key]'),'');
  await page.selectOption('#provider-select','anthropic');assert.equal(await page.inputValue('[name=protocol]'),'anthropic');
  await page.click('[data-close="settings-dialog"]');await page.selectOption('#ui-language','zh');
  assert.equal(await page.locator('#connect-ai-main').innerText(),'配置 AI');
  assert.equal(await page.getAttribute('[name=topic]','placeholder'),'输入本次要教的知识点');
  const print=await browser.newPage();await print.route('**/api/packages/'+fixture.packet.id,r=>r.fulfill({json:fixture.packet}));
  await print.route('**/api/pdf',r=>r.fulfill({contentType:'application/pdf',body:Buffer.from('%PDF-1.4\n% fixture only\n%%EOF')}));
  await print.goto(base+'/print.html?id='+fixture.packet.id+'&view=booklet');
  await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);
  assert.equal(await print.getAttribute('body','data-error'),null);
  assert(await print.locator('#pages strong').count()>0);assert((await print.locator('#print-help').innerText()).includes('Ctrl+P'));
  const download=print.waitForEvent('download');await print.click('#export-pdf');assert.equal((await download).suggestedFilename(),'PAPER-AI-booklet.pdf');
  assert.deepEqual(errors,[]);console.log('PASS: provider selection, bilingual labels, Markdown preview, PDF download interaction (mock PDF transport)');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
