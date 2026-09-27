import {paperHTML,paginate} from './paper.js';
const params=new URLSearchParams(location.search),view=params.get('view')||'booklet',token=params.get('token');
async function init(){
 if(!['booklet','record','teacher','support'].includes(view))throw Error('Unknown print view');
 if(token&&['teacher','support'].includes(view))throw Error('Teacher guide is not available from a student link.');
 const ids=(params.get('ids')||params.get('id')||'').split(',').filter(Boolean);
 if(!ids.length||ids.length>50||token&&ids.length!==1)throw Error('Invalid print selection');
 const packages=[];
 for(const id of ids){
  const res=await fetch(token?`/api/learn/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`:`/api/packages/${encodeURIComponent(id)}`),p=await res.json();
  if(!res.ok)throw Error(p.error);if(p.status==='draft')throw Error('Approve every package before printing.');packages.push(p);
 }
 const zh=packages[0].config.language==='zh';document.documentElement.lang=zh?'zh-CN':'en';
 document.title=`PAPER-AI-${view}`;document.querySelector('#print-title').textContent=packages.map(p=>p.id).join(' · ');
 if(zh){document.querySelector('#print-button').textContent='打印 / 保存 PDF';document.querySelector('.preview-note').textContent='A4 · 实际大小（100%）· 关闭浏览器页眉页脚。可在打印窗口保存为 PDF。';}
 const container=document.querySelector('#pages');
 for(const p of packages){const group=document.createElement('div');group.innerHTML=paperHTML(p,view);for(const page of group.children)page.dataset.package=p.id;container.append(...group.children);}
 await document.fonts.ready;paginate(container,packages,view);
 document.querySelector('#print-button').disabled=false;document.querySelector('#print-button').onclick=()=>window.print();document.body.dataset.ready='1';
}
init().catch(e=>{document.querySelector('#print-error').hidden=false;document.querySelector('#print-error').textContent=e.message;document.body.dataset.error='1';});
