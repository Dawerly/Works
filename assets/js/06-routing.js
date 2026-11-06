/* Перемикання сторінок за адресою та обробники навігації. */
/* ---------- routing ---------- */
function showPage(name){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  const el = document.getElementById('page-'+name);
  if(el) el.classList.add('active');
  document.querySelectorAll('#navLinks a').forEach(a=>a.classList.toggle('active', a.dataset.nav===name));
  window.scrollTo({top:0});
  if(name==='cabinet') renderCabinet();
}
function routeFromHash(){
  const raw = location.hash.replace('#','') || 'home';
  const [name, cat] = raw.split(':');
  if(cat){ path = [cat]; query = ''; const s = document.getElementById('search'); if(s) s.value = ''; renderCatalog(); }
  showPage(['home','catalog','cabinet'].includes(name) ? name : 'home');
}
window.addEventListener('hashchange', routeFromHash);
document.querySelectorAll('[data-nav]').forEach(el=>{
  el.addEventListener('click', e=>{ if(el.tagName==='A'){ /* let hash change fire */ } else { location.hash = el.dataset.nav; } });
});
document.querySelectorAll('[data-goto-cat]').forEach(el=>{
  el.addEventListener('click', ()=>{ location.hash = 'catalog:'+el.dataset.gotoCat; });
  el.addEventListener('keypress', e=>{ if(e.key==='Enter') location.hash = 'catalog:'+el.dataset.gotoCat; });
});

