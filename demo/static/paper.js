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
export function recordSVG(p,filled=null){
 const bits=sheetBits(p.sheet_code),by=Object.fromEntries((filled||[]).map(r=>[r.task_id,r]));
 const t=(x,y,s,size=12,extra='')=>`<text x="${x}" y="${y}" font-size="${size}" ${extra}>${esc(s)}</text>`;
 let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="794" height="1123" fill="white"/><g fill="black" font-family="Arial, sans-serif">`;
 for(const m of MARKERS)svg+=`<rect x="${m.x-9}" y="${m.y-9}" width="18" height="18"/>`;
 svg+=t(65,70,'PAPER AI / LEARNING RECORD',23,'font-weight="bold"');
 svg+=t(65,94,`${p.student_id}  ·  Round ${p.round}  ·  ${p.id} / v${p.version}`);
 svg+=t(65,114,`Template OMR-1  ·  Sheet ${p.sheet_code}  ·  Page 1 of 1  ·  ${filled?'SYNTHETIC SAMPLE':'English / A4'}`);
 bits.split('').forEach((b,i)=>{svg+=`<rect x="${80+i*19}" y="140" width="12" height="16" fill="${b==='1'?'black':'white'}" stroke="#bbb" stroke-width="0.5"/>`;});
 svg+=t(65,182,'Fill circles completely with a dark pen. Do not erase your first answer.',13);
 svg+=t(65,202,'Mark visit order for every visited task. Leave unvisited rows completely blank.',13);
 svg+=t(65,222,'Hint: 0 = none, 1 = first hint, 2 = both. Retry is optional. Follow FIRST answer routes.',12);
 svg+=t(63,250,'Task',12,'font-weight="bold"')+t(116,250,'Visit order',12,'font-weight="bold"')+t(300,250,'First answer',12,'font-weight="bold"')+t(433,250,'Hint',12,'font-weight="bold"')+t(556,250,'Retry',12,'font-weight="bold"');
 p.plan.nodes.forEach((n,i)=>{
  const y=rowY(i),r=by[n.id]||{};
  svg+=`<path d="M65 ${y+57}H720" stroke="#ccc" stroke-width="1"/>`+t(65,y+5,n.id,16,'font-weight="bold"');
  for(const [field,xs] of Object.entries(COLS)){
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
 return svg+'</g></svg>';
}
export function nodePage(id){return id==='END'?3:Number(id.slice(1));}
function routeText(n){return n.routes.map(r=>`${r.answer} → ${r.next} (p. ${nodePage(r.next)})`).join('   ·   ');}
export function bookletHTML(p){
 return p.plan.nodes.filter(n=>n.type==='choice_question').map((n,i)=>{
  const remedy=p.plan.nodes.find(x=>x.id===`R${i+1}`);
  return `<section class="print-page"><header class="print-head"><b>PAPER AI</b><span>${esc(p.student_id)} · Round ${p.round} · ${esc(p.id)} / v${p.version}</span></header>
  <div class="print-kicker">${esc(p.mode==='live'?'AI-PLANNED LEARNING':'RULES DEMO / NO AI CALL')} · ${i+1} / 3</div>
  <h1>${esc(p.plan.title)}</h1><p class="print-intro">${i===0?'Start at Q1. Record the first answer before looking at hints. Follow the route for your FIRST answer. Mark the visit order for each task you enter.':'Continue only if your previous task directs you here.'}</p>
  <h2>${esc(n.id)} / ${esc(n.prompt)}</h2><div class="print-options">${n.options.map(o=>`<p><b>${o.id}</b> ${esc(o.text)}</p>`).join('')}</div>
  <div class="work-space">Working space</div><div class="print-route">${esc(routeText(n))}</div>
  <section class="print-hints"><h3>Hints — use only when needed</h3>${n.hints.map((h,j)=>`<p><b>${j+1}.</b> ${esc(h)}</p>`).join('')}<p>Mark the highest hint level you used: 0, 1 or 2.</p></section>
  ${remedy?`<section class="print-remedy"><h3>${esc(remedy.id)} / Open only if directed</h3><p>${esc(remedy.text)}</p><p>${esc(remedy.coach_note)}</p><b>Continue to ${esc(remedy.next)} (p. ${nodePage(remedy.next)}).</b></section>`:`<section class="print-remedy"><h3>END / Finish</h3><p>Mark END in your visit order. Check your record sheet and return it to your teacher.</p></section>`}
  <footer>PAPER AI · Local prototype · Self-reported learning record · Page ${i+1}</footer></section>`;
 }).join('');
}
export function teacherHTML(p){
 return `<section class="print-page"><header class="print-head"><b>PAPER AI / TEACHER ONLY</b><span>${esc(p.id)} / v${p.version}</span></header><h1>Answer & route guide</h1><p>${esc(p.proposal.reason)}</p>
 ${p.plan.nodes.filter(n=>n.type==='choice_question').map(n=>`<section class="teacher-item"><h2>${esc(n.id)} · ${esc(n.prompt)}</h2><p><b>Answer: ${esc(n.correct_option)}</b> · Bank ${esc(n.bank_id)}</p><p>${esc(n.explanation)}</p><p>${esc(routeText(n))}</p></section>`).join('')}
 <h3>Evidence references</h3><p>${esc(p.proposal.evidence_refs.join(', ')||'No baseline evidence yet.')}</p><h3>Source and verification</h3><p>Author-created arithmetic bank. Equations are checked deterministically. Review AI coach notes for educational quality.</p><p>Mode: ${esc(p.mode)} · Model: ${esc(p.audit.model||'none — rules demo')} · Compiler: ${esc(p.compiler_version)}</p><footer>Do not distribute this answer guide with the student packet.</footer></section>`;
}
export function paperHTML(p,view){
 if(view==='teacher')return teacherHTML(p);
 if(view==='record')return `<section class="print-page record-page">${recordSVG(p)}</section>`;
 return bookletHTML(p);
}
