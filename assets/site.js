'use strict';
(() => {
 const $ = s => document.querySelector(s);
 const all = s => [...document.querySelectorAll(s)];
 let toastTimer;
 function toast(message) {
  const el = $('.toast'); if (!el) return;
  el.textContent = message; el.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3600);
 }
 async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast('已复制'); }
  catch { toast('未能自动复制，请长按或选中页面上的文字复制。'); }
 }
 all('[data-copy]').forEach(b => b.addEventListener('click', () => copy(b.dataset.copy)));
 $('.copy-result')?.addEventListener('click', () => copy($('#meow-output').textContent));
 const menu = $('.menu-toggle'), nav = $('#mobile-nav');
 function closeMenu() { if (!menu) return; menu.setAttribute('aria-expanded','false'); nav.hidden = true; }
 menu?.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') === 'true';
  menu.setAttribute('aria-expanded',String(!open)); nav.hidden = open;
 });
 document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && menu?.getAttribute('aria-expanded') === 'true') { closeMenu(); menu.focus(); }
 });
 nav?.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
 window.matchMedia('(min-width:701px)').addEventListener('change', closeMenu);
 const samples = ['本喵今天很翘尾巴，主人要一起玩嘛~','喵们去用餐叭呀 (ΦωΦ)','主人好喵~','本喵喜欢主人哼哼喵~ ₍^ >ヮ<^₎'];
 all('[data-sample]').forEach(b => b.addEventListener('click', () => {
  all('[data-sample]').forEach(x => x.setAttribute('aria-pressed',String(x===b)));
  $('#meow-output').textContent = samples[Number(b.dataset.sample)];
 }));
 let themeSequence=0;
 all('[data-theme]').forEach(b => b.addEventListener('click', () => {
  const seq=++themeSequence, target=$('#theme-preview'); target.setAttribute('aria-busy','true');
  const image=new Image(); image.src='/assets/meow-'+b.dataset.theme+'.webp';
  image.onload=()=>{if(seq!==themeSequence)return;target.src=image.src;target.alt=b.textContent+'主题产品截图';target.removeAttribute('aria-busy');all('[data-theme]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));};
  image.onerror=()=>{if(seq!==themeSequence)return;target.removeAttribute('aria-busy');toast('主题图片加载失败，请稍后再试。');};
 }));
 all('img').forEach(img => img.addEventListener('error', () => {
  if (img.classList.contains('sculpture-fallback')) return;
  if (img === $('#theme-preview')) {
   img.removeAttribute('aria-busy');
   img.alt='主题图片暂未加载，请选择任一主题重试';
   toast('主题图片暂未加载，请选择任一主题重试。');
   return;
  }
  const text=document.createElement('span'); text.className='image-error'; text.textContent='图片暂未加载 · '+img.alt;
  img.replaceWith(text);
 },{once:true}));
 const canvas=$('#fiber-canvas'); if (!canvas) return;
 const ctx=canvas.getContext('2d',{alpha:true}); if(!ctx)return;
 const sculpture=$('.sculpture'), reduce=matchMedia('(prefers-reduced-motion:reduce)'), coarse=matchMedia('(pointer:coarse)');
 const connection=navigator.connection;
 const constrained=()=>coarse.matches || (navigator.hardwareConcurrency && navigator.hardwareConcurrency<=4) || connection?.saveData;
 const motion=$('#motion-toggle');
 let paused=reduce.matches||constrained(), visible=true, handle=0, last=0, phase=0, px=0,py=0,tx=0,ty=0, width=1,height=1, detail=constrained()?2:1, slow=0;
 const fibers=[];
 for(let i=0;i<84;i++){
  const a=i/84*Math.PI*2, points=[];
  for(let j=0;j<=170;j++){
   const t=j/170*Math.PI*2, r=1.3+.42*Math.cos(3*t);
   const tube=.19*Math.cos(a), rise=.19*Math.sin(a);
   points.push([(r+tube)*Math.cos(2*t),(r+tube)*Math.sin(2*t),.6*Math.sin(3*t)+rise]);
  }
  fibers.push(points);
 }
 function render(){
  const start=performance.now();
  ctx.clearRect(0,0,width,height);
  const scale=Math.min(width,height)*.225;
  const rx=-.65+py*.16, ry=.28+px*.18, rz=-.45+Math.sin(phase)*.05;
  const sx=Math.sin(rx),cx=Math.cos(rx),sy=Math.sin(ry),cy=Math.cos(ry),sz=Math.sin(rz),cz=Math.cos(rz);
  for(let f=0;f<fibers.length;f+=detail){
   const hue= f<29 ? 72 : f<56 ? 48 : 95;
   ctx.beginPath();
   for(let j=0;j<fibers[f].length;j++){
    const [x,y,z]=fibers[f][j];
    const y1=y*cx-z*sx,z1=y*sx+z*cx,x2=x*cy+z1*sy,z2=-x*sy+z1*cy;
    const x3=x2*cz-y1*sz,y3=x2*sz+y1*cz;
    const perspective=4.6/(4.6-z2);
    const xx=width*.5+x3*scale*perspective,yy=height*.5+y3*scale*perspective;
    j?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy);
   }
   ctx.strokeStyle='hsla('+hue+',38%,'+(54+f%9*3)+'%,'+(.25+(f%6)*.07)+')';
   ctx.lineWidth=.65;ctx.stroke();
  }
  sculpture.classList.add('ready');
  const renderMs=performance.now()-start;
  canvas.dataset.renderMs=renderMs.toFixed(2);
  if(renderMs>19 && ++slow>8)detail=2;
 }
 function frame(t){
  handle=0;
  if(paused||!visible||document.hidden)return;
  if(t-last>32){last=t;phase+=.009;px+=(tx-px)*.05;py+=(ty-py)*.05;render();}
  handle=requestAnimationFrame(frame);
 }
 function sync(){
  cancelAnimationFrame(handle);handle=0;
  motion.textContent=paused?'开启动效':'暂停动态';motion.setAttribute('aria-pressed',String(paused));
  canvas.dataset.motion=paused?'paused':'running';
  canvas.dataset.frameState=(!paused&&visible&&!document.hidden)?'active':'suspended';
  if(!paused&&visible&&!document.hidden)handle=requestAnimationFrame(frame);
 }
 function resize(){
  const r=sculpture.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,1.5);
  width=r.width;height=r.height;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);render();sync();
 }
 new ResizeObserver(resize).observe(sculpture);
 new IntersectionObserver(es=>{visible=es[0].isIntersecting;sync();},{threshold:.05}).observe(sculpture);
 document.addEventListener('visibilitychange',sync);
 reduce.addEventListener('change',()=>{paused=reduce.matches||constrained();render();sync();});
 motion.addEventListener('click',()=>{paused=!paused;sync();});
 if(!coarse.matches)document.querySelector('.hero').addEventListener('pointermove',e=>{
  const r=sculpture.getBoundingClientRect();tx=(e.clientX-r.left)/r.width-.5;ty=(e.clientY-r.top)/r.height-.5;
 },{passive:true});
 sync();
})();
