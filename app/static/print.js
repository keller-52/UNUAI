import {nativeBridge,printView,addNativeBack} from './mobile.js';
import {tr,trError,setLocale} from './i18n.js';
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
 const zh=packages[0].config.language==='zh';setLocale(zh?'zh':'en',false);document.documentElement.lang=zh?'zh-CN':'en';
 addNativeBack(zh?'返回':'Back');
 document.title=`PAPER-AI-${view}`;document.querySelector('#print-title').textContent=packages.map(p=>p.id).join(' · ');
 if(zh){document.querySelector('#print-button').textContent='打印 / 保存 PDF';document.querySelector('#export-pdf').textContent='一键下载 PDF';document.querySelector('#print-help').textContent='打印按钮不可用或无反应时按 Ctrl+P（Mac：Cmd+P）。若内容校验报错，请先修正再打印。';document.querySelector('.preview-note').textContent='A4 · 实际大小（100%）· 关闭浏览器页眉页脚。可在打印窗口保存为 PDF。';}
 const container=document.querySelector('#pages');
 if(nativeBridge())document.querySelector('#print-help').textContent=zh?'通过系统打印选项保存或分享 PDF。':'Use the system print options to save or share a PDF.';
 for(const p of packages){const group=document.createElement('div');group.innerHTML=paperHTML(p,view);for(const page of group.children)page.dataset.package=p.id;container.append(...group.children);}
 await document.fonts.ready;paginate(container,packages,view);
 document.querySelector('#print-button').disabled=false;document.querySelector('#print-button').onclick=()=>printView();document.body.dataset.ready='1';
 const exportButton=document.querySelector('#export-pdf');exportButton.disabled=false;if(nativeBridge())exportButton.textContent=zh?'保存 / 分享 PDF':'Save / share PDF';
 exportButton.onclick=async()=>{if(nativeBridge()){printView();return;}exportButton.disabled=true;const old=exportButton.textContent;exportButton.textContent=zh?'正在导出…':'Exporting…';try{
  const res=await fetch('/api/pdf',{method:'POST',headers:{'Content-Type':'application/json','X-PaperAI':'local-teacher'},body:JSON.stringify({ids,view,token:token||''})});
  if(!res.ok){const error=await res.json();throw Error(error.error);}
  const u=URL.createObjectURL(await res.blob()),a=document.createElement('a');a.href=u;a.download='PAPER-AI-'+view+'.pdf';a.click();setTimeout(()=>URL.revokeObjectURL(u),10000);
 }catch(e){const box=document.querySelector('#print-error');box.hidden=false;box.textContent=trError(e.message);}finally{exportButton.disabled=false;exportButton.textContent=old;}};
 if(params.get('pdf_job'))await reportReady(true);

}
async function reportReady(ready,error=''){return fetch('/api/pdf-ready',{method:'POST',headers:{'Content-Type':'application/json','X-PaperAI':'local-teacher'},body:JSON.stringify({job:params.get('pdf_job'),ready,error})});}
init().catch(async e=>{document.querySelector('#print-error').hidden=false;document.querySelector('#print-error').textContent=trError(e.message);document.body.dataset.error='1';if(params.get('pdf_job'))await reportReady(false,e.message);});
