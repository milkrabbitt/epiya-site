'use strict';
(() => {
 const $ = s => document.querySelector(s), all = s => [...document.querySelectorAll(s)];
 let toastTimer;
 function toast(message) { const el=$('.toast');if(!el)return;el.textContent=message;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3600); }
 async function copy(text){try{await navigator.clipboard.writeText(text);toast('已复制');}catch{toast('未能自动复制，请选中或长按文字复制。');}}
 all('[data-copy]').forEach(b=>b.addEventListener('click',()=>copy(b.dataset.copy)));
 $('.copy-result')?.addEventListener('click',()=>copy($('#meow-output').textContent));
 const menu=$('.menu-toggle'),nav=$('#mobile-nav');
 function closeMenu(){if(!menu||!nav)return;menu.setAttribute('aria-expanded','false');nav.hidden=true;}
 menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')==='true';menu.setAttribute('aria-expanded',String(!open));nav.hidden=open;});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){closeMenu();menu.focus();}});
 nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
 matchMedia('(min-width:601px)').addEventListener('change',closeMenu);
 all('[data-hero-tab]').forEach(button=>button.addEventListener('click',()=>{all('[data-hero-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));all('[data-hero-panel]').forEach(panel=>{panel.hidden=panel.dataset.heroPanel!==button.dataset.heroTab;});}));
 const samples=['本喵今天很翘尾巴，主人要一起玩嘛~','喵们去用餐叭呀 (ΦωΦ)','主人好喵~','本喵喜欢主人哼哼喵~ ₍^ >ヮ<^₎'];
 all('[data-sample]').forEach(b=>b.addEventListener('click',()=>{all('[data-sample]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));$('#meow-output').textContent=samples[Number(b.dataset.sample)];}));
 let themeSequence=0;
 all('[data-theme]').forEach(b=>b.addEventListener('click',()=>{const seq=++themeSequence,target=$('#theme-preview');target.setAttribute('aria-busy','true');const preview=new Image();preview.onload=()=>{if(seq!==themeSequence)return;target.src=preview.src;target.alt=b.textContent+'主题产品截图';target.closest('a').href=preview.src;target.closest('a').setAttribute('aria-label','查看大图：'+target.alt);target.removeAttribute('aria-busy');all('[data-theme]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));};preview.onerror=()=>{if(seq!==themeSequence)return;target.removeAttribute('aria-busy');toast('主题图片加载失败，请稍后再试。');};preview.src='/assets/meow-'+b.dataset.theme+'.webp';}));
 all('img').forEach(img=>img.addEventListener('error',()=>{img.removeAttribute('aria-busy');img.alt='图片暂未加载：'+img.alt;toast('部分图片未加载，请检查网络后重试。');},{once:true}));
 if(typeof HTMLDialogElement!=='undefined'){
  const dialog=document.createElement('dialog');dialog.className='lightbox';dialog.setAttribute('aria-label','图片大图');dialog.innerHTML='<button class="lightbox-close" autofocus>关闭 ×</button><figure><img alt=""><figcaption></figcaption></figure>';document.body.append(dialog);
  let trigger=null;const big=dialog.querySelector('img'),caption=dialog.querySelector('figcaption');
  const close=()=>dialog.close();dialog.querySelector('button').addEventListener('click',close);
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)close();}});
  dialog.addEventListener('close',()=>{document.body.style.overflow='';trigger?.focus();});
  all('[data-lightbox]').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();trigger=link;big.src=link.href;big.alt=link.querySelector('img')?.alt||link.dataset.caption||'图片大图';caption.textContent=link.dataset.caption||big.alt;dialog.showModal();document.body.style.overflow='hidden';}));
 }
 // Event-driven material response: no continuously running animation loop.
 const panel=$('.hero-product'),reduce=matchMedia('(prefers-reduced-motion:reduce)'),fine=matchMedia('(pointer:fine)');
 const constrained=()=>reduce.matches||!fine.matches||navigator.connection?.saveData||(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<=4);
 let visible=true,queued=0;
 function reset(){if(!panel)return;cancelAnimationFrame(queued);queued=0;panel.style.removeProperty('--move-x');panel.style.removeProperty('--move-y');panel.style.removeProperty('--light-x');panel.style.removeProperty('--light-y');}
 function sync(){document.body.classList.toggle('motion-enabled',!constrained());if(constrained()||document.hidden||!visible)reset();}
 if(panel){new IntersectionObserver(es=>{visible=es[0].isIntersecting;sync();}).observe(panel);panel.addEventListener('pointermove',e=>{if(constrained()||!visible||document.hidden||queued)return;const r=panel.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;queued=requestAnimationFrame(()=>{queued=0;panel.style.setProperty('--move-x',((x-.5)*3).toFixed(2)+'px');panel.style.setProperty('--move-y',((y-.5)*3).toFixed(2)+'px');panel.style.setProperty('--light-x',(x*100)+'%');panel.style.setProperty('--light-y',(y*100)+'%');});},{passive:true});panel.addEventListener('pointerleave',reset);document.addEventListener('visibilitychange',sync);reduce.addEventListener('change',sync);fine.addEventListener('change',sync);sync();}
})();
