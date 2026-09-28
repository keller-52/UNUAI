const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const path=require('node:path');
const {createCanvas}=require(process.env.CANVAS_MODULE||'@napi-rs/canvas');
global.document={createElement(){return createCanvas(1,1)}};
(async()=>{
 const root=path.resolve(__dirname,'../static');
 const {markCoverage}=await import(pathToFileURL(path.join(root,'scanner.js')));
 const {markdown}=await import(pathToFileURL(path.join(root,'richtext.js')));
 const c=createCanvas(50,50),ctx=c.getContext('2d'),identity=(x,y)=>({x,y});
 const test=(color,left)=>{ctx.fillStyle='#dddddd';ctx.fillRect(0,0,50,50);ctx.strokeStyle='#444';ctx.lineWidth=1;ctx.beginPath();ctx.arc(25,25,6,0,Math.PI*2);ctx.stroke();ctx.save();ctx.beginPath();ctx.arc(25,25,4.8,0,Math.PI*2);ctx.clip();ctx.fillStyle=color;ctx.fillRect(left,15,20,20);ctx.restore();return markCoverage(ctx.getImageData(0,0,50,50).data,50,50,identity,25,25,180);};
 assert(test('#dddddd',20)<.1,'unfilled outline is not a mark');
 assert(test('#777777',24)>.5,'off-centre grey fill covering more than half');
 assert(test('#2020a0',24)>.5,'coloured ink covering more than half');
 assert(test('#333333',28)<.5,'less than half remains unselected');
 const html=markdown('## Steps\n1. **Explain**\n2. `x = 2`\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n<script>alert(1)</script>\n[bad](javascript:alert(1))');
 assert(html.includes('<ol>'));assert(html.includes('<strong>Explain</strong>'));assert(html.includes('<table'));assert(!html.includes('<script>'));assert(!html.includes('<a '));
 console.log('PASS: half-area grey/colour/off-centre marks, empty outline, safe Markdown headings/lists/tables');
})().catch(e=>{console.error(e);process.exitCode=1;});
