import {workbookHTML} from './workbook.js';
export const W=794, H=1123;
export const MARKERS=[{x:40,y:40},{x:754,y:40},{x:754,y:1083},{x:40,y:1083}];
export const COLS={order:[120,139,158,177,196,215,234,253],first_answer:[305,330,355,380],hint_level:[440,465,490],retry_answer:[560,585,610,635]};
export const rowY=i=>280+i*90;
export const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function sheetBits(code){
 const n=parseInt(code,16),check=((n>>>16)^((n>>>8)&255)^(n&255)^0xA7)&255;
 return n.toString(2).padStart(24,'0')+check.toString(2).padStart(8,'0');
}
export function decodeBits(bits){
 if(!/^[01]{32}$/.test(bits))throw Error('The sheet code is ambiguous. Reposition the corner markers or use a clearer image.');
 const code=parseInt(bits.slice(0,24),2).toString(16).padStart(6,'0').toUpperCase();
 if(sheetBits(code)!==bits)throw Error('Sheet code checksum failed. Check orientation, corners and image clarity.');
 return code;
}
export function blankRows(p){return p.plan.nodes.map(n=>({task_id:n.id,order:null,first_answer:null,hint_level:null,retry_answer:null}));}
export function sampleRows(p,kind='support'){
 const rows=blankRows(p),nodes=Object.fromEntries(p.plan.nodes.map(n=>[n.id,n]));
 if(p.plan.layout==='batch-v1'&&p.plan.routing_version==='free-guidance-1'){
  for(const r of rows){if(nodes[r.task_id].type==='choice_question'){r.first_answer=nodes[r.task_id].correct_option;r.hint_level=0;}}return rows;
 }
 if(p.plan.layout==='batch-v1'){
  let batch=1;const size=p.plan.batch_size;
  const seen=new Set();
  while(batch!=='END'&&!seen.has(batch)){
   seen.add(batch);
   const wrong=[];let correct=0;
   for(let i=(batch-1)*size+1;i<=batch*size;i++){
    const n=nodes['Q'+i],r=rows.find(x=>x.task_id===n.id),fail=kind==='support'&&batch===1&&i%2===0;
    r.first_answer=fail?n.options.find(o=>o.id!==n.correct_option).id:n.correct_option;r.hint_level=fail?1:0;
    if(fail)wrong.push(n.id);else correct++;
   }
   const rule=p.plan.batch_feedback[batch-1].rules.find(r=>r.min_correct<=correct&&correct<=r.max_correct&&(!r.wrong_any?.length||r.wrong_any.some(id=>wrong.includes(id))));
   if(!rule)break;batch=rule.target_batch;
  }
  return rows;
 }

 let id=p.plan.entry_node,order=1;
 while(id){
  const n=nodes[id],r=rows.find(x=>x.task_id===id);r.order=order++;
  if(n.type==='choice_question'){
   const fail=kind==='support'&&id==='Q1';
   r.first_answer=fail?n.options.find(o=>o.id!==n.correct_option&&o.id!=='D').id:n.correct_option;
   r.hint_level=fail?1:0;
   id=n.routes.find(x=>x.answer===r.first_answer).next;
  }else id=n.next;
 }
 return rows;
}
export function recordPacket(p,index=0){
 const sheet=p.record_sheets?.[index];if(!sheet)return p;
 return {...p,sheet_code:sheet.code,record_page:index+1,record_total:p.record_sheets.length,
  plan:{...p.plan,nodes:p.plan.nodes.filter(n=>sheet.task_ids.includes(n.id))}};
}
export function recordSVG(p,filled=null){
 const bits=sheetBits(p.sheet_code),by=Object.fromEntries((filled||[]).map(r=>[r.task_id,r]));
 const t=(x,y,s,size=12,extra='')=>`<text x="${x}" y="${y}" font-size="${size}" ${extra}>${esc(s)}</text>`;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="794" height="1123" fill="white"/><g fill="black" font-family="Arial, sans-serif">`;
 for(const m of MARKERS)svg+=`<rect x="${m.x-9}" y="${m.y-9}" width="18" height="18"/>`;
 svg+=t(65,70,'PAPER AI / LEARNING RECORD',23,'font-weight="bold"');
 svg+=t(65,94,`${p.student_id}  ·  Round ${p.round}  ·  ${p.id} / v${p.version}`);
 svg+=t(65,114,`Template OMR-1  ·  Sheet ${p.sheet_code}  ·  Page ${p.record_page||1} of ${p.record_total||1}  ·  ${filled?'SYNTHETIC SAMPLE':'English / A4'}`);
 bits.split('').forEach((b,i)=>{svg+=`<rect x="${80+i*19}" y="140" width="12" height="16" fill="${b==='1'?'black':'white'}" stroke="#bbb" stroke-width="0.5"/>`;});
 svg+=t(65,182,'Fill circles completely with a dark pen. Do not erase your first answer.',13);
 svg+=t(65,202,p.plan.layout==='batch-v1'?'Follow batch routes. Leave unassigned rows blank. Check only after a whole batch.':'Mark visit order for every visited task. Leave unvisited rows completely blank.',13);
 svg+=t(65,222,p.plan.layout==='batch-v1'?'Hints: 0 = none, 1 = first, 2 = both. Keep first answers; retry separately.':'Hint: 0 = none, 1 = first hint, 2 = both. Retry is optional. Follow FIRST answer routes.',12);
 svg+=t(63,250,'Task',12,'font-weight="bold"')+t(116,250,'Visit order',12,'font-weight="bold"')+t(300,250,'First answer',12,'font-weight="bold"')+t(433,250,'Hint',12,'font-weight="bold"')+t(556,250,'Retry',12,'font-weight="bold"');
 p.plan.nodes.forEach((n,i)=>{
  const y=rowY(i),r=by[n.id]||{};
  svg+=`<path d="M65 ${y+57}H720" stroke="#ccc" stroke-width="1"/>`+t(65,y+5,n.id,16,'font-weight="bold"');
  for(const [field,xs] of Object.entries(COLS)){
   if(field==='order'&&p.plan.layout==='batch-v1')continue;
   if(field!=='order'&&n.type!=='choice_question')continue;
   xs.forEach((x,j)=>{
    const value=field==='order'?j+1:field==='hint_level'?j:String.fromCharCode(65+j);
    const checked=r[field]===value;
    svg+=`<circle cx="${x}" cy="${y}" r="6" fill="${checked?'black':'white'}" stroke="black" stroke-width="1"/>`;
    svg+=t(x,y+23,value,11,'text-anchor="middle"');
   });
  }
  if(n.type!=='choice_question')svg+=t(302,y+5,n.type==='finish'?'Finish / no answer needed':'Read explanation / no answer needed',12);
 });
 svg+=t(65,997,'First answers, hint use and visit order are self-reported. Keep this sheet for scanning.',12);
 svg+=t(65,1019,'If you make a marking mistake, ask the teacher to correct it during review.',12);
 svg+=t(65,1042,'Please keep all four black corner markers visible in the photograph.',12);
 return paperTranslate(svg+'</g></svg>',p.config?.language);
}
export function nodePage(id){return id==='END'?3:Number(id.slice(1));}
function routeText(n){return n.routes.map(r=>`${esc(r.answer)} → <span data-target="${esc(r.next)}">${esc(r.next)}</span>`).join(' · ');}
export function bookletHTML(p){
 const count=p.plan.nodes.filter(n=>n.type==='choice_question').length;
 return p.plan.nodes.filter(n=>n.type==='choice_question').map((n,i)=>{
  const remedy=p.plan.nodes.find(x=>x.id===`R${i+1}`);
  return `<section class="print-page"><header class="print-head"><b>PAPER AI</b><span>${esc(p.student_id)} · Round ${p.round} · ${esc(p.id)} / v${p.version}</span></header>
  <div class="print-kicker">${esc(p.mode==='live'?'AI-PLANNED LEARNING':'RULES DEMO / NO AI CALL')} · ${i+1} / ${count} · Day ${p.schedule?.find(x=>x.task_id===n.id)?.day||1}</div>
  <h1>${esc(p.plan.title)}</h1><p class="print-intro">${i===0?'Start at Q1. Record the first answer before looking at hints. Follow the route for your FIRST answer. Mark the visit order for each task you enter.':'Continue only if your previous task directs you here.'}</p>
  <h2 data-node="${n.id}">${esc(n.id)} / ${esc(n.prompt)}</h2><div class="print-options">${n.options.map(o=>`<p><b>${o.id}</b> ${esc(o.text)}</p>`).join('')}</div>
  <div class="work-space">Working space</div><div class="print-route">${routeText(n)}</div>
  <section class="print-hints"><h3>Hints — use only when needed</h3>${n.hints.map((h,j)=>`<p><b>${j+1}.</b> ${esc(h)}</p>`).join('')}<p>Mark the highest hint level you used: 0, 1 or 2.</p></section>
  ${remedy?`<section class="print-remedy" data-node="${remedy.id}"><h3>${esc(remedy.id)} / Open only if directed</h3><p>${esc(remedy.text)}</p><p>${esc(remedy.coach_note)}</p><b>Continue to <span data-target="${esc(remedy.next)}">${esc(remedy.next)}</span>.</b></section>`:`<section class="print-remedy" data-node="END"><h3>END / Finish</h3><p>Mark END in your visit order. Check your record sheet and return it to your teacher.</p></section>`}
  <footer>PAPER AI · Local prototype · Self-reported learning record · Page ${i+1}</footer></section>`;
 }).join('');
}
export function teacherHTML(p){
 return `<section class="print-page"><header class="print-head"><b>PAPER AI / TEACHER ONLY</b><span>${esc(p.id)} / v${p.version}</span></header><h1>Answer & route guide</h1><p>${esc(p.proposal.reason)}</p>
 ${p.plan.nodes.filter(n=>n.type==='choice_question').map(n=>`<section class="teacher-item"><h2 data-node="${n.id}">${esc(n.id)} · ${esc(n.prompt)}</h2><p><b>Answer: ${esc(n.correct_option)}</b> · ${n.origin==='ai_generated'?(p.config.language==='zh'?'AI 新题':'AI authored'):(p.config.language==='zh'?'题库引用':'Bank reference')} ${esc(n.bank_id)}</p><p>${esc(n.explanation)}</p>${n.design_reason?`<p>${esc(n.design_reason)}</p>`:''}<p>${routeText(n)}</p></section>`).join('')}
 <h3>Evidence references</h3><p>${esc(p.proposal.evidence_refs.join(', ')||'No baseline evidence yet.')}</p><h3>Source and verification</h3><p>Questions may be AI-authored or selected from the reference bank. Arithmetic is checked; review all teaching prose.</p><p>Mode: ${esc(p.mode)} · Model: ${esc(p.audit.model||'none — rules demo')} · Compiler: ${esc(p.compiler_version)}</p><footer>Do not distribute this answer guide with the student packet.</footer></section>`;
}
export function paperHTML(p,view){
 if(p.plan.layout==='batch-v1'){
  if(view==='record')return p.record_sheets.map((sheet,i)=>`<section class="print-page record-page">${recordSVG(recordPacket(p,i))}</section>`).join('');
  return workbookHTML(p,view);
 }
 if(view==='teacher')return paperTranslate(teacherHTML(p),p.config?.language);
 if(view==='record')return `<section class="print-page record-page">${recordSVG(p)}</section>`;
 return paperTranslate(bookletHTML(p),p.config?.language);
}

const paperTerms={
 'Follow batch routes. Leave unassigned rows blank. Check only after a whole batch.':'整批作答完成后再核对。本记录纸无需填写访问顺序。','Hints: 0 = none, 1 = first, 2 = both. Keep first answers; retry separately.':'提示：0 未使用，1 一级，2 两级。保留首次答案，重试单独填写。','PAPER AI / LEARNING RECORD':'PAPER AI / 学习记录', 'SYNTHETIC SAMPLE':'模拟样张', 'English / A4':'中文 / A4',
 'Fill circles completely with a dark pen. Do not erase your first answer.':'使用深色笔填满圆圈，不要擦掉首次答案。',
 'Mark visit order for every visited task. Leave unvisited rows completely blank.':'记录每个任务的访问顺序；未访问的任务整行留空。',
 'Hint: 0 = none, 1 = first hint, 2 = both. Retry is optional. Follow FIRST answer routes.':'提示：0 不使用，1 一级，2 两级。重试选填；按首次答案跳转。',
 'First answers, hint use and visit order are self-reported. Keep this sheet for scanning.':'首次答案、提示使用和访问顺序均由学生自报，请保留此纸用于扫描。',
 'If you make a marking mistake, ask the teacher to correct it during review.':'填涂错误请在校对时告知教师。',
 'Please keep all four black corner markers visible in the photograph.':'拍照时保留四角的黑色定位标记。',
 'Finish / no answer needed':'结束 / 无需作答','Read explanation / no answer needed':'阅读讲解 / 无需作答',
 'Start at Q1. Record the first answer before looking at hints. Follow the route for your FIRST answer. Mark the visit order for each task you enter.':'从 Q1 开始。先记录首次答案，再查看提示。按首次答案跳转，并记录所有任务的访问顺序。',
 'Continue only if your previous task directs you here.':'仅在上一任务要求时进入本页。',
 'Mark the highest hint level you used: 0, 1 or 2.':'填写使用的最高提示等级：0、1 或 2。',
 'Mark END in your visit order. Check your record sheet and return it to your teacher.':'记录 END 的访问顺序，检查记录纸并交给教师。',
 'Questions may be AI-authored or selected from the reference bank. Arithmetic is checked; review all teaching prose.':'题目可由 AI 创作或引用参考题库。算式已校验，所有讲解文字仍需教师审核。',
 'Do not distribute this answer guide with the student packet.':'教师答案请勿与学生材料一起发放。',
 'Hints — use only when needed':'提示——按需查看', 'Open only if directed':'仅按指示阅读', 'Working space':'演算区',
 'Answer &amp; route guide':'答案与路径指南', 'Answer & route guide':'答案与路径指南', 'No baseline evidence yet.':'暂无初始诊断证据。', 'Evidence references':'证据引用', 'Source and verification':'来源与校验',
 'AI-PLANNED LEARNING':'AI 规划学习包', 'RULES DEMO / NO AI CALL':'规则演示 / 未调用 AI',
 'PAPER AI / TEACHER ONLY':'PAPER AI / 教师专用', 'Visit order':'访问顺序','First answer':'首次答案',
 'Self-reported learning record':'学生自报学习记录', 'Local prototype':'本地应用', 'Continue to':'继续前往',
 'Finish':'完成','Task':'任务','Retry':'重试','Hint':'提示','Round':'轮次','Page':'页','Day':'学习日',
 'Answer:':'答案：','Bank':'题库','Mode:':'模式：','Model:':'模型：','Compiler:':'编译器：',
 'Template':'模板','Sheet':'记录纸','none — rules demo':'无——规则演示'};
export function paperTranslate(html,language){
 if(language!=='zh')return html;
 // Only translate text nodes; never rewrite IDs, attributes or student content fields.
 return html.replace(/>([^<]+)</g,(all,value)=>{
  for(const [en,zh] of Object.entries(paperTerms))value=value.split(en).join(zh);
  return '>'+value+'<';
 });
}

export function paginate(container,packages,view){
 if(view==='record')return;
 // Teacher routes refer to the student's booklet, not the teacher guide pages.
 const bookletPositions={};
 if(view==='teacher')for(const p of packages){
  if(p.plan.layout==='batch-v1')continue;
  const reference=document.createElement('div');reference.style.cssText='position:absolute;visibility:hidden;left:0;top:0';
  reference.innerHTML=paperHTML(p,'booklet');for(const page of reference.children)page.dataset.package=p.id;
  document.body.append(reference);
  try{
   paginate(reference,[p],'booklet');const positions={};
   reference.querySelectorAll('.print-page').forEach((page,i)=>page.querySelectorAll('[data-node]').forEach(n=>positions[n.dataset.node]=i+1));
   bookletPositions[p.id]=positions;
  }finally{reference.remove();}
 }
 for(const item of container.querySelectorAll('.teacher-item'))item.replaceWith(...item.childNodes);
 for(const rich of container.querySelectorAll('.rich-text')){
  for(const list of rich.querySelectorAll(':scope > ul,:scope > ol')){let i=1;for(const li of [...list.children]){const line=document.createElement('p');line.innerHTML=(list.tagName==='OL'?i+++'. ':'• ')+li.innerHTML;list.before(line);}list.remove();}
  for(const child of rich.children)child.classList.add('rich-block');
  rich.replaceWith(...rich.childNodes);
 }
 const originals=[...container.querySelectorAll('.print-page')];
 for(const page of originals){
  const group=page.dataset.package;
  let current=page;
  let remaining=[...page.children].filter(x=>!x.matches('footer,.print-head'));
  remaining.forEach(block=>block.remove());
  const header=page.querySelector('.print-head'),footer=page.querySelector('footer');
  for(const block of remaining){
   current.insertBefore(block,current.querySelector('footer'));
   if(block.getBoundingClientRect().bottom<=current.querySelector('footer').getBoundingClientRect().top-8)continue;
   const next=document.createElement('section');next.className='print-page';next.dataset.package=group;
   if(header)next.append(header.cloneNode(true));next.append(footer.cloneNode(true));current.after(next);
   const previous=block.previousElementSibling;
   if(previous&&previous.matches('h2,h3,h4'))next.insertBefore(previous,next.querySelector('footer'));
   next.insertBefore(block,next.querySelector('footer'));current=next;
   if(block.getBoundingClientRect().bottom>current.querySelector('footer').getBoundingClientRect().top-8)
    throw Error('A content block exceeds one page. Revise the draft before printing.');
  }
 }
 for(const p of packages){
  const pages=[...container.querySelectorAll('.print-page')].filter(x=>x.dataset.package===p.id);
  if(view==='booklet'&&pages.length>p.config.max_pages)throw Error('Page budget exceeded: '+pages.length+' / '+p.config.max_pages);
  const positions=bookletPositions[p.id]||{};
  if(view!=='teacher')pages.forEach((page,i)=>page.querySelectorAll('[data-node]').forEach(n=>positions[n.dataset.node]=i+1));
  pages.forEach((page,i)=>{
   page.querySelector('footer').textContent=`PAPER AI · ${p.id} · ${p.config.language==='zh'?'页':'Page'} ${i+1} / ${pages.length}`;
   page.querySelectorAll('[data-target]').forEach(n=>{n.textContent=n.dataset.target+' ('+(p.config.language==='zh'?'页 ':'p. ')+(positions[n.dataset.target]||positions[n.dataset.target.replace('R','Q')]||pages.length)+')';});
  });
 }
 for(const page of container.querySelectorAll('.print-page')){
  const limit=page.querySelector('footer').getBoundingClientRect().top-5;
  for(const child of page.children)if(!child.matches('footer')&&child.getBoundingClientRect().bottom>limit)throw Error('Page overflow after route layout; revise the draft.');
 }
}

