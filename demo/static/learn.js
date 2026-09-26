import {esc} from './paper.js';
const q=new URLSearchParams(location.search),id=q.get('id'),token=q.get('token');
async function init(){const response=await fetch(`/api/learn/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`),p=await response.json();if(!response.ok)throw Error(p.error);
 const link=view=>`/print.html?id=${encodeURIComponent(id)}&token=${encodeURIComponent(token)}&view=${view}`;
 document.querySelector('#student-home').innerHTML=`<small>PAPER AI / LEARN ON PAPER</small><h1>${esc(p.plan.title)}</h1><p>${esc(p.student_id)} · Round ${p.round} · ${p.mode==='live'?'AI-planned package':'Rules demonstration package'}</p><div class="student-actions"><a href="${link('booklet')}">Open learning booklet</a><a href="${link('record')}">Open record sheet</a></div><ol><li>Print both documents. Start at Q1.</li><li>Write your first answer before using hints. Follow the first-answer route.</li><li>Mark the order of every task you visit. Keep unvisited rows blank.</li><li>Return the record sheet to your teacher at the next checkpoint.</li></ol><div class="notice">No device is needed while working on the paper. This prototype link is a student printing view on a local teacher application, not a deployed multi-user account system.</div>`;
}
init().catch(e=>document.querySelector('#student-home').textContent=e.message);
