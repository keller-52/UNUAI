import {paperHTML} from './paper.js';
const params=new URLSearchParams(location.search),id=params.get('id'),view=params.get('view')||'booklet',token=params.get('token');
async function init(){
 if(!['booklet','record','teacher'].includes(view))throw Error('Unknown print view');
 if(token&&view==='teacher')throw Error('Teacher guide is not available from a student link.');
 const res=await fetch(token?`/api/learn/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`:`/api/packages/${encodeURIComponent(id)}`),p=await res.json();
 if(!res.ok)throw Error(p.error);if(p.status==='draft')throw Error('This package needs teacher approval before printing.');
 document.title=`${p.id}-${view}`;document.querySelector('#print-title').textContent=`${p.id} · ${view} · ${p.mode==='live'?'AI planned':'Rules demo'}`;
 document.querySelector('#pages').innerHTML=paperHTML(p,view);
 await document.fonts.ready;
 // Fixed-page compiler must stop when a content block reaches the footer.
 for(const page of document.querySelectorAll('.print-page:not(.record-page)')){
  const footer=page.querySelector('footer');if(!footer)continue;const limit=footer.getBoundingClientRect().top;
  for(const child of page.children)if(child!==footer&&child.getBoundingClientRect().bottom>limit-5)throw Error('Content exceeds the page boundary. Do not print; shorten the coach notes or revise the plan.');
 }
 document.querySelector('#print-button').disabled=false;document.querySelector('#print-button').onclick=()=>window.print();document.body.dataset.ready='1';
}
init().catch(e=>{document.querySelector('#print-error').hidden=false;document.querySelector('#print-error').textContent=e.message;document.body.dataset.error='1';});
