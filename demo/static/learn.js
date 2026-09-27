import {esc} from './paper.js';
const q=new URLSearchParams(location.search),id=q.get('id'),token=q.get('token');
async function init(){const response=await fetch(`/api/learn/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`),p=await response.json();if(!response.ok)throw Error(p.error);
 const zh=p.config.language==='zh';document.documentElement.lang=zh?'zh-CN':'en';
 const link=view=>`/print.html?id=${encodeURIComponent(id)}&token=${encodeURIComponent(token)}&view=${view}`;
 document.querySelector('#student-home').innerHTML=`<small>PAPER AI / LEARN ON PAPER</small><h1>${esc(p.plan.title)}</h1><p>${esc(p.student_id)} · Round ${p.round} · ${p.mode==='live'?'AI-planned package':'Rules demonstration package'}</p><div class="student-actions"><a href="${link('booklet')}">Open learning booklet</a><a href="${link('record')}">Open record sheet</a></div><ol><li>Print both documents. Start at Q1.</li><li>Write your first answer before using hints. Follow the first-answer route.</li><li>Mark the order of every task you visit. Keep unvisited rows blank.</li><li>Return the record sheet to your teacher at the next checkpoint.</li></ol><div class="notice">No device is needed while working on the paper. This prototype link is a student printing view on a local teacher application, not a deployed multi-user account system.</div>`;
 if(zh){const home=document.querySelector('#student-home');home.innerHTML=`<small>PAPER AI / 纸上学习</small><h1>${esc(p.plan.title)}</h1><p>${esc(p.student_id)} · 第 ${p.round} 轮 · ${p.mode==='live'?'AI 规划学习包':'规则演示学习包'}</p><div class="student-actions"><a href="${link('booklet')}">打开学习册</a><a href="${link('record')}">打开记录纸</a></div><ol><li>打印两份材料，从 Q1 开始。</li><li>先记录首次答案，再使用提示。按照首次答案跳转。</li><li>记录任务访问顺序，未访问的任务整行留空。</li><li>在下一次回收时将记录纸交给教师。</li></ol><div class="notice">纸上学习期间无需设备。此链接是本地教师应用的打印视图。</div>`;}

}
init().catch(e=>document.querySelector('#student-home').textContent=e.message);
