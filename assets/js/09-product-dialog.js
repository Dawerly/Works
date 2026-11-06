/* Наявні обробники вікна деталей. */
/* ---------- product window ---------- */
const pdOverlay = document.getElementById('pdOverlay');
let pdProduct = null, pdQty = 1, pdLastFocus = null;
function openProduct(id){
  const p = PRODUCTS.find(x=>x.id===id); if(!p) return;
  if(!pdOverlay.classList.contains('open')) pdLastFocus = document.activeElement;
  pdProduct = p; pdQty = 1;
  const imgBox = document.getElementById('pdImg');
  imgBox.style.background = `radial-gradient(ellipse at 50% 75%, ${p.color}33, transparent 55%), rgba(255,255,255,.02)`;
  imgBox.innerHTML = p.image
    ? `<img src="${esc2(p.image)}" alt="${esc2(p.name)}" onerror="this.outerHTML='<span class=&quot;pd-noimg&quot;>Фото товару недоступне</span>'">`
    : svgIcon(p);
  document.getElementById('pdTag').textContent = CATLABEL[p.cat];
  document.getElementById('pdName').textContent = p.name;
  document.getElementById('pdBrand').textContent = p.brand;
  document.getElementById('pdSpec').textContent = p.spec;
  document.getElementById('pdMeta').innerHTML = p.cat==='liquid' ? `<span>${p.vol} мл</span><span>${p.mg} мг</span>` : '';
  document.getElementById('pdPrice').textContent = money(p.price);
  // інші смаки / кольори тієї ж лінійки
  const sib = PRODUCTS.filter(x=>x.cat===p.cat && x.brand===p.brand && x.name===p.name && x.vol===p.vol && x.mg===p.mg);
  const vars = document.getElementById('pdVars');
  vars.innerHTML = sib.length>1
    ? `<div class="pd-vl">${p.cat==='pod' ? 'Колір / варіант' : 'Інші смаки цієї лінійки'}</div><div class="pd-chips">`
      + sib.map(x=>`<button type="button" class="pd-chip${x.id===p.id?' on':''}" data-id="${x.id}">${esc2(x.spec)}</button>`).join('') + '</div>'
    : '';
  vars.querySelectorAll('.pd-chip').forEach(b=>b.onclick = ()=>openProduct(+b.dataset.id));
  updatePd();
  pdOverlay.classList.add('open'); document.body.style.overflow = 'hidden';
  document.getElementById('pdAdd').focus();
}
function pdMax(){ return Math.min(20, Math.max(0, stockLeft(pdProduct.id))); }
function updatePd(){
  const max = pdMax(), add = document.getElementById('pdAdd');
  if(max === 0){
    document.getElementById('pdQty').textContent = 0;
    add.disabled = true; add.textContent = 'Немає в наявності';
  } else {
    if(pdQty > max) pdQty = max;
    document.getElementById('pdQty').textContent = pdQty;
    add.disabled = false; add.textContent = 'До кошика · ' + money(pdProduct.price * pdQty);
  }
  document.getElementById('pdPlus').disabled = pdQty >= max;
  const left = stockLeft(pdProduct.id);
  let el = document.getElementById('pdStock');
  if(!el){ el = document.createElement('div'); el.id = 'pdStock'; document.getElementById('pdPrice').after(el); }
  el.className = 'stock-badge ' + (left === 0 ? 'out' : left <= LOW_STOCK ? 'low' : 'hidden');
  el.textContent = left === 0 ? 'Немає в наявності' : left <= LOW_STOCK ? 'Залишилось ' + left + ' шт.' : '';
}
function closeProduct(){
  pdOverlay.classList.remove('open');
  if(!coOverlay.classList.contains('open')) document.body.style.overflow = '';
  if(pdLastFocus && pdLastFocus.focus) pdLastFocus.focus();
}
document.getElementById('pdClose').onclick = closeProduct;
pdOverlay.addEventListener('mousedown', e=>{ if(e.target===pdOverlay) closeProduct(); });
document.getElementById('pdMinus').onclick = ()=>{ if(pdQty>1){ pdQty--; updatePd(); } };
document.getElementById('pdPlus').onclick = ()=>{ if(pdQty < pdMax()){ pdQty++; updatePd(); } };
document.getElementById('pdAdd').onclick = ()=>{ if(addToCart(pdProduct.id, pdQty)) closeProduct(); };
document.addEventListener('keydown', e=>{ if(e.key==='Escape' && pdOverlay.classList.contains('open')) closeProduct(); });

