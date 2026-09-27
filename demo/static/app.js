import {locale,tr,setLocale,startI18n} from './i18n.js';
import {esc,blankRows,sampleRows,recordSVG} from './paper.js';
import {autoCorners,readSheet,loadImage} from './scanner.js';

const $=s=>document.querySelector(s);
let data=null,studentId=localStorage.getItem('paper-student')||'',pkg=null,rows=[],traceSource='manual';
let scanImage=null,corners=[],scanIssues=[],scanSource='scan',scanRead=false,scanOriginal=null;
let toastTimer,modeInitialized=false;
function toast(message,error=false){clearTimeout(toastTimer);$('#notice').textContent=tr(message);$('#notice').className=error?'error':'';$('#notice').hidden=false;toastTimer=setTimeout(()=>$('#notice').hidden=true,error?14000:6500);}
async function api(path,body){const res=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-PaperAI':'local-teacher'},body:JSON.stringify(body)});const result=await res.json();if(!res.ok)throw Error(result.error||'Request failed');return result;}
function on(selector,event,fn){$(selector).addEventListener(event,async e=>{const button=e.currentTarget;try{if(button.tagName==='BUTTON')button.disabled=true;await fn(e);}catch(err){toast(err.message,true);}finally{if(button.tagName==='BUTTON')button.disabled=false;}});}
function student(){return data?.students.find(s=>s.id===studentId);}
function selectedPackages(){return data?.packages.filter(p=>p.student_id===studentId)||[];}
function show(tab){document.querySelectorAll('.view').forEach(e=>e.classList.toggle('active',e.id===tab));document.querySelectorAll('.nav').forEach(e=>e.classList.toggle('active',e.dataset.tab===tab));if(tab==='results')renderResults();}
function download(name,content,type='application/json'){const u=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
async function refresh(){
 data=await api('/api/bootstrap');if(!data.students.some(s=>s.id===studentId))studentId=data.students[0]?.id||'';
 localStorage.setItem('paper-student',studentId);
 $('#student-select').innerHTML=data.students.length?data.students.map(s=>`<option value="${esc(s.id)}">${esc(s.label)}</option>`).join(''):'<option value="">No learner yet</option>';
 $('#student-select').value=studentId;
 $('#mode-status').textContent=data.provider.configured?'Live AI configured':'Rules demo available';
 $('#planning-mode option[value="live"]').disabled=!data.provider.configured;
 if(!modeInitialized){$('#planning-mode').value=data.provider.configured?'live':'demo';modeInitialized=true;}
 renderOverview();renderState();renderScanSelect();renderBatch();
}
function renderOverview(){
 const s=student(),ps=selectedPackages();$('#metric-learner').textContent=s?.label.split(' · ')[0]||'—';$('#metric-synthetic').textContent=s?(s.synthetic?'Synthetic demonstration profile':s.id+' · teacher-created profile'):'Create a profile or load samples';$('#metric-rounds').textContent=ps.length;
 $('#metric-score').textContent=pkg?.evaluation?`${pkg.evaluation.first_correct} / ${pkg.evaluation.first_total}`:(s?.state.recent_total?`${s.state.recent_correct} / ${s.state.recent_total}`:'—');
 $('#round-list').innerHTML=ps.length?[...ps].reverse().map(p=>`<article class="round-card"><div class="round-number">${p.round}</div><div><h3>${esc(p.title)}</h3><small>${p.mode==='live'?'Live AI':'Rules demo'} · ${esc(p.status)} · ${esc(p.id)}</small></div><button class="secondary" data-open="${esc(p.id)}">Open round ↗</button></article>`).join(''):'<div class="card empty">No paper packages yet. Start with a learner, then plan a round.</div>';
 document.querySelectorAll('[data-open]').forEach(b=>b.onclick=async()=>{try{await openPackage(b.dataset.open);show('plan');}catch(e){toast(e.message,true);}});
}
function renderState(){
 const s=student();$('#state-title').textContent=s?({unknown:'First, gather evidence',needs_support_check:'Support, then check again',ready_for_transfer_check:'Ready for a transfer check'}[s.state.status]):'No learner selected';
 $('#state-details').innerHTML=s?`<p class="muted">${esc(s.label)} · ${esc(s.grade)}${s.synthetic?' · SYNTHETIC':''}</p><div class="observation"><strong>${s.state.recent_correct} / ${s.state.recent_total}</strong>Recent observed correct answers</div><div class="observation"><strong>${s.state.evidence.length}</strong>Evidence references across diagnosis and rounds</div><div class="observation">Independent correct: ${s.state.independent_correct||0} · Supported correct: ${s.state.supported_correct||0}<br>${s.state.review_required?'Review due':'Not stable mastery'}</div>${s.state.hypotheses.map(h=>`<div class="observation"><b>Hypothesis: ${esc(h.label.replaceAll('_',' '))}</b><br>Needs verification · ${esc(h.evidence_refs.join(', '))}</div>`).join('')}`:'<p class="muted">Add a learner or load the two sample profiles.</p>';
}
function renderScanSelect(){const ps=selectedPackages().filter(p=>p.status!=='draft');$('#scan-package-select').innerHTML=ps.length?ps.map(p=>`<option value="${esc(p.id)}">Round ${p.round} · ${esc(p.id)}</option>`).join(''):'<option value="">Approve a package first</option>';if(pkg&&ps.some(x=>x.id===pkg.id))$('#scan-package-select').value=pkg.id;}
async function openPackage(id){
 pkg=await api('/api/packages/'+encodeURIComponent(id));rows=pkg.trace?.rows||blankRows(pkg);traceSource=pkg.trace?.source||'manual';scanImage=null;corners=[];scanIssues=[];scanRead=false;scanOriginal=null;$('#scan-canvas').removeAttribute('data-loaded');$('#scan-issues').textContent='';$('#trace-confirmed').checked=false;
 renderPackage();renderRows();renderResults();renderScanSelect();renderOverview();restoreDraft();
}
function renderPackage(){
 $('#package-panel').hidden=!pkg;if(!pkg)return;
 $('#package-title').textContent=`Round ${pkg.round} / ${pkg.plan.title}`;$('#package-status').textContent=`${pkg.mode==='live'?'LIVE AI':'RULES DEMO'} · ${pkg.status.toUpperCase()}`;
 $('#plan-reason').innerHTML=`<span class="eyebrow">WHY THIS PLAN</span><p>${esc(pkg.proposal.reason)}</p><p class="muted">Evidence: ${esc(pkg.proposal.evidence_refs.join(', ')||'No previous observations.')}<br>${pkg.mode==='demo'?'This package was generated by deterministic rehearsal rules. No AI was called.':`Model: ${esc(pkg.audit.model)} · ${pkg.audit.attempts.length} attempt(s) · ${pkg.audit.elapsed_seconds}s`}</p>`;
 $('#plan-reason').insertAdjacentHTML('beforeend',`<p>${tr('Learning days:')} ${esc((pkg.schedule||[]).map(x=>x.task_id+' → '+x.day).join(', '))}</p><p>${tr('Reused questions:')} ${esc((pkg.reused_question_ids||[]).join(', ')||'—')}</p>`);
 $('#plan-path').innerHTML=pkg.plan.nodes.filter(n=>n.type==='choice_question').map(n=>`<article class="path-card"><small>${n.id} · ${esc(n.level.toUpperCase())}</small><p>${esc(n.prompt)}</p><em>${esc(n.routes.map(r=>r.answer+' → '+r.next).join(' · '))}</em></article>`).join('');
 $('#teacher-review').innerHTML=pkg.plan.nodes.map(n=>n.type==='choice_question'?`<h3>${n.id}: ${esc(n.prompt)}</h3><p>${n.options.map(o=>`${o.id}: ${esc(o.text)}`).join(' · ')}</p><p><b>Correct option: ${esc(n.correct_option)}</b> · ${esc(n.explanation)}</p>`:n.type==='explanation'?`<h3>${n.id}: Support branch</h3><p>${esc(n.text)}</p><p>${esc(n.coach_note)}</p>`:'').join('');
 $('#plan-json').textContent=JSON.stringify({proposal:pkg.proposal,plan:pkg.plan,audit:pkg.audit,request:pkg.request},null,2);
 $('#discard-draft').hidden=pkg.status!=='draft';
 $('#draft-editor')?.remove();
 if(pkg.status==='draft')$('#teacher-review').insertAdjacentHTML('afterend',`<div id="draft-editor"><label>${tr('Title')}<input id="draft-title" maxlength="90" value="${esc(pkg.proposal.title)}"></label><label>${tr('Reason')}<textarea id="draft-reason" maxlength="700">${esc(pkg.proposal.reason)}</textarea></label>${pkg.proposal.coach_notes.map((note,i)=>`<label>${tr('Coach note')} ${i+1}<textarea data-note="${i}" maxlength="450">${esc(note)}</textarea></label>`).join('')}<button id="draft-save">${tr('Save draft edits')}</button></div>`);
 if($('#draft-save'))$('#draft-save').onclick=async()=>{try{await api('/api/packages/'+pkg.id+'/edit',{plan_hash:pkg.plan_hash,title:$('#draft-title').value,reason:$('#draft-reason').value,coach_notes:[...document.querySelectorAll('[data-note]')].map(x=>x.value)});await refresh();await openPackage(pkg.id);}catch(e){toast(e.message,true);}};
 $('#approval-row').hidden=pkg.status!=='draft';$('#reviewed').checked=false;$('#print-controls').hidden=pkg.status==='draft';
}
function renderRows(){
 if(!pkg){$('#trace-body').innerHTML='';return;}
 const option=(v,label)=>`<option value="${v}">${label}</option>`;
 function field(r,k,values,disabled=false){return `<select data-task="${r.task_id}" data-field="${k}" aria-label="${r.task_id} ${k}" ${disabled?'disabled':''}>${option('','—')}${values.map(v=>`<option value="${v}" ${r[k]===v?'selected':''}>${v}</option>`).join('')}</select>`;}
 $('#trace-body').innerHTML=rows.map(r=>{const n=pkg.plan.nodes.find(n=>n.id===r.task_id);return `<tr class="${scanIssues.some(i=>i.startsWith(r.task_id+' /'))?'uncertain':''}"><td>${r.task_id}</td><td>${field(r,'order',[1,2,3,4,5,6,7,8])}</td><td>${field(r,'first_answer',['A','B','C','D'],n.type!=='choice_question')}</td><td>${field(r,'hint_level',[0,1,2],n.type!=='choice_question')}</td><td>${field(r,'retry_answer',['A','B','C','D'],n.type!=='choice_question')}</td></tr>`;}).join('');
 $('#trace-source').textContent=traceSource==='synthetic'?'SYNTHETIC SAMPLE':traceSource==='scan'?'Local scan · review required':'Manual entry';
 document.querySelectorAll('#trace-body select').forEach(e=>e.onchange=()=>{const row=rows.find(r=>r.task_id===e.dataset.task);row[e.dataset.field]=e.value===''?null:['order','hint_level'].includes(e.dataset.field)?Number(e.value):e.value;$('#trace-confirmed').checked=false;saveDraft();});
}
function renderResults(){
 const e=pkg?.evaluation,s=student();if(!e){$('#results-content').innerHTML='<div class="empty">Collect and confirm a record first. Its observations will appear here.</div>';return;}
 $('#results-content').innerHTML=`<div class="section-heading"><h2>Round ${pkg.round} / Observations</h2><span class="pill">${e.source==='synthetic'||s?.synthetic?'SYNTHETIC DATA':esc(e.source.toUpperCase())} · revision ${pkg.trace_revision}</span></div><p>${esc(e.path.join(' → '))}</p><div class="result-metrics"><div><strong>${e.first_correct} / ${e.first_total}</strong><small>Correct first answers / readable first answers</small></div><div><strong>${e.independent_correct} / ${e.independent_total}</strong><small>Correct without reported hints / hint-free answers</small></div><div><strong>${e.warnings.length}</strong><small>Path issues preserved for review</small></div></div>${e.warnings.map(w=>`<div class="warning">${esc(w)}</div>`).join('')}<table class="result-table"><thead><tr><th>Task</th><th>First answer</th><th>Hint</th><th>Observation</th></tr></thead><tbody>${e.results.map(r=>`<tr><td>${r.task_id}</td><td>${esc(r.first_answer||'Unknown')}</td><td>${r.hint_level??'Unknown'}</td><td>${r.first_correct===null?esc(r.completion.replaceAll('_',' ')):r.first_correct?'Correct':'Needs another check'}</td></tr>`).join('')}</tbody></table><div class="callout"><b>Next planning state: ${esc(s?.state.status.replaceAll('_',' ')||'unknown')}</b><p>${esc(e.note)} Paper hints and visit order are self-reported.</p></div><div class="button-row" style="margin-top:22px"><button id="next-round" class="primary">Plan the next round →</button><button id="export-round" class="secondary">Export this round’s JSON</button></div>`;
 $('#next-round').onclick=()=>{show('plan');window.scrollTo({top:0,behavior:'smooth'});toast('The next generation will include the confirmed evidence. Choose a planning mode, then generate.');};
 $('#export-round').onclick=()=>{const copy=structuredClone(pkg);delete copy.student_token;download(pkg.id+'.json',JSON.stringify(copy,null,2));};
}
function renderCanvas(){
 if(!scanImage)return;const c=$('#scan-canvas');c.width=scanImage.width;c.height=scanImage.height;c.dataset.loaded='1';const ctx=c.getContext('2d');ctx.drawImage(scanImage,0,0);corners.forEach((p,i)=>{ctx.fillStyle='#d24a2e';ctx.beginPath();ctx.arc(p.x,p.y,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.font='bold 13px sans-serif';ctx.textAlign='center';ctx.fillText(i+1,p.x,p.y+4);});
 $('#corner-help').textContent=corners.length===4?'Four markers selected. Adjust by resetting, or read the marked circles.':`Click ${['top-left','top-right','bottom-right','bottom-left'][corners.length]} black marker centre (${corners.length}/4).`;
}
async function setScan(file,source='scan'){
 requirePackage();scanImage=await loadImage(file);scanSource=source;scanRead=false;scanOriginal=null;corners=[];scanIssues=[];rows=blankRows(pkg);traceSource=source;$('#trace-confirmed').checked=false;renderRows();
 try{corners=autoCorners(scanImage);}catch(e){toast(e.message,true);}renderCanvas();$('#scan-issues').textContent='Image loaded locally. Check the red marker positions, then read.';
}
function requirePackage(){if(!pkg||pkg.status==='draft')throw Error('Open and approve a package first.');}
async function sampleBlob(){requirePackage();const svg=recordSVG(pkg,sampleRows(pkg,'support'));const image=await loadImage(new Blob([svg],{type:'image/svg+xml'}));return new Promise(resolve=>image.toBlob(resolve,'image/png'));}

document.querySelectorAll('.nav').forEach(b=>b.onclick=async()=>{try{const tab=b.dataset.tab;if(tab==='scan'&&(!pkg||pkg.status==='draft')){const p=selectedPackages().filter(x=>x.status!=='draft').at(-1);if(p)await openPackage(p.id);}if(tab==='results'&&!pkg){const p=selectedPackages().filter(x=>x.status==='evaluated').at(-1);if(p)await openPackage(p.id);}show(tab);}catch(e){toast(e.message,true);}});
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>document.getElementById(b.dataset.close).close());
on('#seed-button','click',async()=>{await api('/api/seed',{});await refresh();toast('Two synthetic learners loaded. Their baseline responses lead to different plans.');});
on('#start-button','click',()=>{if(!studentId)$('#add-student').click();else show('plan');});
on('#student-select','change',async e=>{studentId=e.target.value;pkg=null;rows=[];scanImage=null;corners=[];scanIssues=[];$('#package-panel').hidden=true;await refresh();renderRows();renderResults();$('#scan-canvas').removeAttribute('data-loaded');});
on('#add-student','click',()=>{$('#diagnostic-fields').innerHTML=data.diagnostic.map(q=>`<label>${esc(q.prompt)}<select name="${q.id}"><option value="">Unknown / not taken</option>${q.options.map(o=>`<option value="${o.id}">${o.id}. ${esc(o.text)}</option>`).join('')}</select></label>`).join('');$('#student-dialog').showModal();});
on('#student-form','submit',async e=>{e.preventDefault();const f=new FormData(e.target),button=e.target.querySelector('button[type=submit]');button.disabled=true;try{const s=await api('/api/students',{label:f.get('label'),grade:f.get('grade'),class_name:f.get('class_name'),diagnostic:Object.fromEntries(['D01','D02','D03'].map(k=>[k,f.get(k)||null]))});studentId=s.id;pkg=null;$('#package-panel').hidden=true;await refresh();$('#student-dialog').close();show('plan');toast('Learner created. Set the teaching brief and generate a plan.');}finally{button.disabled=false;}});
on('#settings-button','click',()=>{const f=$('#settings-form');f.elements.base_url.value=data.provider.base_url;f.elements.model.value=data.provider.model;f.elements.api_key.value='';$('#settings-dialog').showModal();});
on('#settings-form','submit',async e=>{e.preventDefault();const f=new FormData(e.target);await api('/api/settings',Object.fromEntries(f.entries()));e.target.elements.api_key.value='';$('#settings-dialog').close();await refresh();toast('Provider configuration saved in server memory. Live mode is now available if a key is configured.');});
on('#plan-form','submit',async e=>{e.preventDefault();if(!studentId)throw Error('Create a learner first.');const f=new FormData(e.target),b=$('#generate-button');b.disabled=true;$('#student-select').disabled=true;b.textContent=f.get('mode')==='live'?'Planning with live AI…':'Building rehearsal plan…';try{const p=await api('/api/generate',{student_id:studentId,mode:f.get('mode'),request_id:crypto.randomUUID(),config:teachingConfig()});await refresh();await openPackage(p.id);$('#package-panel').scrollIntoView({behavior:'smooth',block:'start'});toast('Draft ready. Review the content before issuing it.');}finally{b.disabled=false;$('#student-select').disabled=false;b.textContent='Generate learning plan ↗';}});
on('#approve-button','click',async()=>{if(!$('#reviewed').checked)throw Error('Review and confirm the questions, worked answers and coach notes first.');await api('/api/packages/'+pkg.id+'/approve',{plan_hash:pkg.plan_hash,reviewed:true});await refresh();await openPackage(pkg.id);toast('Package approved. This version is frozen for printing and scanning.');});
document.querySelectorAll('[data-print]').forEach(b=>b.onclick=()=>{if(!pkg)return;window.open(`/print.html?id=${encodeURIComponent(pkg.id)}&view=${b.dataset.print}`,'_blank','noopener');});
on('#student-view-button','click',()=>{requirePackage();window.open(`/learn.html?id=${pkg.id}&token=${encodeURIComponent(pkg.student_token)}`,'_blank','noopener');});
on('#collect-button','click',()=>{requirePackage();show('scan');window.scrollTo(0,0);});
on('#scan-package-select','change',async e=>{if(e.target.value)await openPackage(e.target.value);});
on('#scan-file','change',async e=>{if(e.target.files[0])await setScan(e.target.files[0]);});
on('#sample-scan-button','click',async()=>{await setScan(await sampleBlob(),'synthetic');toast('Synthetic filled sheet loaded. Read it to test the local scanner.');});
on('#sample-image-button','click',async()=>{const b=await sampleBlob();download(pkg.id+'-SYNTHETIC.png',b,'image/png');});
on('#auto-corners','click',()=>{if(!scanImage)throw Error('Upload a record image first.');corners=autoCorners(scanImage);scanRead=false;renderCanvas();});
on('#reset-corners','click',()=>{corners=[];scanRead=false;renderCanvas();});
on('#scan-canvas','click',e=>{if(!scanImage)return;if(corners.length>=4)corners=[];const box=e.target.getBoundingClientRect();corners.push({x:(e.clientX-box.left)*e.target.width/box.width,y:(e.clientY-box.top)*e.target.height/box.height});scanRead=false;renderCanvas();});
on('#read-sheet','click',()=>{requirePackage();if(!scanImage)throw Error('Upload a record image first.');const result=readSheet(scanImage,corners,pkg);rows=result.rows;scanOriginal=structuredClone(result.rows);scanIssues=result.issues;traceSource=scanSource;scanRead=true;$('#trace-confirmed').checked=false;renderRows();$('#scan-issues').innerHTML=`<p>Sheet ${esc(result.code)} matched. ${result.issues.length} ambiguous field(s).</p>${result.issues.map(i=>`<p class="warning">${esc(i)}</p>`).join('')}<p>All rows require teacher confirmation before saving.</p>`;toast('Marks read. Review the table, including any blanks, and confirm.');});
on('#manual-clear','click',()=>{requirePackage();rows=blankRows(pkg);traceSource='manual';scanIssues=[];scanRead=false;scanOriginal=null;$('#trace-confirmed').checked=false;renderRows();});
on('#sample-ready-button','click',()=>{requirePackage();rows=sampleRows(pkg,'ready');traceSource='synthetic';scanIssues=[];scanRead=false;scanOriginal=null;$('#trace-confirmed').checked=false;renderRows();});
on('#save-trace','click',async()=>{requirePackage();if(!$('#trace-confirmed').checked)throw Error('Check the record and tick the confirmation box.');if(traceSource==='scan'&&!scanRead)throw Error('Read this image first, or clear the table for manual entry.');const trace={package_id:pkg.id,package_version:pkg.version,confirmed:true,source:traceSource,rows,scan_review:scanOriginal?{method:'local-omr-v1',original_rows:scanOriginal,issues:scanIssues,corrected_fields:rows.flatMap(r=>Object.keys(r).filter(k=>k!=='task_id'&&r[k]!==scanOriginal.find(x=>x.task_id===r.task_id)?.[k]).map(k=>({task_id:r.task_id,field:k,from:scanOriginal.find(x=>x.task_id===r.task_id)?.[k]??null,to:r[k]})))}:null};const result=await api('/api/packages/'+pkg.id+'/trace',{trace,expected_revision:pkg.trace_revision||0});localStorage.removeItem('paper-draft-'+pkg.id);await refresh();await openPackage(pkg.id);show('results');window.scrollTo(0,0);toast(result.duplicate?'Identical record already saved. No duplicate result was added.':'Evidence saved. The next plan will use these observations.');});
on('#export-button','click',async()=>{download('paper-ai-local-export.json',JSON.stringify(await api('/api/export'),null,2));toast('Export downloaded. Review free text and aliases before sharing it.');});
startI18n();$('#ui-language').value=locale;$('#plan-form').elements.language.value=locale;if(locale==='zh')$('#plan-form').elements.goal.value='用逆运算解一元一次方程。';
refresh().catch(e=>toast('Cannot connect to the local app: '+e.message,true));


function teachingConfig(){const f=new FormData($('#plan-form'));return {goal:f.get('goal'),offline_days:Number(f.get('offline_days')),max_pages:Number(f.get('max_pages')),language:f.get('language'),question_count:Number(f.get('question_count')),unit_id:f.get('unit_id')};}
on('#ui-language','change',e=>{setLocale(e.target.value);});
function renderBatch(){
 const selected=new Set([...document.querySelectorAll('[data-batch]:checked')].map(x=>x.value));
 const filter=$('#class-filter').value,query=$('#learner-search').value.toLowerCase();
 const classes=[...new Set(data.students.map(s=>s.class_name||'Default'))];
 $('#class-filter').innerHTML='<option value="">All classes</option>'+classes.map(c=>`<option ${c===filter?'selected':''} value="${esc(c)}">${esc(c)}</option>`).join('');
 const visible=data.students.filter(s=>(!filter||(s.class_name||'Default')===filter)&&(!query||(s.label+' '+s.id).toLowerCase().includes(query)));
 $('#batch-learners').innerHTML=visible.map(s=>`<label class="checkbox user-content"><input type="checkbox" data-batch value="${esc(s.id)}" ${selected.has(s.id)?'checked':''}>${esc(s.label)} · ${esc(s.class_name||'Default')}</label>`).join('');
}
on('#learner-search','input',renderBatch);on('#class-filter','change',renderBatch);
async function jobs(){const result=await api('/api/jobs');$('#jobs-list').innerHTML=result.jobs.map(j=>`<p>${esc(j.student_id)} · ${esc(j.status)} · ${esc(j.created_at)} ${j.package_id?`<button data-job="${esc(j.package_id)}">Open round ↗</button>`:''}</p>`).join('');document.querySelectorAll('[data-job]').forEach(b=>b.onclick=async()=>{try{const p=await api('/api/packages/'+b.dataset.job);studentId=p.student_id;await refresh();await openPackage(p.id);show('plan');}catch(e){toast(e.message,true);}});}
on('#jobs-refresh','click',jobs);
on('#batch-generate','click',async()=>{
 const ids=[...document.querySelectorAll('[data-batch]:checked')].map(x=>x.value);if(!ids.length)throw Error(tr('Select learners first.'));
 const config=teachingConfig(),mode=$('#planning-mode').value;let done=0;
 for(const id of ids){$('#batch-status').textContent=`${done} / ${ids.length} · ${id}`;try{await api('/api/generate',{student_id:id,mode,config,request_id:crypto.randomUUID()});done++;}catch(e){$('#batch-status').textContent=`${done} / ${ids.length} · ${tr(e.message)}`;await refresh();await jobs();return;}}
 $('#batch-status').textContent=`${done} / ${ids.length}`;await refresh();await jobs();
});
function batchPrint(view){const selected=new Set([...document.querySelectorAll('[data-batch]:checked')].map(x=>x.value));const ids=[...selected].map(id=>data.packages.filter(p=>p.student_id===id&&p.status!=='draft').at(-1)?.id).filter(Boolean);if(!ids.length)throw Error('Approve a package first');if(ids.length!==selected.size)throw Error(tr('Every selected learner needs an approved package.'));if(ids.length>50)throw Error('Select at most 50 learners');window.open('/print.html?ids='+ids.join(',')+'&view='+view,'_blank','noopener');}
on('#batch-booklets','click',()=>batchPrint('booklet'));on('#batch-records','click',()=>batchPrint('record'));
on('#backup-download','click',async()=>download('paper-ai-backup.json',JSON.stringify(await api('/api/backup'),null,2)));
on('#backup-file','change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>19000000)throw Error('Backup exceeds 19 MB');const backup=JSON.parse(await file.text());if(!confirm(tr('Merge this backup? Existing conflicting records will be rejected.')))return;const result=await api('/api/restore',{backup,confirmed:true});await refresh();toast('Merged records: '+result.merged);}finally{e.target.value='';}});
on('#discard-draft','click',async()=>{if(!pkg||pkg.status!=='draft')return;if(!confirm(tr('Discard this unissued draft?')))return;await api('/api/packages/'+pkg.id+'/discard',{plan_hash:pkg.plan_hash});pkg=null;$('#package-panel').hidden=true;await refresh();});
function saveDraft(){if(pkg)localStorage.setItem('paper-draft-'+pkg.id,JSON.stringify({revision:pkg.trace_revision||0,rows,source:traceSource}));}
function restoreDraft(){if(!pkg)return;try{const draft=JSON.parse(localStorage.getItem('paper-draft-'+pkg.id));if(draft&&draft.revision===(pkg.trace_revision||0)&&draft.rows.length===rows.length){rows=draft.rows;traceSource=draft.source==='scan'?'manual':draft.source;renderRows();toast('Unsaved corrections restored. Check and confirm before saving.');}}catch{}}
window.addEventListener('beforeunload',()=>{if(pkg&&rows.length)saveDraft();});

$('#plan-form').elements.language.addEventListener('change',e=>{const goal=$('#plan-form').elements.goal;if(['Use inverse operations to solve linear equations.','用逆运算解一元一次方程。'].includes(goal.value))goal.value=e.target.value==='zh'?'用逆运算解一元一次方程。':'Use inverse operations to solve linear equations.';});
