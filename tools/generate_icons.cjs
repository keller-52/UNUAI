// Precise vector-based app mark, rasterized for Apple's required icon dimensions.
const {createCanvas}=require('@napi-rs/canvas'),fs=require('node:fs');
const folder='mobile/ios/Assets.xcassets/AppIcon.appiconset';fs.mkdirSync(folder,{recursive:true});
const canvas=createCanvas(1024,1024),c=canvas.getContext('2d');
c.fillStyle='#245e49';c.fillRect(0,0,1024,1024);
c.fillStyle='#d9e9b0';c.beginPath();c.moveTo(265,210);c.lineTo(600,210);c.lineTo(765,375);c.lineTo(765,815);c.lineTo(265,815);c.closePath();c.fill();
c.fillStyle='#fffdf4';c.beginPath();c.moveTo(600,210);c.lineTo(600,375);c.lineTo(765,375);c.closePath();c.fill();
c.fillStyle='#245e49';c.fillRect(380,455,260,48);c.fillRect(380,565,205,48);c.fillRect(380,675,150,48);
fs.writeFileSync(folder+'/icon.png',canvas.toBuffer('image/png'));
fs.writeFileSync(folder+'/Contents.json',JSON.stringify({images:[{filename:'icon.png',idiom:'universal',platform:'ios',size:'1024x1024'}],info:{author:'xcode',version:1}},null,2));
fs.writeFileSync('mobile/ios/Assets.xcassets/Contents.json',JSON.stringify({info:{author:'xcode',version:1}}));
