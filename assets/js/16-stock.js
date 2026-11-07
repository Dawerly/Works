/* Наявність товарів і статуси замовлень із сервера (server.py + data/dymok.db).
   Якщо сервера немає (сайт відкрито як файл) — усе працює як раніше, без обліку залишків. */
function applyStock(map){
  Object.keys(map || {}).forEach(id=>{ STOCK[id] = map[id]; });
  clampCart(); renderCatalog(); renderCart();
}

/* Не дозволяє тримати в кошику більше, ніж є на складі */
function clampCart(){
  let changed = false;
  Object.keys(cart).forEach(id=>{
    if(!PRODUCTS.some(p=>String(p.id)===String(id))){ delete cart[id]; changed = true; return; }
    const left = stockLeft(id);
    if(cart[id] > left){ changed = true; if(left <= 0) delete cart[id]; else cart[id] = left; }
  });
  if(changed){ saveCart(); }
  return changed;
}

let lastStockJson = '';
async function refreshStock(){
  try {
    const res = await fetch('/api/stock', {cache:'no-store'});
    if(!res.ok) return;
    const data = await res.json();
    const json = JSON.stringify(data.stock);
    if(json === lastStockJson) return;
    lastStockJson = json;
    STOCK = data.stock || {};
    const cut = clampCart();
    const busy = document.getElementById('pdOverlay').classList.contains('open') || document.getElementById('coOverlay').classList.contains('open');
    if(!busy) renderCatalog();
    renderCart();
    if(cut) showToast('Деякі товари в кошику закінчились — кількість оновлено');
  } catch(e){ /* сервера немає — ігноруємо */ }
}
refreshStock();
setInterval(()=>{ if(!document.hidden) refreshStock(); }, 60000);
document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) refreshStock(); });

/* Customer history and statuses are loaded from the authenticated server account. */
let statusRefreshedAt=0;
async function refreshOrderStatuses(force){
  if(!profile||customerEdit||(!force&&Date.now()-statusRefreshedAt<20000))return;
  statusRefreshedAt=Date.now();await loadCustomerOrders();
}
setInterval(()=>{if(!document.hidden&&location.hash==='#cabinet')refreshOrderStatuses();},30000);
