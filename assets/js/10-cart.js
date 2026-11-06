/* Наявні обробники бічної панелі та її відображення. */
/* ---------- cart ---------- */
function renderCart(){
  const items = Object.keys(cart).filter(id=>cart[id]>0);
  document.getElementById('cartCount').textContent = items.reduce((s,id)=>s+cart[id],0);
  const wrap = document.getElementById('drawerItems');
  wrap.innerHTML = '';
  let subtotal = 0;
  if(!items.length){ wrap.innerHTML = '<div class="empty">Кошик порожній.</div>'; }
  items.forEach(id=>{
    const p = PRODUCTS.find(x=>x.id==id);
    if(!p) return;
    subtotal += p.price * cart[id];
    const row = document.createElement('div');
    row.className = 'citem';
    row.innerHTML = `
      <div class="ci-thumb" style="background:radial-gradient(ellipse at 30% 20%, ${p.color}30, var(--bg-soft2) 70%)">${svgIcon(p)}</div>
      <div class="ci-info"><b>${p.name}</b><span>${money(p.price)} · ${p.brand}</span></div>
      <div class="qty">
        <button data-a="dec" data-id="${id}" aria-label="Менше">−</button>
        <span>${cart[id]}</span>
        <button data-a="inc" data-id="${id}" aria-label="Більше">+</button>
      </div>`;
    wrap.appendChild(row);
  });
  wrap.querySelectorAll('button').forEach(btn=>{
    btn.onclick = ()=>{
      const id = btn.dataset.id;
      if(btn.dataset.a==='inc'){
        if(canAddMore(id) <= 0){ showToast('Більше немає в наявності (' + stockLeft(id) + ' шт.)'); return; }
        cart[id] += 1;
      }
      else { cart[id] -= 1; if(cart[id]<=0) delete cart[id]; }
      saveCart(); renderCart();
    };
  });
  document.getElementById('subtotal').textContent = money(subtotal);
}
document.getElementById('search').addEventListener('input', e=>{ query = e.target.value.trim().toLowerCase(); renderCatalog(); });
document.getElementById('sort').addEventListener('change', e=>{ sortMode = e.target.value; renderCatalog(); });

const overlay = document.getElementById('overlay'), drawer = document.getElementById('drawer');
function openCart(){ overlay.classList.add('open'); drawer.classList.add('open'); }
function closeCart(){ overlay.classList.remove('open'); drawer.classList.remove('open'); }
document.getElementById('cartOpenBtn').onclick = openCart;
document.getElementById('closeDrawer').onclick = closeCart;
overlay.onclick = closeCart;

