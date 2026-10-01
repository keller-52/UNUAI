import {esc} from './paper.js';
import {openView} from './mobile.js';
const q=new URLSearchParams(location.search),id=q.get('id'),token=q.get('token');
async function init(){
 const response=await fetch(`/api/learn/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`),p=await response.json();if(!response.ok)throw Error(p.error);
 const zh=p.config.language==='zh';document.documentElement.lang=zh?'zh-CN':'en';
 const link=view=>`/print.html?id=${encodeURIComponent(id)}&token=${encodeURIComponent(token)}&view=${view}`;
 document.querySelector('#student-home').innerHTML=`<small>PAPER AI / ${zh?'纸上学习':'LEARN ON PAPER'}</small><h1>${esc(p.plan.title)}</h1><p>${zh?'开始前备齐题册、核对册和记录纸。先读讲解，从题组 1 开始；每组完成后核对，按纸上指引继续。未分配题目留空，最后交回全部记录纸。':'Prepare the lesson, support booklet and record sheets. Read the lesson and start at group 1. Check each completed group and follow the printed next step. Leave unassigned questions blank; return all record sheets.'}</p><div class="student-actions"><a href="${link('booklet')}">${zh?'讲解与题册':'Lesson and questions'}</a><a href="${link('record')}">${zh?'全部记录纸':'All record sheets'}</a></div>`;
 document.querySelectorAll('.student-actions a').forEach(a=>a.onclick=e=>{e.preventDefault();openView(a.href);});
}
init().catch(e=>document.querySelector('#student-home').textContent=e.message);
