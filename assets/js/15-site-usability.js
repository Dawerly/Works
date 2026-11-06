/* Загальна навігація та доступність. Незалежний від даних і функцій продажу. */
(() => {
  const main = document.getElementById('main-content');
  const header = document.getElementById('siteHeader');
  const back = document.getElementById('backToTop');
  const gateOpen = () => document.getElementById('ageGate').classList.contains('open');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function syncNavigation(moveFocus){
    const active = document.querySelector('.page.active');
    const name = active ? active.id.replace('page-', '') : 'home';
    document.querySelectorAll('.nav-links a[data-nav], .mobile-nav a[data-nav]').forEach(link => {
      const current = link.dataset.nav === name;
      link.classList.toggle('active', current);
      if(current) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if(moveFocus && !gateOpen()){
      const heading = active && active.querySelector('h1, h2');
      const target = heading || main;
      target.setAttribute('tabindex', '-1');
      target.focus({preventScroll:true});
    }
  }

  document.getElementById('skipLink').addEventListener('click', e => {
    e.preventDefault();
    if(gateOpen()) return;
    main.focus({preventScroll:true});
    main.scrollIntoView({block:'start', behavior:'instant'});
  });

  function measureHeader(){
    const height = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--site-header-height', height + 'px');
  }
  measureHeader();
  if('ResizeObserver' in window) new ResizeObserver(measureHeader).observe(header);
  else window.addEventListener('resize', measureHeader, {passive:true});

  let scrollPending = false;
  function updateBackButton(){
    back.hidden = window.scrollY < 600 || gateOpen();
    scrollPending = false;
  }
  window.addEventListener('scroll', () => {
    if(!scrollPending){ scrollPending = true; requestAnimationFrame(updateBackButton); }
  }, {passive:true});
  back.addEventListener('click', () => {
    main.focus({preventScroll:true});
    window.scrollTo({top:0, behavior:reducedMotion.matches ? 'instant' : 'smooth'});
  });
  window.addEventListener('hashchange', () => { syncNavigation(true); updateBackButton(); });
  syncNavigation(false);
  updateBackButton();
})();
