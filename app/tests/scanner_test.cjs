// Optional image-level integration tests, no browser required.
// npm install --no-save @napi-rs/canvas
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
const fs=require('node:fs');
const {spawnSync}=require('node:child_process');
const {createCanvas,loadImage}=require(process.env.CANVAS_MODULE||'@napi-rs/canvas');
global.document={createElement(name){assert.equal(name,'canvas');return createCanvas(1,1);}};
(async()=>{
 const dir=path.resolve(__dirname,'..');
 const paper=await import(pathToFileURL(path.join(dir,'static/paper.js')));
 const scan=await import(pathToFileURL(path.join(dir,'static/scanner.js')));
 const generated=spawnSync(process.env.PYTHON||'python',['-c',
  'import json;from core import *;s=state_for({"diagnostic":{}},[]);p=demo_proposal(s,[]);print(json.dumps({"id":"P-TEST","student_id":"S-SYNTHETIC","round":1,"version":1,"sheet_code":"4A92CF","mode":"demo","plan":compile_plan(p),"proposal":p,"audit":{"model":None},"compiler_version":VERSION}))'],{cwd:dir,encoding:'utf8'});
 assert.equal(generated.status,0,generated.stderr);const p=JSON.parse(generated.stdout);
 const expected=paper.sampleRows(p,'support'),svg=paper.recordSVG(p,expected);
 const image=await loadImage(Buffer.from(svg));const base=createCanvas(paper.W,paper.H);base.getContext('2d').drawImage(image,0,0);
 const corners=scan.autoCorners(base),found=scan.readSheet(base,corners,p);
 assert.deepEqual(found.rows,expected);assert.equal(found.issues.length,0);
 assert.throws(()=>scan.readSheet(base,corners,{...p,sheet_code:'000000'}),/expects/);
 const ambiguous=createCanvas(paper.W,paper.H),ac=ambiguous.getContext('2d');ac.drawImage(base,0,0);
 const extra=expected[0].first_answer==='A'?1:0;ac.fillStyle='black';ac.beginPath();ac.arc(paper.COLS.first_answer[extra],paper.rowY(0),6,0,Math.PI*2);ac.fill();
 const unsure=scan.readSheet(ambiguous,corners,p);assert.ok(unsure.issues.length);assert.equal(unsure.rows[0].first_answer,null);
 const emptyImage=await loadImage(Buffer.from(paper.recordSVG(p)));const empty=createCanvas(paper.W,paper.H);empty.getContext('2d').drawImage(emptyImage,0,0);
 assert.deepEqual(scan.readSheet(empty,scan.autoCorners(empty),p).rows,paper.blankRows(p));
 // Perspective camera fixture, with slightly grey paper and dark grey ink.
 const photo=createCanvas(1050,1400),pts=[{x:160,y:95},{x:955,y:190},{x:855,y:1270},{x:85,y:1180}];
 const map=scan.homography(pts),src=base.getContext('2d').getImageData(0,0,paper.W,paper.H);
 const dc=photo.getContext('2d'),im=dc.createImageData(photo.width,photo.height);im.data.fill(255);
 for(let y=0;y<paper.H;y+=.4)for(let x=0;x<paper.W;x+=.4){const q=map(x,y),xx=Math.round(q.x),yy=Math.round(q.y);if(xx<0||yy<0||xx>=photo.width||yy>=photo.height)continue;const si=(Math.floor(y)*paper.W+Math.floor(x))*4,di=(yy*photo.width+xx)*4;for(let k=0;k<3;k++)im.data[di+k]=30+Math.round(src.data[si+k]*.8);}
 dc.putImageData(im,0,0);const recovered=scan.readSheet(photo,pts,p);assert.deepEqual(recovered.rows,expected);
 const auto=scan.autoCorners(photo);assert.deepEqual(scan.readSheet(photo,auto,p).rows,expected);
 assert.throws(()=>paper.decodeBits(paper.sheetBits(p.sheet_code).slice(0,-1)+(paper.sheetBits(p.sheet_code).endsWith('1')?'0':'1')),/checksum/);
 assert.throws(()=>scan.homography([{x:0,y:0},{x:0,y:0},{x:0,y:0},{x:0,y:0}]),/degenerate/);
 const output=process.env.PAPER_TEST_OUTPUT;
 if(output){fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'record-filled.png'),base.toBuffer('image/png'));fs.writeFileSync(path.join(output,'record-perspective.png'),photo.toBuffer('image/png'));fs.writeFileSync(path.join(output,'record.svg'),paper.recordSVG(p));
  const css=fs.readFileSync(path.join(dir,'static/print.css'),'utf8');fs.writeFileSync(path.join(output,'booklet-preview.html'),`<!doctype html><html><head><style>${css}</style></head><body>${paper.bookletHTML(p)}</body></html>`);
 }
 console.log('PASS: blank / filled OMR, automatic markers, perspective correction, grey exposure, ambiguous marks, wrong sheet code, checksum and degenerate corners');
})().catch(e=>{console.error(e);process.exit(1);});
