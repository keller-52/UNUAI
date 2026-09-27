// All branches are printed before learning. No online call is needed between batches.
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function workbookHTML(p,view){
 const zh=p.config.language==='zh',t=(en,cn)=>zh?cn:en;
 const page=(title,body)=>`<section class="print-page"><header class="print-head"><b>PAPER AI</b><span>${esc(p.id)} · ${esc(p.student_id)}</span></header><h1>${esc(title)}</h1>${body}<footer>PAPER AI</footer></section>`;
 const questions=p.plan.nodes.filter(n=>n.type==='choice_question'),size=p.plan.batch_size;
 const groups=p.plan.batches||p.plan.batch_feedback;
 const name=b=>`${t('Batch','题组')} ${b} · ${groups[b-1].title} (Q${(b-1)*size+1}–Q${b*size})`;
 if(view==='booklet'){
  let html=page(p.plan.title,`<p>${t('Read the lesson, then start at batch 1. Finish the whole batch and record FIRST answers before opening its check pages. Follow the FIRST matching routing rule. All groups are printed, but only do the ones assigned by your route. Leave other record rows blank. No internet or AI call is needed until the final scan.','先读讲解，从题组 1 开始。整批完成并记录首次答案后，再打开对应核对页。按从上到下第一条符合的规则分流。所有题组已提前打印，只做路线指定的题，其他记录行留空；直到最后扫描都无需联网或调用 AI。')}</p>`+p.plan.lesson.map(s=>`<h2>${esc(s.heading)}</h2><p>${esc(s.text)}</p><p><b>${t('Worked example','讲解示例')}</b> ${esc(s.example)}</p>`).join(''));
  for(let offset=0;offset<questions.length;offset+=size){const batch=offset/size+1;
   html+=page(name(batch),`<p>${esc(groups[batch-1].focus)}</p><p>${t('Enter only when directed. Keep first answers unchanged after checking.','仅在规则指向本组时作答。核对后不要擦掉首次答案。')}</p>`+questions.slice(offset,offset+size).map(n=>`<section class="batch-question" data-node="${esc(n.id)}"><h2>${esc(n.id)} · ${esc(n.prompt)}</h2><div class="print-options">${n.options.map(o=>`<p><b>${esc(o.id)}</b> ${esc(o.text)}</p>`).join('')}</div><div class="work-space">${t('Working space','思考与演算区')}</div></section>`).join('')+`<p>${t('Now check this batch in the separate support booklet and follow its routing rule. Do not automatically continue to the next printed group.','本组完成后，立即查看独立核对册中的本组答案，按规则决定去向。不要直接按印刷顺序做下一组。')}</p>`);
  }return html;
 }
 let html='';
 for(let offset=0;offset<questions.length;offset+=size){const batch=offset/size+1,items=questions.slice(offset,offset+size),feedback=p.plan.batch_feedback[batch-1];
  html+=page(`${t('Optional hints','可选提示')} · ${name(batch)}`,
   `<p>${t('Keep separate from questions. Record the highest hint level used. All materials are supplied before starting.','与题册分开装订，开始前全部备齐。记录实际使用的最高提示等级。')}</p>`+items.map(n=>`<section class="teacher-item"><h2>${esc(n.id)}</h2>${n.hints.map((h,i)=>`<p>${i+1}. ${esc(h)}</p>`).join('')}</section>`).join(''));
  html+=page(`${t('Check after completing the batch','整批完成后核对')} · ${name(batch)}`,
   items.map(n=>`<section class="teacher-item"><h2>${esc(n.id)} · ${t('Answer','答案')} ${esc(n.correct_option)}</h2><p>${esc(n.explanation)}</p>${view==='teacher'?`<p>${esc(n.design_reason)}</p>`:''}</section>`).join('')+
   `<h2>${t('Offline routing — use FIRST answers','离线分流——依据首次答案')}</h2><p>${t('Count correct FIRST answers and note wrong question IDs. Read top to bottom and follow only the FIRST matching rule. Retries do not change the route.','统计首次答对题数并记下错题编号。从上到下检查，只执行第一条符合的规则。重试结果不改变本次分流。')}</p>`+feedback.rules.map((r,i)=>`<section class="teacher-item"><h3>${i+1}. ${r.min_correct}–${r.max_correct} / ${size}${r.wrong_any?.length?` · ${t('AND at least one wrong: ','并且这些题至少错一题：')}${esc(r.wrong_any.join(', '))}`:''}</h3><p>${esc(r.feedback)}</p>${r.action==='review_then_continue'?`<p>${t('Read the relevant explanations and retry wrong items before following the destination.','先读相关解析、重试错题，再按以下去向继续。')}</p>`:''}<b>${r.target_batch==='END'?t('END — stop and return all record sheets, including blank pages.','END——结束，交回全部记录纸（含未作答页）。'):t('Go to ','前往 ')+esc(name(r.target_batch))}</b></section>`).join(''));
 }return html;
}
