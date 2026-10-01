// Shared browser/native boundary. Desktop keeps ordinary downloads and new windows.
export function nativeBridge(){return window.PaperAINative||window.webkit?.messageHandlers?.paperAI;}
function send(message){const bridge=nativeBridge();if(window.PaperAINative)bridge.postMessage(JSON.stringify(message));else bridge?.postMessage(message);}
export function openView(url){if(nativeBridge())send({action:'open',url:new URL(url,location.href).href});else window.open(url,'_blank','noopener');}
export function printView(){if(nativeBridge())send({action:'print'});else window.print();}
export function addNativeBack(label='Back'){
 if(!nativeBridge())return;
 const bar=document.querySelector('.toolbar')||document.body.insertBefore(Object.assign(document.createElement('div'),{className:'toolbar'}),document.body.firstChild);
 const button=document.createElement('button');button.textContent=label;button.onclick=()=>send({action:'back'});bar.prepend(button);
}
export async function saveFile(name,content,type='application/json'){
 const blob=content instanceof Blob?content:new Blob([content],{type});
 if(nativeBridge()){
  if(blob.size>20000000)throw Error('File exceeds 20 MB');
  const reader=new FileReader();const data=await new Promise((resolve,reject)=>{reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);});
  send({action:'save',name,type:blob.type,data});return;
 }
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
