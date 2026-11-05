/* EPIYA product scenes: presentation only; no storage, requests or live distillation. */
(() => {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const fine = window.matchMedia('(pointer: fine)');
  const constrained = () => reduce.matches || !fine.matches || !!navigator.connection?.saveData || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency < 4);
  document.querySelectorAll('[data-ps-distill]').forEach(root => {
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const panels = [...root.querySelectorAll('[role="tabpanel"]')];
    if (tabs.length !== panels.length || !tabs.length) return;
    let animation;
    function select(index, focus = false) {
      animation?.cancel();
      tabs.forEach((tab, i) => {
        const selected = i === index;
        tab.setAttribute('aria-selected', String(selected));
        tab.tabIndex = selected ? 0 : -1;
        panels[i].hidden = !selected;
      });
      if (focus) tabs[index].focus();
      if (!constrained() && !document.hidden && panels[index].animate) {
        animation = panels[index].animate([{ opacity: .55, transform: 'translateY(5px)' }, { opacity: 1, transform: 'none' }], { duration: 250, easing: 'cubic-bezier(.2,.7,.3,1)' });
      }
    }
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(index));
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault();
        select(next, true);
      });
    });
    root.dataset.ready = 'true';
    root.querySelector('[role="tablist"]').hidden = false;
    select(0);
    reduce.addEventListener('change', () => { if (reduce.matches) animation?.cancel(); });
    document.addEventListener('visibilitychange', () => { if (document.hidden) animation?.cancel(); });
    if ('IntersectionObserver' in window) new IntersectionObserver(entries => { if (!entries[0].isIntersecting) animation?.cancel(); }).observe(root);
  });
  const surfaces = [...document.querySelectorAll('.ps-reactive')];
  const states = surfaces.map(surface => {
    const state = { surface, frame: 0, visible: true };
    state.reset = () => {
      cancelAnimationFrame(state.frame); state.frame = 0;
      surface.style.removeProperty('--ps-light-x'); surface.style.removeProperty('--ps-light-y');
    };
    surface.addEventListener('pointermove', event => {
      if (constrained() || document.hidden || !state.visible || state.frame) return;
      const box = surface.getBoundingClientRect();
      const x = Math.max(0, Math.min(100, (event.clientX - box.left) / box.width * 100));
      const y = Math.max(0, Math.min(100, (event.clientY - box.top) / box.height * 100));
      state.frame = requestAnimationFrame(() => {
        state.frame = 0;
        if (constrained() || document.hidden || !state.visible) return state.reset();
        surface.style.setProperty('--ps-light-x', x.toFixed(1) + '%');
        surface.style.setProperty('--ps-light-y', y.toFixed(1) + '%');
      });
    }, { passive: true });
    surface.addEventListener('pointerleave', state.reset);
    return state;
  });
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      const state = states.find(item => item.surface === entry.target);
      if (!state) return;
      state.visible = entry.isIntersecting;
      if (!state.visible) state.reset();
    }));
    surfaces.forEach(surface => observer.observe(surface));
  }
  const resetConstrained = () => { if (constrained() || document.hidden) states.forEach(state => state.reset()); };
  reduce.addEventListener('change', resetConstrained);
  fine.addEventListener('change', resetConstrained);
  navigator.connection?.addEventListener?.('change', resetConstrained);
  document.addEventListener('visibilitychange', resetConstrained);
})();
