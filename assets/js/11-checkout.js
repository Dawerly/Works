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
    total += centsOf(p)*qty;
    const title = p.name + (p.spec ? ' — ' + p.spec : '');
    return `<div class="co-item"><span>${esc(title)} × ${qty}</span><span>${money(centsOf(p)*qty/100)}</span></div>`;
  }).join('');
  $('coTotal').textContent = money(total / 100);
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

coForm.addEventListener('submit', async e=>{
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

  /* 1. Реєструємо замовлення на сервері: він перевіряє залишки й списує їх однією операцією. */
  const submitBtn = coForm.querySelector('.co-submit');
  submitBtn.disabled = true; submitBtn.textContent = 'Відправляємо…';
  let srv = null;      // відповідь сервера; null — сервера немає (сайт відкрито як файл)
  try {
    const res = await fetch('/api/order', {
      method:'POST', headers:{'Content-Type':'application/json','X-Requested-With':'dymok'},
      body: JSON.stringify({
        name:v('coName'), phone:v('coPhone'), tg, street:v('coStreet'), house:v('coHouse'),
        flat:v('coFlat'), entr:v('coEntr'), floor:v('coFloor'), wishTime:$('coTime').value, pay, note:v('coNote'),
        items: lines.map(({p,qty})=>({id:p.id, qty}))
      })
    });
    const data = await res.json().catch(()=>({}));
    if(res.status === 201) srv = data;
    else if(res.status === 409){
      submitBtn.disabled = false; submitBtn.textContent = 'Надіслати замовлення менеджеру';
      handleShortage(data.items || []);
      return;
    } else if(res.status === 404 || res.status === 405 || res.status === 501){
      srv = null;      // статичний хостинг без бази — працюємо як раніше, лише через Telegram
    } else {
      submitBtn.disabled = false; submitBtn.textContent = 'Надіслати замовлення менеджеру';
      coErr.textContent = data.error || 'Не вдалося оформити замовлення. Спробуйте ще раз.';
      return;
    }
  } catch(err){
    submitBtn.disabled = false; submitBtn.textContent = 'Надіслати замовлення менеджеру';
    coErr.textContent = 'Немає звʼязку із сервером. Перевірте інтернет і спробуйте ще раз.';
    return;
  }
  submitBtn.disabled = false; submitBtn.textContent = 'Надіслати замовлення менеджеру';

  /* 2. Текст для Telegram */
  const addr = srv ? srv.address
    : `м. Рівне, ${v('coStreet')}, буд. ${v('coHouse')}`
      + (v('coFlat') ? `, кв./офіс ${v('coFlat')}` : '')
      + (v('coEntr') ? `, під'їзд ${v('coEntr')}` : '')
      + (v('coFloor') ? `, поверх/домофон ${v('coFloor')}` : '');
  let text = 'Вітаю! Хочу оформити замовлення з сайту Dymok.rv'
    + (srv ? ` (№${srv.id})` : '') + ':\n\n🛒 Товари:\n';
  let total = 0; const snapshot = [];
  const confirmedLines = srv ? srv.items.map(item=>({p:item, qty:item.qty})) : lines;
  confirmedLines.forEach(({p,qty})=>{
    const title = p.name + (p.spec ? ' — ' + p.spec : '');
    text += `— ${title} ×${qty} = ${money(centsOf(p)*qty/100)}\n`;
    total += centsOf(p)*qty;
    snapshot.push({name:title, qty, price:p.price});
  });
  text += `\n💰 Разом: ${money(total / 100)} (без доставки)\n\n`
    + `👤 Ім'я: ${v('coName')}\n📞 Телефон: ${v('coPhone')}\n`
    + (tg ? `✈️ Telegram: ${tg}\n` : '')
    + `📍 Адреса доставки: ${addr}\n`
    + `🕒 Зручний час: ${$('coTime').value}\n`
    + `💳 Оплата: ${pay}\n`
    + (v('coNote') ? `💬 Коментар: ${v('coNote')}\n` : '')
    + `\nПрошу підтвердити наявність і повідомити точний час доставки.`;

  try { localStorage.setItem('dymok_addr', JSON.stringify({name:v('coName'),phone:v('coPhone'),tg:v('coTg'),street:v('coStreet'),house:v('coHouse'),flat:v('coFlat'),entr:v('coEntr'),floor:v('coFloor')})); } catch(err) {}
  navigator.clipboard?.writeText(text).catch(()=>{});
  orders.unshift({
    id: srv ? srv.id : null, phoneDigits: digits, status: srv ? 'new' : null,
    date:new Date().toLocaleDateString('uk-UA'), items:snapshot, total: srv ? srv.total : total / 100,
    address:addr, wishTime:$('coTime').value, pay
  });
  saveOrders();
  cart = {}; saveCart(); renderCart();
  if(srv){ applyStock(srv.stock); }

  const link = 'https://t.me/DymokManager?text=' + encodeURIComponent(text);
  $('coTgLink').href = link;
  coModal.classList.add('done');
  $('coDoneTitle').textContent = srv ? `Замовлення №${srv.id} прийнято!` : 'Майже готово!';
  window.open(link, '_blank');
});

/* Товару не вистачає: оновлюємо кошик за залишками й показуємо, що змінилось */
function handleShortage(items){
  const msgs = [];
  items.forEach(it=>{
    STOCK[it.id] = it.available;
    const p = PRODUCTS.find(x=>x.id==it.id);
    const name = p ? p.name + (p.spec ? ' — ' + p.spec : '') : 'Товар';
    if(it.available <= 0){ delete cart[it.id]; msgs.push(`«${name}» щойно закінчився — прибрали з кошика.`); }
    else { cart[it.id] = Math.min(cart[it.id] || 0, it.available); msgs.push(`«${name}»: залишилось лише ${it.available} шт. — змінили кількість.`); }
  });
  saveCart(); renderCart(); renderCatalog();
  const lines = cartLines();
  if(!lines.length){ closeCheckout(); showToast('Товарів із кошика вже немає в наявності'); return; }
  let total = 0;
  $('coItems').innerHTML = lines.map(({p,qty})=>{
    total += centsOf(p)*qty;
    return `<div class="co-item"><span>${esc(p.name + (p.spec ? ' — ' + p.spec : ''))} × ${qty}</span><span>${money(centsOf(p)*qty/100)}</span></div>`;
  }).join('');
  $('coTotal').textContent = money(total / 100);
  coErr.textContent = msgs.join(' ') + ' Перевірте замовлення й натисніть «Надіслати» ще раз.';
}
