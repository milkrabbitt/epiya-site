(() => {
  'use strict';
  if (!document.body.classList.contains('services-page')) return;
  const process = document.querySelector('[data-svc-process]');
  if (process) {
    const tabs = [...process.querySelectorAll('[data-svc-step]')];
    const panels = [...process.querySelectorAll('.svc-process-panel')];
    const list = process.querySelector('.svc-process-tabs');
    if (tabs.length === 4 && panels.length === tabs.length && list) {
      list.setAttribute('role', 'tablist');
      tabs.forEach(tab => tab.setAttribute('role', 'tab'));
      panels.forEach(panel => {
        panel.setAttribute('role', 'tabpanel');
        panel.tabIndex = 0;
      });
      const select = (index, moveFocus = false) => {
        tabs.forEach((tab, i) => {
          const active = i === index;
          tab.setAttribute('aria-selected', String(active));
          tab.tabIndex = active ? 0 : -1;
          panels[i].hidden = !active;
        });
        if (moveFocus) tabs[index].focus();
      };
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
      select(0);
    }
  }
  const bench = document.querySelector('[data-svc-light]');
  const fine = window.matchMedia('(hover: hover) and (pointer: fine)');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const constrained = (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2)
    || (navigator.deviceMemory && navigator.deviceMemory <= 2)
    || (navigator.connection && navigator.connection.saveData);
  if (bench && !constrained) {
    // No animation loop: the silver surface responds only while a pointer moves on it.
    bench.addEventListener('pointermove', event => {
      if (!fine.matches || reduced.matches || event.pointerType === 'touch') return;
      const bounds = bench.getBoundingClientRect();
      bench.style.setProperty('--svc-x', `${Math.max(0, Math.min(100, (event.clientX - bounds.left) / bounds.width * 100)).toFixed(1)}%`);
      bench.style.setProperty('--svc-y', `${Math.max(0, Math.min(100, (event.clientY - bounds.top) / bounds.height * 100)).toFixed(1)}%`);
    }, {passive: true});
    const reset = () => {
      bench.style.removeProperty('--svc-x');
      bench.style.removeProperty('--svc-y');
    };
    bench.addEventListener('pointerleave', reset);
    reduced.addEventListener?.('change', reset);
    fine.addEventListener?.('change', reset);
  }
})();
