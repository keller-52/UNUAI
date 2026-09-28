import {W,H,MARKERS,COLS,rowY,decodeBits} from './paper.js';

// Homography maps coordinates on the canonical printed sheet to the uploaded photo.
function solve(a,b){
 const n=b.length,m=a.map((r,i)=>[...r,b[i]]);
 for(let i=0;i<n;i++){
  let k=i;for(let j=i+1;j<n;j++)if(Math.abs(m[j][i])>Math.abs(m[k][i]))k=j;
  if(Math.abs(m[k][i])<1e-8)throw Error('Corner points are degenerate. Select four different corners.');
  [m[i],m[k]]=[m[k],m[i]];const v=m[i][i];for(let c=i;c<=n;c++)m[i][c]/=v;
  for(let r=0;r<n;r++)if(r!==i){const f=m[r][i];for(let c=i;c<=n;c++)m[r][c]-=f*m[i][c];}
 }
 return m.map(r=>r[n]);
}
export function homography(points){
 if(points.length!==4)throw Error('Select the centres of all four black markers.');
 const a=[],b=[];
 MARKERS.forEach(({x,y},i)=>{const {x:u,y:v}=points[i];a.push([x,y,1,0,0,0,-u*x,-u*y]);b.push(u);a.push([0,0,0,x,y,1,-v*x,-v*y]);b.push(v);});
 const h=solve(a,b);return (x,y)=>{const d=h[6]*x+h[7]*y+1;return{x:(h[0]*x+h[1]*y+h[2])/d,y:(h[3]*x+h[4]*y+h[5])/d};};
}
function luminance(data,w,h,x,y){
 x=Math.round(x);y=Math.round(y);if(x<0||y<0||x>=w||y>=h)return 255;
 const p=(y*w+x)*4;return data[p]*.299+data[p+1]*.587+data[p+2]*.114;
}
export function autoCorners(canvas){
 // Search connected dark components in each outer quadrant. Manual correction is always available.
 const scale=Math.min(1,1000/canvas.width),small=document.createElement('canvas');
 small.width=Math.round(canvas.width*scale);small.height=Math.round(canvas.height*scale);
 const ctx=small.getContext('2d',{willReadFrequently:true});ctx.drawImage(canvas,0,0,small.width,small.height);
 const {width:w,height:h}=small,im=ctx.getImageData(0,0,w,h).data,visited=new Uint8Array(w*h),candidates=[];
 const levels=[];for(let i=0;i<w*h;i+=31)levels.push((im[i*4]+im[i*4+1]+im[i*4+2])/3);levels.sort((a,b)=>a-b);
 const cutoff=Math.min(180,levels[Math.floor(levels.length*.85)]-50);
 const dark=i=>(im[i*4]+im[i*4+1]+im[i*4+2])/3<cutoff;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const start=y*w+x;
  if(visited[start]||!dark(start))continue;
  const stack=[start];visited[start]=1;let count=0,x0=x,x1=x,y0=y,y1=y;
  while(stack.length){const k=stack.pop(),xx=k%w,yy=Math.floor(k/w);count++;x0=Math.min(x0,xx);x1=Math.max(x1,xx);y0=Math.min(y0,yy);y1=Math.max(y1,yy);
   for(const [nx,ny] of [[xx-1,yy],[xx+1,yy],[xx,yy-1],[xx,yy+1]])if(nx>=0&&ny>=0&&nx<w&&ny<h){const n=ny*w+nx;if(!visited[n]&&dark(n)){visited[n]=1;stack.push(n);}}
  }
  const bw=x1-x0+1,bh=y1-y0+1,cx=(x0+x1)/2,cy=(y0+y1)/2;
  if(count>=16&&bw/bh>.5&&bw/bh<2&&count/(bw*bh)>.7&&bw<w*.08&&bh<h*.08)candidates.push({x:cx,y:cy,area:count});
 }
 const targets=[{x:0,y:0},{x:w,y:0},{x:w,y:h},{x:0,y:h}];
 return targets.map((t,i)=>{
  const c=candidates.filter(p=>(i===0||i===3?p.x<w*.4:p.x>w*.6)&&(i<2?p.y<h*.3:p.y>h*.7));
  c.sort((a,b)=>Math.hypot(a.x-t.x,a.y-t.y)-Math.hypot(b.x-t.x,b.y-t.y));
  if(!c.length)throw Error('Automatic marker detection was incomplete. Click the four marker centres manually.');
  return {x:c[0].x/scale,y:c[0].y/scale};
 });
}
// Compare the inner disk to its own surrounding paper, excluding the printed outline.
export function markCoverage(data,w,h,map,x,y,contrast=180){
 const rgb=(a,b)=>{const q=map(a,b),xx=Math.round(q.x),yy=Math.round(q.y);if(xx<0||yy<0||xx>=w||yy>=h)return [255,255,255];const i=(yy*w+xx)*4;return [data[i],data[i+1],data[i+2]];};
 const ring=[];for(let k=0;k<32;k++){const a=k*Math.PI/16;ring.push(rgb(x+9*Math.cos(a),y+9*Math.sin(a)));}
 const white=[0,1,2].map(c=>ring.map(p=>p[c]).sort((a,b)=>a-b)[24]);
 const threshold=Math.max(35,Math.min(85,contrast*.3));let filled=0,total=0;
 for(let dx=-4.8;dx<=4.8;dx+=.6)for(let dy=-4.8;dy<=4.8;dy+=.6)if(dx*dx+dy*dy<=4.8*4.8){
  const pixel=rgb(x+dx,y+dy),delta=Math.sqrt(pixel.reduce((s,v,c)=>s+(v-white[c])**2,0)/3);
  if(delta>=threshold)filled++;total++;
 }
 return filled/total;
}
export function readSheet(canvas,points,p){
 const map=homography(points),ctx=canvas.getContext('2d',{willReadFrequently:true});
 const im=ctx.getImageData(0,0,canvas.width,canvas.height).data;
 const sample=(x,y,r=2.5)=>{
  let sum=0,n=0;for(let dx=-r;dx<=r;dx+=1)for(let dy=-r;dy<=r;dy+=1)if(dx*dx+dy*dy<=r*r){const q=map(x+dx,y+dy);sum+=luminance(im,canvas.width,canvas.height,q.x,q.y);n++;}
  return sum/n;
 };
 const black=MARKERS.reduce((s,m)=>s+sample(m.x,m.y,4),0)/4;
 const white=sample(400,70,4);
 if(white-black<45)throw Error('Insufficient contrast or incorrect corners. Try a brighter, sharper photo.');
 const darkness=(x,y,r)=>(white-sample(x,y,r))/(white-black);
 let bits='';for(let i=0;i<32;i++){const d=darkness(86+i*19,148,2);bits+=d>.65?'1':d<.25?'0':'?';}
 const code=decodeBits(bits);
 const sheet=p.record_sheets?.find(s=>s.code===code);
 if(p.record_sheets?.length&&!sheet)throw Error('Wrong record sheet for this package.');
 if(sheet)p={...p,sheet_code:sheet.code,plan:{...p.plan,nodes:p.plan.nodes.filter(n=>sheet.task_ids.includes(n.id))}};
 if(code!==p.sheet_code)throw Error(`This is sheet ${code}; selected package expects ${p.sheet_code}. Select the matching package.`);
 const issues=[],rows=p.plan.nodes.map((n,i)=>{
  const row={task_id:n.id,order:null,first_answer:null,hint_level:null,retry_answer:null};
  for(const [key,xs] of Object.entries(COLS)){
   if(key==='order'&&p.plan.layout==='batch-v1')continue;
   if(key!=='order'&&n.type!=='choice_question')continue;
   const values=xs.map(x=>markCoverage(im,canvas.width,canvas.height,map,x,rowY(i),white-black));
   const chosen=values.map((v,j)=>v>.5?j:-1).filter(x=>x>=0);
   if(chosen.length===1){const j=chosen[0];row[key]=key==='order'?j+1:key==='hint_level'?j:String.fromCharCode(65+j);}
   else if(chosen.length>1||values.some(v=>v>.25))issues.push(`${n.id} / ${key}: ambiguous marks — review required`);

  }
  return row;
 });
 return {rows,issues,code,page:sheet?.page||1,method:'local-omr-area-v2',notice:'Review every row. This reads marks, not handwriting or reasoning.'};
}
export async function loadImage(file){
 const url=URL.createObjectURL(file),img=new Image();
 try{await new Promise((ok,no)=>{img.onload=ok;img.onerror=()=>no(Error('Could not open this image. Use PNG or JPEG.'));img.src=url;});
  const canvas=document.createElement('canvas'),s=Math.min(1,1800/Math.max(img.width,img.height));
  canvas.width=Math.round(img.width*s);canvas.height=Math.round(img.height*s);canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);return canvas;
 }finally{URL.revokeObjectURL(url);}
}
