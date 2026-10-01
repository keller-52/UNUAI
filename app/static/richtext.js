// Small offline Markdown renderer. AI text never becomes raw HTML or executable links.
export const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function inline(s){return escapeHTML(s).replace(/`([^`\n]+)`/g,'<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g,'<em>$1</em>');}
export function markdown(value){
 const lines=String(value??'').replace(/\r/g,'').split('\n');let out='',list='',fence=false,code=[];
 const close=()=>{if(list){out+=`</${list}>`;list='';}};
 for(let i=0;i<lines.length;i++){
  const line=lines[i];if(/^\s*```/.test(line)){close();if(fence){out+='<pre><code>'+escapeHTML(code.join('\n'))+'</code></pre>';code=[];}fence=!fence;continue;}
  if(fence){code.push(line);continue;}
  if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
   close();const cells=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());out+='<table class="prose-table"><thead><tr>'+cells(line).map(x=>'<th>'+inline(x)+'</th>').join('')+'</tr></thead><tbody>';i++;
   while(i+1<lines.length&&lines[i+1].includes('|'))out+='<tr>'+cells(lines[++i]).map(x=>'<td>'+inline(x)+'</td>').join('')+'</tr>';
   out+='</tbody></table>';continue;
  }
  const item=line.match(/^\s*(?:(\d+)[.)]|([-*]))\s+(.+)/);
  if(item){const kind=item[1]?'ol':'ul';if(kind!==list){close();list=kind;out+=`<${kind}>`;}out+='<li>'+inline(item[3])+'</li>';continue;}
  close();if(!line.trim())continue;
  const head=line.match(/^(#{1,6})\s+(.+)/);if(head){const n=Math.min(4,head[1].length+1);out+=`<h${n}>${inline(head[2])}</h${n}>`;}
  else if(/^>\s?/.test(line))out+='<blockquote>'+inline(line.replace(/^>\s?/,''))+'</blockquote>';
  else out+='<p>'+inline(line.trimStart())+'</p>';
 }
 close();if(fence)out+='<pre><code>'+escapeHTML(code.join('\n'))+'</code></pre>';
 return '<div class="rich-text">'+out+'</div>';
}
