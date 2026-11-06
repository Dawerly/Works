/* Перевірка віку: недоступний фон, утримання фокуса й повернення до вмісту. */
const ageGate = document.getElementById('ageGate');
let ageGateBackground = [];
let ageGatePreviousOverflow = '';

function openAgeGate(){
  ageGatePreviousOverflow = document.body.style.overflow;
  ageGateBackground = Array.from(document.body.children)
    .filter(el => el !== ageGate && !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(el.tagName))
    .map(el => ({ el, inert: el.inert }));
  ageGateBackground.forEach(({el}) => { el.inert = true; });
  ageGate.classList.add('open');
  ageGate.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  document.getElementById('ageYes').focus();
}

function closeAgeGate(){
  ageGate.classList.remove('open');
  ageGate.setAttribute('aria-hidden', 'true');
  ageGateBackground.forEach(({el, inert}) => { el.inert = inert; });
  ageGateBackground = [];
  document.body.style.overflow = ageGatePreviousOverflow;
  const target = document.querySelector('.page.active h1, .page.active h2')
    || document.getElementById('main-content');
  if(target){
    target.setAttribute('tabindex', '-1');
    target.focus({preventScroll:true});
  }
}

let ageConfirmed = false;
try { ageConfirmed = localStorage.getItem('dymok_age_ok') === '1'; } catch(e) {}
if(ageConfirmed) ageGate.setAttribute('aria-hidden', 'true');
else openAgeGate();

ageGate.addEventListener('keydown', e => {
  if(e.key !== 'Tab' || !ageGate.classList.contains('open')) return;
  const first = document.getElementById('ageYes');
  const last = document.getElementById('ageNo');
  if(e.shiftKey && document.activeElement === first){ e.preventDefault(); last.focus(); }
  else if(!e.shiftKey && document.activeElement === last){ e.preventDefault(); first.focus(); }
});
document.addEventListener('focusin', e => {
  if(ageGate.classList.contains('open') && !ageGate.contains(e.target)){
    document.getElementById('ageYes').focus();
  }
});
document.getElementById('ageYes').onclick = () => {
  try { localStorage.setItem('dymok_age_ok','1'); } catch(e) {}
  closeAgeGate();
};
document.getElementById('ageNo').onclick = () => {
  window.location.href = 'https://www.google.com/';
};
