/* Наявні сповіщення та пов’язаний обробник. */
/* ---------- add to cart + toast ---------- */
let toastTimer = null;
function showToast(text){
  document.getElementById('toastText').textContent = text;
  const t = document.getElementById('toast'); t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 2600);
}
function addToCart(id, qty){
  cart[id] = (cart[id]||0) + qty; saveCart(); renderCart();
  const p = PRODUCTS.find(x=>x.id==id);
  if(p) showToast('Додано: ' + p.name + (p.spec ? ' — ' + p.spec : '') + (qty>1 ? ' ×'+qty : ''));
}
document.getElementById('toastCart').onclick = ()=>{ document.getElementById('toast').classList.remove('show'); openCart(); };

