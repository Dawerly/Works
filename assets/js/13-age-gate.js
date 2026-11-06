/* Перевірка віку та керування фокусом у її вікні. */
/* ---------- age gate ---------- */
const ageGate = document.getElementById('ageGate');
try {
  if(localStorage.getItem('dymok_age_ok') !== '1') ageGate.classList.add('open');
} catch(e) { ageGate.classList.add('open'); }
if(ageGate.classList.contains('open')) document.getElementById('ageYes').focus();
ageGate.addEventListener('keydown', e=>{
  if(e.key !== 'Tab') return;
  const first = document.getElementById('ageYes');
  const last = document.getElementById('ageNo');
  if(e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
  else if(!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
});
document.getElementById('ageYes').onclick = ()=>{
  try { localStorage.setItem('dymok_age_ok','1'); } catch(e) {}
  ageGate.classList.remove('open');
  const page = document.querySelector('.page.active');
  page.setAttribute('tabindex','-1');
  page.focus();
};
document.getElementById('ageNo').onclick = ()=>{
  window.location.href='https://www.google.com/';
};

