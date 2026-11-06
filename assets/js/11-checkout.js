/* Наявні обробники форми, перенесені без змін. */
/* ---------- checkout modal (доставка лише по Рівному) ---------- */
const coOverlay = document.getElementById('coOverlay');
const coModal = document.getElementById('coModal');
const coForm = document.getElementById('coForm');
const coErr = document.getElementById('coErr');
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let coLastFocus = null;

function cartLines(){
  return Object.keys(cart).filter(id=>cart[id]>0).map(id=>{
    const p = PRODUCTS.find(x=>x.id==id);
    return p ? {p, qty:cart[id]} : null;
  }).filter(Boolean);
}
function openCheckout(){
  const lines = cartLines();
  if(!lines.length){ alert('Кошик порожній — додайте товари перед оформленням.'); return; }
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem('dymok_addr') || '{}'); } catch(e) {}
  $('coName').value  = saved.name  || (profile && profile.name)  || '';
  $('coPhone').value = saved.phone || (profile && profile.phone) || '';
  $('coTg').value    = saved.tg || '';
  $('coStreet').value= saved.street || '';
  $('coHouse').value = saved.house || '';
  $('coFlat').value  = saved.flat || '';
  $('coEntr').value  = saved.entr || '';
  $('coFloor').value = saved.floor || '';
  $('coNote').value = '';
  $('coAge').checked = false;
  coErr.textContent = '';
  coForm.querySelectorAll('.bad').forEach(e=>e.classList.remove('bad'));
  coModal.classList.remove('done');
  let total = 0;
  $('coItems').innerHTML = lines.map(({p,qty})=>{
    total += p.price*qty;
    const title = p.name + (p.spec ? ' — ' + p.spec : '');
    return `<div class="co-item"><span>${esc(title)} × ${qty}</span><span>${money(p.price*qty)}</span></div>`;
  }).join('');
  $('coTotal').textContent = money(total);
  closeCart();
  coLastFocus = document.activeElement;
  coOverlay.classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(()=>$('coName').focus(), 50);
}
function closeCheckout(){
  coOverlay.classList.remove('open');
  document.body.style.overflow = '';
  if(coLastFocus && coLastFocus.focus) coLastFocus.focus();
}
$('checkoutBtn').onclick = openCheckout;
$('coClose').onclick = closeCheckout;
$('coDoneClose').onclick = closeCheckout;
coOverlay.addEventListener('mousedown', e=>{ if(e.target===coOverlay) closeCheckout(); });
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && coOverlay.classList.contains('open')) closeCheckout(); });
coForm.querySelectorAll('input,select,textarea').forEach(el=>el.addEventListener('input', ()=>el.classList.remove('bad')));

coForm.addEventListener('submit', e=>{
  e.preventDefault();
  const v = id => $(id).value.trim();
  const bad = [];
  if(!v('coName')) bad.push('coName');
  const digits = v('coPhone').replace(/\D/g,'');
  if(digits.length < 10) bad.push('coPhone');
  if(!v('coStreet')) bad.push('coStreet');
  if(!v('coHouse')) bad.push('coHouse');
  coForm.querySelectorAll('.bad').forEach(x=>x.classList.remove('bad'));
  if(bad.length){
    bad.forEach(id=>$(id).classList.add('bad'));
    coErr.textContent = 'Заповніть обов\'язкові поля (імʼя, телефон, вулиця, будинок).';
    $(bad[0]).focus();
    return;
  }
  if(!$('coAge').checked){
    coErr.textContent = 'Підтвердіть вік 18+ та що доставка потрібна в межах м. Рівне.';
    return;
  }
  coErr.textContent = '';

  const lines = cartLines();
  if(!lines.length){ closeCheckout(); return; }
  const pay = (coForm.querySelector('input[name="coPay"]:checked')||{}).value || '';
  let tg = v('coTg'); if(tg && !tg.startsWith('@')) tg = '@' + tg.replace(/^https?:\/\/t\.me\//,'');
  const addr = `м. Рівне, ${v('coStreet')}, буд. ${v('coHouse')}`
    + (v('coFlat') ? `, кв./офіс ${v('coFlat')}` : '')
    + (v('coEntr') ? `, під'їзд ${v('coEntr')}` : '')
    + (v('coFloor') ? `, поверх/домофон ${v('coFloor')}` : '');

  let text = 'Вітаю! Хочу оформити замовлення з сайту Dymok.rv:\n\n🛒 Товари:\n';
  let total = 0; const snapshot = [];
  lines.forEach(({p,qty})=>{
    const title = p.name + (p.spec ? ' — ' + p.spec : '');
    text += `— ${title} ×${qty} = ${money(p.price*qty)}\n`;
    total += p.price*qty;
    snapshot.push({name:title, qty, price:p.price});
  });
  text += `\n💰 Разом: ${money(total)} (без доставки)\n\n`
    + `👤 Ім'я: ${v('coName')}\n📞 Телефон: ${v('coPhone')}\n`
    + (tg ? `✈️ Telegram: ${tg}\n` : '')
    + `📍 Адреса доставки: ${addr}\n`
    + `🕒 Зручний час: ${$('coTime').value}\n`
    + `💳 Оплата: ${pay}\n`
    + (v('coNote') ? `💬 Коментар: ${v('coNote')}\n` : '')
    + `\nПрошу підтвердити наявність і повідомити точний час доставки.`;

  try { localStorage.setItem('dymok_addr', JSON.stringify({name:v('coName'),phone:v('coPhone'),tg:v('coTg'),street:v('coStreet'),house:v('coHouse'),flat:v('coFlat'),entr:v('coEntr'),floor:v('coFloor')})); } catch(err) {}
  navigator.clipboard?.writeText(text).catch(()=>{});
  orders.unshift({date:new Date().toLocaleDateString('uk-UA'), items:snapshot, total, address:addr, wishTime:$('coTime').value, pay});
  saveOrders();
  cart = {}; saveCart(); renderCart();

  const link = 'https://t.me/DymokManager?text=' + encodeURIComponent(text);
  $('coTgLink').href = link;
  coModal.classList.add('done');
  window.open(link, '_blank');
});

