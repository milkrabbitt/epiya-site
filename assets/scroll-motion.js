/* Progressive presentation only: no scroll interception, storage or requests. */
(() => {
  'use strict';
  if (document.body.matches('.legal-page,.support-page,.utility-page,.error-page')
      || !('IntersectionObserver' in window) || !Element.prototype.animate) return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(pointer: fine)');
  const compact = matchMedia('(max-width:700px)');
  const connection = navigator.connection;
  const lowPower = () => !!connection?.saveData
    || (navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 4)
    || (navigator.deviceMemory > 0 && navigator.deviceMemory <= 2);
  const enabled = () => !reduced.matches && !lowPower();
  const depthEnabled = () => enabled() && fine.matches && !compact.matches && !document.hidden;
  const animations = new Map();
  const seen = new WeakSet();
  const pending = new Set();
  let alive = true, frame = 0, listening = false;

  // Deliberately select content fragments, not every section or whole card surface.
  // The first screen, founder biography, QR codes, forms and live Meow controls stay still.
  const selectors = [
    '.section-head', '.home-product-copy', '.home-futures-heading', '.home-futures .screen-display',
    '.product-copy', '.products-page .product-section > figure', '.services-preview .service-grid > article',
    '.opc-intro', '.opc-step', '.investment-note', '.contact-strip > div',
    '.about-page .feature-card', '.contact-page .feature-card', '.contact-card',
    '.business-card-copy', '.download-row > div:first-child > h2', '.investment-grid > div', '.investor-facts > div',
    '.svc-section-heading', '.svc-capability', '.svc-process-tabs', '.svc-contact > div',
    '.ps-distill-heading', '.character-card', '.split-content > div', '.research-index'
  ].join(',');
  const candidates = [...document.querySelectorAll(selectors)].filter(el =>
    !el.closest('.founder-grid,[data-meow-lab],.legal,.legacy-reading')
    && !el.querySelector('input,textarea,select')
  );
  // No nested entrance animations: the nearest selected ancestor already provides the cue.
  const selected = candidates.filter(el => !candidates.some(parent => parent !== el && parent.contains(el)));
  const initialHeight = window.innerHeight;
  const entranceObserver = new IntersectionObserver(entries => {
    if (!alive) return;
    const entering = [];
    for (const entry of entries) {
      const el = entry.target;
      if (!entry.isIntersecting) {
        animations.get(el)?.cancel();
        animations.delete(el);
        continue;
      }
      if (document.hidden || seen.has(el)) continue;
      pending.delete(el);
      seen.add(el);
      if (enabled() && !el.contains(document.activeElement)) entering.push(el);
      else entranceObserver.unobserve(el);
    }
    // A quick scroll must never queue a long succession of delayed text.
    entering.forEach((el, index) => {
      const small = compact.matches || !fine.matches;
      const animation = el.animate([
        { opacity: .78, translate: `0 ${small ? 7 : 14}px` },
        { opacity: 1, translate: '0 0' }
      ], {
        duration: small ? 440 : 720,
        delay: Math.min(index, 2) * (small ? 35 : 65),
        easing: 'cubic-bezier(.2,.7,.25,1)',
        fill: 'backwards'
      });
      animations.set(el, animation);
      const clean = () => {
        if (animations.get(el) === animation) animations.delete(el);
        entranceObserver.unobserve(el);
      };
      animation.onfinish = clean;
      animation.oncancel = clean;
    });
  }, { threshold: .06, rootMargin: '0px 0px -28px 0px' });
  for (const el of selected) {
    const box = el.getBoundingClientRect();
    if (box.top < initialHeight && box.bottom > 0) { continue; }
    pending.add(el);
    entranceObserver.observe(el);
  }

  const definitions = [
    { host: '.home-gallery .exhibition', layers: '.architecture img', amplitude: 6 },
    { host: '.ps-gallery', layers: '.ps-bay-backplate', amplitude: 9, sheen: true },
    { host: '.ps-memory-bench', layers: '.ps-chip', amplitude: 7, sheen: true },
    { host: '.svc-workbench', layers: '.svc-ai-core', amplitude: 6, sheen: true },
    { host: '.ix-intro-stage', layers: '.ix-envelope', amplitude: 7 }
  ];
  const scenes = [];
  for (const definition of definitions) {
    document.querySelectorAll(definition.host).forEach(host => {
      const layers = [...host.querySelectorAll(definition.layers)];
      host.classList.add('ep-scroll-surface');
      layers.forEach(layer => layer.classList.add('ep-scroll-depth'));
      if (definition.sheen) {
        const sheen = document.createElement('span');
        sheen.className = 'ep-scroll-sheen';
        sheen.setAttribute('aria-hidden', 'true');
        host.prepend(sheen);
      }
      scenes.push({ host, layers, amplitude: definition.amplitude, visible: false });
    });
  }
  const visible = new Set();
  const reset = scene => {
    scene.host.style.removeProperty('--ep-scroll-y');
    scene.host.style.removeProperty('--ep-scroll-light');
    scene.layers.forEach(layer => layer.style.removeProperty('--ep-scroll-y'));
  };
  const cancelFrame = () => { if (frame) cancelAnimationFrame(frame); frame = 0; };
  const update = () => {
    frame = 0;
    if (!alive || !depthEnabled()) return;
    const height = window.innerHeight;
    // Batch layout reads, then writes. No permanent animation loop or lerp tail.
    const measurements = [...visible].map(scene => {
      const box = scene.host.getBoundingClientRect();
      const progress = Math.max(-1, Math.min(1, ((height / 2) - (box.top + box.height / 2)) / ((height + box.height) / 2)));
      return { scene, progress };
    });
    measurements.forEach(({ scene, progress }) => {
      if (scene.host.contains(document.activeElement)) return reset(scene);
      const y = progress * scene.amplitude;
      scene.host.style.setProperty('--ep-scroll-y', y.toFixed(2) + 'px');
      scene.host.style.setProperty('--ep-scroll-light', (progress * 60).toFixed(2) + 'px');
      scene.layers.forEach((layer, index) => layer.style.setProperty('--ep-scroll-y', (y * (index % 2 ? -.65 : 1)).toFixed(2) + 'px'));
    });
  };
  const schedule = () => { if (alive && visible.size && depthEnabled() && !frame) frame = requestAnimationFrame(update); };
  const listen = () => {
    const next = alive && visible.size > 0 && depthEnabled();
    if (next === listening) return;
    listening = next;
    if (next) window.addEventListener('scroll', schedule, { passive: true });
    else { window.removeEventListener('scroll', schedule); cancelFrame(); }
  };
  const sceneObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const scene = scenes.find(item => item.host === entry.target);
      if (!scene) continue;
      scene.visible = entry.isIntersecting;
      if (scene.visible) visible.add(scene);
      else { visible.delete(scene); reset(scene); }
    }
    listen(); schedule();
  });
  scenes.forEach(scene => sceneObserver.observe(scene.host));
  const sync = () => {
    document.documentElement.dataset.scrollMotion = reduced.matches ? 'reduced' : lowPower() ? 'low-power' : depthEnabled() ? 'full' : 'gentle';
    if (!enabled() || document.hidden) {
      animations.forEach(animation => animation.cancel());
      animations.clear();
    }
    if (!depthEnabled()) scenes.forEach(reset);
    listen(); schedule();
    // Re-evaluate outstanding sections after a background tab becomes visible.
    if (!document.hidden) pending.forEach(el => { entranceObserver.unobserve(el); entranceObserver.observe(el); });
  };
  [reduced, fine, compact].forEach(query => query.addEventListener('change', sync));
  connection?.addEventListener?.('change', sync);
  document.addEventListener('visibilitychange', sync);
  document.addEventListener('focusin', event => {
    animations.forEach((animation, el) => {
      if (el.contains(event.target)) { animation.cancel(); animations.delete(el); }
    });
    scenes.forEach(scene => { if (scene.host.contains(event.target)) reset(scene); });
  });
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('pagehide', () => {
    alive = false;
    animations.forEach(animation => animation.cancel()); animations.clear();
    scenes.forEach(reset); listen(); cancelFrame();
  });
  window.addEventListener('pageshow', () => { alive = true; sync(); });
  sync();
})();
