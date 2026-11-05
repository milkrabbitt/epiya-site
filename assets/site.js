'use strict';
(() => {
 const $ = s => document.querySelector(s), all = s => [...document.querySelectorAll(s)];
 const reduce=matchMedia('(prefers-reduced-motion:reduce)'),fine=matchMedia('(pointer:fine)');
 const constrained=()=>reduce.matches||!fine.matches||navigator.connection?.saveData||(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<=4);
 const transitions=new Map();
 function enter(el,duration=360){if(!el||constrained()||document.hidden||typeof el.animate!=='function')return;transitions.get(el)?.cancel();const animation=el.animate([{opacity:.25,transform:'translateY(7px)'},{opacity:1,transform:'translateY(0)'}],{duration,easing:'cubic-bezier(.22,1,.36,1)'});transitions.set(el,animation);animation.onfinish=()=>transitions.delete(el);}
 let toastTimer;
 function toast(message){const el=$('.toast');if(!el)return;el.textContent=message;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),3800);}
 async function copy(text){try{await navigator.clipboard.writeText(text);toast('已复制');}catch{toast('未能自动复制，请选中或长按文字复制。');}}
 all('[data-copy]').forEach(b=>b.addEventListener('click',()=>copy(b.dataset.copy)));
 $('.copy-result')?.addEventListener('click',()=>copy($('#meow-output').textContent));
 const menu=$('.menu-toggle'),nav=$('#mobile-nav');
 function closeMenu(){if(!menu||!nav)return;nav.hidden=true;menu.setAttribute('aria-expanded','false');}
 menu?.addEventListener('click',()=>{if(!nav)return;const open=menu.getAttribute('aria-expanded')==='true';nav.hidden=open;menu.setAttribute('aria-expanded',String(!open));if(!open)enter(nav,220);});
 nav?.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){closeMenu();menu.focus();}});
 document.addEventListener('click',e=>{if(nav&&!nav.hidden&&!nav.contains(e.target)&&!menu.contains(e.target))closeMenu();});
 matchMedia('(min-width:601px)').addEventListener('change',closeMenu);
 function arrowGroup(buttons){buttons.forEach((button,index)=>button.addEventListener('keydown',e=>{let next;if(e.key==='ArrowRight')next=(index+1)%buttons.length;if(e.key==='ArrowLeft')next=(index+buttons.length-1)%buttons.length;if(e.key==='Home')next=0;if(e.key==='End')next=buttons.length-1;if(next===undefined)return;e.preventDefault();buttons[next].focus();buttons[next].click();}));}
 const gallery=$('.exhibition'),productButtons=all('[data-product-button]');
 productButtons.forEach((button,index)=>button.addEventListener('click',()=>{if(!gallery)return;const key=button.dataset.productButton;if(gallery.dataset.product===key)return;gallery.dataset.product=key;productButtons.forEach(b=>b.setAttribute('aria-pressed',String(b===button)));all('[data-panel]').forEach(panel=>{transitions.get(panel)?.cancel();panel.hidden=panel.dataset.panel!==key;if(!panel.hidden)enter(panel,440);});const number=$('.exhibit-number');if(number)number.textContent=String(index+1).padStart(2,'0');}));
 arrowGroup(productButtons);
 const samples=['本喵今天很翘尾巴，主人要一起玩嘛~','喵们去用餐叭呀 (ΦωΦ)','主人好喵~','本喵喜欢主人哼哼喵~ ₍^ >ヮ<^₎'];
 all('button[data-sample]').forEach(button=>button.addEventListener('click',()=>{const output=$('#meow-output');if(!output)return;all('button[data-sample]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));output.textContent=samples[Number(button.dataset.sample)];enter(output,220);}));
 function themes(buttons,images,host,status,key){
  if(!buttons.length||!images.length)return;let sequence=0;
  buttons.forEach(button=>button.addEventListener('click',()=>{const token=++sequence,name=button.dataset[key],label=button.textContent.trim();images.forEach(img=>img.setAttribute('aria-busy','true'));if(status)status.textContent='正在加载'+label+'…';const image=new Image();
   image.onload=()=>{if(token!==sequence)return;images.forEach((img,index)=>{img.src=image.src;img.alt=label+(index?' · 真实键盘区域局部放大':' · 真实产品完整截图');img.removeAttribute('aria-busy');const a=img.closest('a');if(a){a.href=image.src;a.dataset.caption='喵喵键盘 · '+label+' · 当前 App Store 版本真实截图';a.setAttribute('aria-label','查看大图：'+img.alt);}});buttons.forEach(b=>b.setAttribute('aria-pressed',String(b===button)));if(host)host.dataset.theme=name;if(status)status.textContent=label+' · 当前 App Store 版本真实截图';images.forEach(img=>enter(img,240));};
   image.onerror=()=>{if(token!==sequence)return;images.forEach(img=>img.removeAttribute('aria-busy'));if(status)status.textContent='图片加载失败，已保留当前主题。点击主题可重试。';else toast('主题图片加载失败，已保留当前主题。请稍后重试。');};image.src='/assets/meow-'+name+'.webp';
  }));arrowGroup(buttons);
 }
 themes(all('button[data-theme-button]'),all('#theme-phone,#theme-keyboard'),$('#meow'),$('#theme-status'),'themeButton');
 themes(all('button[data-theme]'),all('#theme-preview'),$('.meow-showcase'),$('#theme-detail-status'),'theme');
 if(typeof HTMLDialogElement!=='undefined'){
  const dialog=document.createElement('dialog');dialog.className='lightbox';dialog.setAttribute('aria-label','图片大图');dialog.innerHTML='<button class="lightbox-close" autofocus>关闭 ×</button><figure><img alt=""><figcaption role="status"></figcaption><button class="lightbox-retry" hidden>重新加载图片</button></figure>';document.body.append(dialog);let trigger=null;
  const big=dialog.querySelector('img'),caption=dialog.querySelector('figcaption'),retry=dialog.querySelector('.lightbox-retry');
  big.addEventListener('error',()=>{caption.textContent='图片加载失败，可以重新加载或关闭后再试。';retry.hidden=false;retry.disabled=false;});big.addEventListener('load',()=>{caption.textContent=trigger?.dataset.caption||big.alt;retry.hidden=true;retry.disabled=false;});
  retry.addEventListener('click',()=>{if(!trigger)return;retry.disabled=true;caption.textContent='正在重新加载…';const url=new URL(trigger.href,location.href);url.searchParams.set('retry',String(Date.now()));big.src=url.href;});
  dialog.querySelector('.lightbox-close').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>{document.body.style.overflow='';trigger?.focus();});dialog.addEventListener('click',e=>{if(e.target!==dialog)return;const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();});
  all('[data-lightbox]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();trigger=a;big.src=a.href;big.alt=a.querySelector('img')?.alt||a.dataset.caption||'产品截图';caption.textContent=a.dataset.caption||big.alt;retry.hidden=true;retry.disabled=false;dialog.showModal();document.body.style.overflow='hidden';enter(dialog,180);}));
 }
 // Failed product images get a visible retry; no user data is submitted.
 all('img').filter(img=>!img.closest('dialog')).forEach(img=>{let fallback;
  img.addEventListener('error',()=>{if(img.closest('.architecture'))return;const figure=img.closest('figure');if(!figure){toast('部分图片未加载，请检查网络后刷新。');return;}if(fallback){fallback.hidden=false;fallback.querySelector('button').disabled=false;return;}fallback=document.createElement('div');fallback.className='media-fallback';fallback.setAttribute('role','status');fallback.innerHTML='<span>图片暂未加载</span><button>重试</button>';figure.append(fallback);fallback.querySelector('button').addEventListener('click',()=>{fallback.querySelector('button').disabled=true;const url=new URL(img.currentSrc||img.src,location.href);url.searchParams.set('retry',String(Date.now()));img.src=url.href;});});
  img.addEventListener('load',()=>{if(fallback)fallback.hidden=true;});
 });
 // Event-driven material response. Foreground screenshots remain front facing.
 const surfaces=all('.showroom,.product-showcase,.business-card,.wide-screen'),states=[];
 surfaces.forEach(surface=>{const state={surface,visible:true,queued:0};states.push(state);const reset=()=>{cancelAnimationFrame(state.queued);state.queued=0;['--scene-x','--scene-y','--light-x','--light-y','--glow-x','--glow-y'].forEach(n=>surface.style.removeProperty(n));};state.reset=reset;
  if('IntersectionObserver'in window)new IntersectionObserver(entries=>{state.visible=entries[0].isIntersecting;if(!state.visible){reset();transitions.forEach((animation,el)=>{if(surface.contains(el)){animation.cancel();transitions.delete(el);}});}}).observe(surface);
  surface.addEventListener('pointermove',e=>{if(constrained()||document.hidden||!state.visible||state.queued)return;const r=surface.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;state.queued=requestAnimationFrame(()=>{state.queued=0;if(constrained()||document.hidden||!state.visible){reset();return;}surface.style.setProperty('--glow-x',(x*100).toFixed(1)+'%');surface.style.setProperty('--glow-y',(y*100).toFixed(1)+'%');if(surface.classList.contains('showroom')){surface.style.setProperty('--scene-x',((x-.5)*4).toFixed(2)+'px');surface.style.setProperty('--scene-y',((y-.5)*3).toFixed(2)+'px');surface.style.setProperty('--light-x',(x*100).toFixed(1)+'%');surface.style.setProperty('--light-y',(y*100).toFixed(1)+'%');}});},{passive:true});surface.addEventListener('pointerleave',reset);
 });
 function syncMotion(){if(constrained()||document.hidden){states.forEach(s=>s.reset());transitions.forEach(a=>a.cancel());transitions.clear();}}
 reduce.addEventListener('change',syncMotion);fine.addEventListener('change',syncMotion);navigator.connection?.addEventListener?.('change',syncMotion);document.addEventListener('visibilitychange',syncMotion);syncMotion();
 // Investment and support links only set a contact context, never send a message.
 const contactContext=$('#contact-context');if(contactContext){const topic=new URLSearchParams(location.search).get('topic');const topics={investment:['投资交流','欢迎聊聊 EPIYA 的产品进展、后续方向与投资合作。'],business:['商务合作','可以先说明使用场景、希望解决的问题与项目范围。'],support:['产品支持','请说明产品、版本与操作步骤，并遮挡截图中的私人资料。']};if(Object.prototype.hasOwnProperty.call(topics,topic)){const [title,description]=topics[topic];contactContext.hidden=false;contactContext.textContent=description;$('#contact-heading').textContent=title;all('.contact-mail').forEach(a=>{a.href='mailto:contact@epiya.cn?subject='+encodeURIComponent('EPIYA · '+title);});}}
})();
