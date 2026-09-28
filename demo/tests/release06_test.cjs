// Synthetic page-curl regression. Optional real-photo checks use local paths only.
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const path=require('node:path');
const {createCanvas,loadImage}=require(process.env.CANVAS_MODULE||'@napi-rs/canvas');
global.document={createElement:()=>createCanvas(1,1)};
(async()=>{
 const {guidanceWarnings}=await import(pathToFileURL(path.resolve(__dirname,'../static/workbook.js')));
 assert.deepEqual(guidanceWarnings({batch_size:10,batch_feedback:[{batch:1,guidance:'| Q12 wrong | Needs practice | Q2 |'},{batch:2,guidance:'| Q12 wrong | Needs practice | Q25 |'}]}),[{batch:1,questions:['Q12']}]);
 const paper=await import(pathToFileURL(path.resolve(__dirname,'../static/paper.js')));
 const scan=await import(pathToFileURL(path.resolve(__dirname,'../static/scanner.js')));
 const p={id:'SYNTHETIC',student_id:'TEST',round:1,version:1,sheet_code:'689634',config:{language:'en'},plan:{layout:'batch-v1',nodes:['Q9','Q10'].map(id=>({id,type:'choice_question'}))}};
 const expected=[{task_id:'Q9',order:null,first_answer:'A',hint_level:1,retry_answer:'B'},{task_id:'Q10',order:null,first_answer:'B',hint_level:1,retry_answer:'C'}];
 const img=await loadImage(Buffer.from(paper.recordSVG(p,expected))),base=createCanvas(paper.W,paper.H),ctx=base.getContext('2d');ctx.drawImage(img,0,0);
 const strip=createCanvas(640,22);strip.getContext('2d').drawImage(base,75,137,640,22,0,0,640,22);ctx.fillStyle='white';ctx.fillRect(75,137,640,30);ctx.drawImage(strip,75,143);
 const pts=scan.autoCorners(base);assert.deepEqual(scan.readSheet(base,pts,p).rows,expected);
 assert.throws(()=>scan.readSheet(base,pts,{...p,sheet_code:'123456'}),/expects/);
 // A physically corrupted bit must still fail its checksum, despite nearby-offset search.
 ctx.fillStyle='black';ctx.fillRect(80,147,12,14);assert.throws(()=>scan.readSheet(base,pts,p),/checksum|ambiguous/);
 for(const file of process.argv.slice(2)){
  const image=await loadImage(file),scale=Math.min(1,1800/Math.max(image.width,image.height));
  const c=createCanvas(Math.round(image.width*scale),Math.round(image.height*scale));c.getContext('2d').drawImage(image,0,0,c.width,c.height);
  const found=scan.readSheet(c,scan.autoCorners(c),p);assert.equal(found.code,'689634');assert.deepEqual(found.rows,expected);assert.deepEqual(found.issues,[]);
 }
 console.log('PASS: shifted code strip, wrong package, damaged checksum'+(process.argv.length>2?', supplied real photographs':''));
})().catch(e=>{console.error(e);process.exitCode=1;});
