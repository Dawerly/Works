/* Checkout is successful only after a durable server-side order is created. */
const coOverlay=document.getElementById('coOverlay'),coModal=document.getElementById('coModal'),coForm=document.getElementById('coForm'),coErr=document.getElementById('coErr');
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let coLastFocus=null,coDelivery=null,coSubmitting=false,coOpening=0;
function cartLines(){return Object.keys(cart).filter(id=>cart[id]>0).map(id=>{const p=PRODUCTS.find(x=>x.id==id);return p?{p,qty:cart[id]}:null;}).filter(Boolean);}
function checkoutTotals(){
  const lines=cartLines(),subtotal=lines.reduce((n,{p,qty})=>n+centsOf(p)*qty,0);
  $('coItems').innerHTML=lines.map(({p,qty})=>`<div class="co-item"><span>${esc(p.name+(p.spec?' — '+p.spec:''))} × ${qty}</span><span>${money(centsOf(p)*qty/100)}</span></div>`).join('');
  const zone=coDelivery?.zones.find(z=>String(z.id)===$('coZone').value);
  const fee=zone?(zone.free_from_cents!=null&&subtotal>=zone.free_from_cents?0:zone.fee_cents):0;
  $('coSubtotal').textContent=money(subtotal/100);$('coFee').textContent=zone?money(fee/100):'Оберіть район';$('coTotal').textContent=money((subtotal+fee)/100);
  $('coDeliveryNote').textContent=zone?'Мінімальна покупка: '+money(zone.minimum_cents/100)+(zone.free_from_cents!=null?'. Безкоштовна доставка від '+money(zone.free_from_cents/100):'')+'. Адміністратор перевірить відповідність адреси району.':'Не вдалося завантажити райони доставки.';
  coForm.querySelector('.co-submit').disabled=!coDelivery?.accepting||!zone||subtotal<(zone?.minimum_cents||0)||!lines.length||coSubmitting;
}
async function openCheckout(){
  if(!cartLines().length){showToast('Кошик порожній');return;}
  try{await refreshCustomerSession(false);}catch(e){showToast('Не вдалося перевірити вхід. Спробуйте ще раз.');return;}
  if(!profile){customerCheckoutPending=true;closeCart();location.hash='cabinet';renderCabinet();return;}
  const opening=++coOpening;const saved={...profile.address,name:profile.name,phone:profile.phone,tg:profile.tg};
  for(const[k,id]of Object.entries({name:'coName',phone:'coPhone',tg:'coTg',street:'coStreet',house:'coHouse',flat:'coFlat',entr:'coEntr',floor:'coFloor'}))$(id).value=saved[k]||(profile&&profile[k])||'';
  $('coNote').value='';$('coAge').checked=false;coErr.textContent='';coDelivery=null;$('coZone').replaceChildren(new Option('Завантаження районів…',''));coForm.querySelectorAll('.bad').forEach(e=>e.classList.remove('bad'));coModal.classList.remove('done');
  coLastFocus=document.activeElement;closeCart();coOverlay.classList.add('open');document.body.style.overflow='hidden';checkoutTotals();setTimeout(()=>$('coName').focus(),50);
  try{const r=await fetch('/api/delivery/options',{cache:'no-store'});if(!r.ok)throw new Error();const d=await r.json();if(opening!==coOpening)return;coDelivery=d;$('coZone').replaceChildren(...d.zones.map(z=>new Option(z.name,String(z.id))));if(saved.zone_id&&d.zones.some(z=>String(z.id)===String(saved.zone_id)))$('coZone').value=String(saved.zone_id);checkoutTotals();if(!d.accepting)coErr.textContent='Приймання замовлень зараз закрите. Графік: '+(d.settings.hours_enabled?d.settings.opens+'–'+d.settings.closes+' (Київ). Перевірте також робочі дні.':'тимчасова пауза.');}
  catch(e){coErr.textContent='Не вдалося завантажити умови доставки. Перевірте зв’язок і відкрийте оформлення знову.';}
}
function closeCheckout(){if(coSubmitting)return;coOpening++;coOverlay.classList.remove('open');document.body.style.overflow='';coLastFocus?.focus();}
$('checkoutBtn').onclick=openCheckout;$('coClose').onclick=closeCheckout;$('coDoneClose').onclick=closeCheckout;$('coZone').onchange=checkoutTotals;
coOverlay.addEventListener('mousedown',e=>{if(e.target===coOverlay)closeCheckout();});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&coOverlay.classList.contains('open'))closeCheckout();});
coForm.querySelectorAll('input,select,textarea').forEach(el=>el.addEventListener('input',()=>el.classList.remove('bad')));
function checkoutKey(payload){let pending=null;const serialized=JSON.stringify(payload);try{pending=JSON.parse(sessionStorage.getItem('dymok_pending_order')||'null');}catch(e){}if(pending?.payload===serialized)return pending.key;const key=crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2)+Math.random().toString(36).slice(2);try{sessionStorage.setItem('dymok_pending_order',JSON.stringify({payload:serialized,key}));}catch(e){}return key;}
coForm.addEventListener('submit',async e=>{
  e.preventDefault();if(coSubmitting)return;const v=id=>$(id).value.trim(),digits=v('coPhone').replace(/\D/g,''),bad=[];
  if(!v('coName'))bad.push('coName');if(!/^\+?[\d\s()\-]{10,30}$/.test(v('coPhone'))||digits.length<10||digits.length>15)bad.push('coPhone');
  const tg=v('coTg').replace(/^@/,'');if(!/^[A-Za-z0-9][A-Za-z0-9_]{1,30}[A-Za-z0-9]$/.test(tg))bad.push('coTg');if(!v('coStreet'))bad.push('coStreet');if(!v('coHouse'))bad.push('coHouse');
  coForm.querySelectorAll('.bad').forEach(x=>x.classList.remove('bad'));if(bad.length){bad.forEach(id=>$(id).classList.add('bad'));coErr.textContent='Заповніть ім’я, телефон (10–15 цифр), Telegram-нік (3–32 символи), вулицю та будинок.';$(bad[0]).focus();return;}
  if(!$('coAge').checked){coErr.textContent='Підтвердіть вік 18+ і адресу в межах Рівного.';return;}if(!coDelivery?.accepting||!$('coZone').value){coErr.textContent='Оформлення зараз недоступне. Перевірте умови доставки.';return;}
  const lines=cartLines();if(!lines.length){coErr.textContent='Кошик порожній. Додайте товари перед оформленням.';return;}
  const pay=coForm.querySelector('input[name=coPay]:checked').value;
  const payload={name:v('coName'),phone:v('coPhone'),tg:'@'+tg,street:v('coStreet'),house:v('coHouse'),flat:v('coFlat'),entr:v('coEntr'),floor:v('coFloor'),wishTime:$('coTime').value,pay,note:v('coNote'),zone_id:Number($('coZone').value),age_confirmed:true,items:lines.map(({p,qty})=>({id:p.id,qty}))};
  payload.request_id=checkoutKey(payload);const submit=coForm.querySelector('.co-submit');coSubmitting=true;submit.disabled=true;submit.textContent='Оформлюємо…';coErr.textContent='';
  try{
    const res=await fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'dymok','X-CSRF-Token':(await D.request('/api/customer/session')).csrf_token},body:JSON.stringify(payload)});const srv=await res.json().catch(()=>({}));
    if(res.status!==201||!srv.id||!srv.tracking_token){if(res.status===401){coErr.textContent='Сеанс завершився. Увійдіть до акаунта знову. Кошик збережено.';}else if(res.status===409&&srv.items)handleShortage(srv.items);else coErr.textContent=srv.error||'Не вдалося зберегти замовлення. Спробуйте ще раз.';return;}
    try{sessionStorage.removeItem('dymok_pending_order');}catch(e){}
    cart={};saveCart();renderCart();applyStock(srv.stock);
    $('coTrackLink').href='/order/#id='+srv.id;$('coDoneTitle').textContent='Замовлення №'+srv.id+' прийнято!';$('coDoneTotal').textContent='До оплати: '+money(srv.total)+', з них доставка '+money(srv.delivery_fee_cents/100)+'.';coModal.classList.add('done');refreshCustomerSession().catch(()=>{});
  }catch(err){coErr.textContent='Немає відповіді сервера. Кошик збережено. Повторіть спробу — однаковий запит не створить друге замовлення.';}
  finally{coSubmitting=false;submit.textContent='Оформити замовлення';checkoutTotals();}
});
function handleShortage(items){const messages=[];for(const it of items){STOCK[it.id]=it.available;const p=PRODUCTS.find(x=>x.id==it.id);if(it.available<=0)delete cart[it.id];else cart[it.id]=Math.min(cart[it.id]||0,it.available);messages.push((p?.name||'Товар')+': доступно '+it.available+' шт.');}saveCart();renderCart();renderCatalog();checkoutTotals();coErr.textContent=messages.join(' ')+' Перевірте кошик і повторіть оформлення.';}
