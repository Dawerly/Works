/* Наявні сповіщення та пов’язаний обробник. */
/* ---------- add to cart + toast ---------- */
let toastTimer = null;
function showToast(text){
  document.getElementById('toastText').textContent = text;
  const t = document.getElementById('toast'); t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 2600);
}
function addToCart(id, qty){
  const p = PRODUCTS.find(x=>x.id==id);
  const room = canAddMore(id);                       // скільки ще можна додати з урахуванням залишку
  if(room <= 0){
    showToast(stockLeft(id) === 0 ? 'Цього товару вже немає в наявності' : 'У кошику вже весь наявний залишок (' + stockLeft(id) + ' шт.)');
    return false;
  }
  const add = Math.min(qty, room);
  cart[id] = (cart[id]||0) + add; saveCart(); renderCart();
  if(p) showToast(add < qty ? `Додано лише ${add}: більше немає в наявності`
    : 'Додано: ' + p.name + (p.spec ? ' — ' + p.spec : '') + (qty>1 ? ' ×'+qty : ''));
  return true;
}
document.getElementById('toastCart').onclick = ()=>{ document.getElementById('toast').classList.remove('show'); openCart(); };

