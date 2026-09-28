// Current three-workspace flow, mocked AI generation; no paid calls.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {execFileSync}=require('node:child_process');const assert=require('node:assert/strict');const fs=require('node:fs');
const fixture=JSON.parse(execFileSync(process.env.PYTHON||'python',['-c',`
import sys,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['demo','demo/tests']
from test_workbook import proposal,config
from server import Store,generate
from providers import PRESETS
with tempfile.TemporaryDirectory() as d:
 s=Store(Path(d)/'t.sqlite3');s.save('students',{'id':'S','label':'Synthetic learner','grade':'Secondary','diagnostic':{},'synthetic':True})
 p=proposal()
 for b in p['batch_feedback']:
  b.pop('rules');b['guidance']='| 选择情况 | 情况分析 | 跳转内容 |\\n| --- | --- | --- |\\n| 全对 | 基础清晰 | END |\\n| 其他 | 基础需巩固 | 阅读本组解析，重试一次后 END |'
 p['lesson'][0]['text']='　　先理解教师提供的背景。明确本节知识的概念和使用条件，再进行练习。'
 with patch('server.ai_plan',return_value=(p,{'model':'mock','attempts':[{}],'elapsed_seconds':0})):packet=generate(s,'S','live',config())
 packet['config']['language']='zh'
 print(json.dumps({'packet':packet,'presets':PRESETS}))
`],{encoding:'utf8'}));
(async()=>{const base=process.env.PAPER_TEST_URL||'http://127.0.0.1:8765',browser=await chromium.launch(),out=process.env.PAPER_TEST_OUTPUT;try{
 const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));let generated=false,configured=false;
 await page.route('**/api/bootstrap',r=>r.fulfill({json:{version:'0.6',students:[{id:'S',label:'Synthetic learner',synthetic:true,state:{},grade:'Secondary'}],packages:generated?[{...fixture.packet,title:fixture.packet.plan.title}]:[],diagnostic:[],provider_presets:fixture.presets,provider:{configured,model:'mock',base_url:'https://api.deepseek.com',protocol:'chat',provider:'deepseek'}}}));
 await page.route('**/api/packages/'+fixture.packet.id,r=>r.fulfill({json:fixture.packet}));
 await page.route('**/api/generate',r=>{const body=r.request().postDataJSON();assert.equal(body.mode,'live');assert.equal(body.config.custom_topic,true);assert.equal(body.config.topic,'进位加法');assert.equal(body.config.include_reference_bank,false);generated=true;return r.fulfill({status:201,json:fixture.packet});});
 await page.route('**/api/packages/*/approve',r=>{fixture.packet.status='issued';return r.fulfill({json:fixture.packet});});
 await page.route('**/api/packages/*/summary',r=>r.fulfill({json:{content:{summary:'情况：首次答案记录不足。',next_steps:['措施：先完成题组 1。']}}}));
 await page.goto(base);await page.selectOption('#ui-language','zh');
 assert.equal(await page.locator('nav button').count(),3);assert.equal(await page.locator('#custom-topic,#planning-mode,#seed-button').count(),0);
 await page.click('[data-tab=plan]');assert.equal(await page.locator('#manage-panel').getAttribute('open'),null);
 await page.fill('[name=topic]','进位加法');await page.fill('[name=background]','理解凑十法和进位加法。');await page.fill('[name=goal]','完成简单的进位加法。');
 await page.click('#generate-button');await page.waitForSelector('#settings-dialog[open]');assert.match(await page.locator('#notice').innerText(),/配置/);
 await page.click('[data-close=settings-dialog]');configured=true;await page.reload();await page.click('[data-tab=plan]');
 await page.fill('[name=topic]','进位加法');await page.fill('[name=background]','理解凑十法和进位加法。');await page.fill('[name=goal]','完成简单的进位加法。');await page.click('#generate-button');
 await page.waitForSelector('#package-panel:not([hidden])');assert.equal(await page.locator('#plan #learning-summary').count(),0);
 await page.check('#reviewed');await page.click('#approve-button');await page.waitForSelector('#print-controls:not([hidden])');
 await page.click('[data-tab=results]');await page.click('#refresh-ai-summary');await page.waitForFunction(()=>document.querySelector('#learning-summary').textContent.includes('措施：先完成题组 1'));
 await page.click('[data-tab=scan]');assert(await page.locator('#scan-file').isVisible());
 if(process.env.PAPER_PHOTO_DIR){
  fixture.packet.record_sheets=[{code:'689634',page:2,task_ids:['Q9','Q10']}];
  await page.click('[data-tab=results]');await page.selectOption('#summary-package-select',fixture.packet.id);await page.click('[data-tab=scan]');
  for(const file of ['01-0.jpg','02-c6979748f1973484bad9629f11908a2b.jpg']){
   await page.setInputFiles('#scan-file',require('node:path').join(process.env.PAPER_PHOTO_DIR,file));await page.waitForSelector('#scan-canvas[data-loaded]');await page.click('#read-sheet');await page.waitForFunction(()=>document.querySelector('#scan-issues').textContent.includes('689634'));
   assert.equal(await page.inputValue('[data-task=Q9][data-field=first_answer]'),'A');assert.equal(await page.inputValue('[data-task=Q9][data-field=hint_level]'),'1');assert.equal(await page.inputValue('[data-task=Q9][data-field=retry_answer]'),'B');
   assert.equal(await page.inputValue('[data-task=Q10][data-field=first_answer]'),'B');assert.equal(await page.inputValue('[data-task=Q10][data-field=retry_answer]'),'C');
  }
 }
 await page.click('#home-button');assert(await page.locator('#overview').isVisible());
 for(const lang of ['en','zh']){await page.selectOption('#ui-language',lang);await page.click('[data-tab=plan]');if(out){fs.mkdirSync(out,{recursive:true});await page.screenshot({path:out+'/studio-'+lang+'.png',fullPage:true});}}
 for(const view of ['booklet','support']){
  const print=await browser.newPage();await print.route('**/api/packages/'+fixture.packet.id,r=>r.fulfill({json:fixture.packet}));await print.goto(base+'/print.html?id='+fixture.packet.id+'&view='+view);await print.waitForFunction(()=>document.body.dataset.ready||document.body.dataset.error);assert.equal(await print.getAttribute('body','data-error'),null);
  if(view==='booklet'){assert.equal(await print.locator('.answer-slot').count(),12);assert.equal(await print.locator('.lesson-paragraph').first().evaluate(e=>getComputedStyle(e).textIndent),'32px');}
  else{assert.equal(await print.locator('.hint-check').count(),24);assert.equal(await print.locator('.hint-item').count(),12);const geometry=await print.locator('.hint-line').evaluateAll(lines=>lines.map(l=>{const n=l.querySelector('b').getBoundingClientRect(),p=l.querySelector('p').getBoundingClientRect();return Math.abs(n.top-p.top)}));assert(geometry.every(d=>d<5),'Hint number and prose must share a line');}
  if(out)await print.pdf({path:out+'/current-'+view+'.pdf',format:'A4',preferCSSPageSize:true,printBackground:true});await print.close();
 }
 assert.deepEqual(errors,[]);console.log('PASS: latest-only authoring, missing-AI prompt, three workspaces, summary, bilingual UI, inline hints/ticks, answer slots and paragraph indentation');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
