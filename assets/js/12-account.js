/* Особистий кабінет і збережений профіль. */
/* ---------- cabinet ---------- */
function renderCabinet(){
  const anon = document.getElementById('cabAnon'), inn = document.getElementById('cabIn');
  if(profile && !editingProfile){
    anon.style.display='none'; inn.style.display='block';
    document.getElementById('cabAvatar').textContent = (profile.name||'D')[0].toUpperCase();
    document.getElementById('cabName').textContent = profile.name;
    document.getElementById('cabPhone').textContent = profile.phone;
    document.getElementById('cabCity').textContent = profile.city ? ('📍 ' + profile.city) : '';
    const list = document.getElementById('ordersList');
    if(!orders.length){ list.innerHTML = '<div class="empty">Замовлень поки немає — оформіть перше в каталозі.</div>'; }
    else {
      list.innerHTML = orders.map(o=>`
        <div class="order-item">
          <div class="oh"><span>${o.date}</span><span>${money(o.total)}</span></div>
          <ul>${o.items.map(it=>`<li>${it.name} × ${it.qty}</li>`).join('')}</ul>
          ${o.address ? `<div class="order-addr">📍 ${esc(o.address)}${o.wishTime ? ' · 🕒 ' + esc(o.wishTime) : ''}</div><span class="order-status">⏳ Менеджер напише вам у Telegram і повідомить час доставки</span>` : ''}
        </div>`).join('');
    }
  } else {
    anon.style.display='block'; inn.style.display='none';
  }
}
document.getElementById('saveProfile').onclick = ()=>{
  const name = document.getElementById('cName').value.trim();
  const phone = document.getElementById('cPhone').value.trim();
  const city = document.getElementById('cCity').value.trim();
  if(!name || !phone){ alert('Вкажіть імʼя та телефон.'); return; }
  profile = {name, phone, city}; editingProfile = false; saveProfile(); renderCabinet();
};
document.getElementById('editProfile').onclick = ()=>{
  document.getElementById('cName').value = profile.name;
  document.getElementById('cPhone').value = profile.phone;
  document.getElementById('cCity').value = profile.city;
  editingProfile = true; renderCabinet();
};
document.getElementById('logoutProfile').onclick = ()=>{
  profile = null;
  orders = [];
  editingProfile = false;
  try {
    localStorage.removeItem('dymok_profile');
    localStorage.removeItem('dymok_orders');
  } catch(e) {}
  document.getElementById('cName').value = '';
  document.getElementById('cPhone').value = '';
  document.getElementById('cCity').value = '';
  renderCabinet();
};


