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

/* Статуси замовлень (час доставки від менеджера) */
let statusRefreshedAt = 0, statusBusy = false;
async function refreshOrderStatuses(force){
  if(statusBusy || (!force && Date.now() - statusRefreshedAt < 20000)) return;
  const active = orders.filter(o=>o.id && o.phoneDigits && o.status !== 'done' && o.status !== 'cancelled');
  if(!active.length) return;
  statusBusy = true; statusRefreshedAt = Date.now();
  let changed = false;
  await Promise.all(active.map(async o=>{
    try {
      const res = await fetch('/api/order-status?id=' + o.id + '&phone=' + encodeURIComponent(o.phoneDigits), {cache:'no-store'});
      if(!res.ok) return;
      const d = await res.json();
      if(d.status !== o.status || (d.delivery_time||'') !== (o.deliveryTime||'') || (d.manager_note||'') !== (o.managerNote||'')){
        o.status = d.status; o.deliveryTime = d.delivery_time; o.managerNote = d.manager_note; changed = true;
      }
    } catch(e){}
  }));
  statusBusy = false;
  if(changed){ saveOrders(); renderCabinet(); }
}

/* Якщо сторінку відкрито одразу на «Кабінеті», цей файл завантажується вже після першого показу кабінету */
if(location.hash.indexOf('#cabinet') === 0) refreshOrderStatuses();
