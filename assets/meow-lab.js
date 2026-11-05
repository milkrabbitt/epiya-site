'use strict';
(() => {
  const config = document.querySelector('#meow-theme-data');
  if (!config) return;
  let themes;
  try { themes = JSON.parse(config.textContent).themes; } catch { return; }
  const engine = window.EpiyaMeow;
  document.querySelectorAll('[data-meow-lab]').forEach(root => {
    const $ = s => root.querySelector(s), all = s => [...root.querySelectorAll(s)];
    const input = $('[data-lab-input]'), output = $('[data-lab-output]');
    if (!input || !output) return;
    const status = $('[data-lab-status]'), copy = $('[data-lab-copy]');
    const live = $('[data-live-panel]'), photo = $('[data-photo-panel]');
    const photoImage = $('[data-lab-photo]'), photoLink = photoImage.closest('a');
    const photoCaption = $('[data-photo-caption]'), retry = $('[data-photo-retry]');
    const skinButtons = all('[data-skin]'), viewButtons = all('[data-lab-view]');
    let theme, view = 'live', composing = false, photoSequence = 0, messageTimer;
    const available = !!(engine && engine.available && typeof engine.transform === 'function');
    const normalStatus = () => `${theme.name} · ${theme.release === 'development-preview' ? '开发版主题 · ' : ''}网页配色与喵化演示`;
    function message(text) {
      clearTimeout(messageTimer); status.textContent = text;
      messageTimer = setTimeout(() => { status.textContent = normalStatus(); }, 4200);
    }
    function update() {
      if (!available || composing) return;
      // Match the native textarea limit, without leaving a dangling surrogate.
      if (input.value.length > 120) input.value = input.value.slice(0,120).replace(/[\uD800-\uDBFF]$/, '');
      $('[data-lab-count]').textContent = `${input.value.length} / 120`;
      const text = input.value.trim() ? engine.transform(input.value, 'natural') : '';
      output.textContent = text || '输入一句话，看看它的猫咪语气。';
      output.dataset.empty = String(!text);
      output.removeAttribute('aria-busy');
      copy.disabled = !text;
      $('[data-lab-clear]').disabled = !input.value;
      all('[data-lab-mirror]').forEach(el => { el.textContent = text || '在上方输入框，试试你自己的句子。'; });
    }
    function loadPhoto(reload = false) {
      if (!theme.photo) return;
      const token = ++photoSequence, selected = theme;
      const img = new Image();
      photoImage.hidden = true;
      photoLink.hidden = true;
      retry.hidden = true;
      photoCaption.textContent = `正在加载${selected.name}的真实截图…`;
      photo.setAttribute('aria-busy', 'true');
      img.onload = () => {
        if (token !== photoSequence || selected !== theme) return;
        photoImage.src = img.src;
        photoImage.width = selected.photo.width; photoImage.height = selected.photo.height;
        photoImage.alt = selected.photo.caption;
        photoImage.hidden = false;
        photoLink.hidden = false;
        photoImage.closest('.lab-photo-window').classList.toggle('simulator-crop', !!selected.photo.crop);
        photoLink.href = selected.photo.src;
        photoLink.dataset.caption = selected.photo.caption.replace(' · 已裁去模拟器外框', ' · 完整原始截图');
        photoLink.setAttribute('aria-label', `查看${selected.name}完整真实截图`);
        photoCaption.textContent = selected.photo.caption;
        photo.removeAttribute('aria-busy');
      };
      img.onerror = () => {
        if (token !== photoSequence || selected !== theme) return;
        photoCaption.textContent = '截图暂未加载，请重试；也可以继续使用互动演示。';
        retry.hidden = false; retry.disabled = false;
        photo.removeAttribute('aria-busy');
      };
      img.src = selected.photo.src + (reload ? '?preview-retry=' + Date.now() : '');
    }
    function setView(next) {
      if (next === 'photo' && !theme.photo) return;
      view = next;
      live.hidden = view !== 'live'; photo.hidden = view !== 'photo';
      viewButtons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.labView === view)));
      if (view === 'photo') loadPhoto();
      else { photoSequence++; photo.removeAttribute('aria-busy'); }
    }
    function selectSkin(id) {
      const selected = themes.find(t => t.id === id);
      if (!selected) return;
      theme = selected; photoSequence++;
      root.dataset.theme = theme.id; root.dataset.skinDark = String(theme.dark);
      const p = theme.palette;
      const colors = {'bg':p.background,'key':p.key,'special':p.pressed,'ink':p.text,'muted':p.secondary,'accent':p.accent,'preview':p.key,'outline':p.line,'glow':p.accent};
      Object.entries(colors).forEach(([name,value]) => root.style.setProperty('--skin-'+name,value));
      all('[data-lab-cat]').forEach(img => {
        img.hidden = !theme.cat;
        if (theme.cat) img.src = theme.cat;
        else img.removeAttribute('src');
      });
      skinButtons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.skin === id)));
      if ($('[data-lab-select]')) $('[data-lab-select]').value = id;
      $('[data-lab-view="photo"]').disabled = !theme.photo;
      $('[data-photo-note]').hidden = !!theme.photo;
      $('[data-photo-note]').textContent = theme.photo ? '' : '这款暂未提供独立截图，当前可体验网页配色与喵化。';
      clearTimeout(messageTimer); status.textContent = normalStatus();
      if (!theme.photo && view === 'photo') setView('live');
      else if (view === 'photo') loadPhoto();
    }
    function arrows(buttons) {
      buttons.forEach((button,index) => button.addEventListener('keydown', e => {
        let next;
        if (e.key === 'ArrowRight') next = (index + 1) % buttons.length;
        if (e.key === 'ArrowLeft') next = (index + buttons.length - 1) % buttons.length;
        if (e.key === 'Home') next = 0;
        if (e.key === 'End') next = buttons.length - 1;
        if (next === undefined) return;
        e.preventDefault();
        if (!buttons[next].disabled) { buttons[next].focus(); buttons[next].click(); }
      }));
    }
    skinButtons.forEach(b => b.addEventListener('click', () => selectSkin(b.dataset.skin)));
    $('[data-lab-select]')?.addEventListener('change', e => selectSkin(e.target.value));
    viewButtons.forEach(b => b.addEventListener('click', () => setView(b.dataset.labView)));
    retry.addEventListener('click', () => { retry.disabled = true; loadPhoto(true); });
    arrows(skinButtons); arrows(viewButtons);
    input.addEventListener('compositionstart', () => { composing = true; output.setAttribute('aria-busy','true'); copy.disabled = true; });
    input.addEventListener('compositionend', () => { composing = false; update(); });
    input.addEventListener('input', e => { if (!e.isComposing) update(); });
    $('[data-lab-clear]').addEventListener('click', () => { input.value = ''; composing = false; update(); input.focus(); });
    all('[data-lab-sample]').forEach(b => b.addEventListener('click', () => {
      input.value = b.dataset.labSample; composing = false; setView('live'); update();
    }));
    copy.addEventListener('click', async () => {
      if (copy.disabled || composing) return;
      try { await navigator.clipboard.writeText(output.textContent); message('已复制喵化结果。'); }
      catch { message('未能自动复制，请长按或选中喵化结果复制。'); }
    });
    selectSkin(root.dataset.theme || 'strawberry');
    if (available) update();
    else {
      input.disabled = true; copy.disabled = true;
      $('[data-lab-clear]').disabled = true;
      all('[data-lab-sample]').forEach(b => { b.disabled = true; });
      output.textContent = '当前浏览器暂不支持此演示。请使用较新的浏览器，或切换到真实截图。';
    }
  });
})();
