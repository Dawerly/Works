/* Оновлення товарів і категорій без перезавантаження сторінки. */
let liveCatalogJSON = '', liveCatalogBusy = false;
async function refreshCatalog(){
  if(location.protocol === 'file:' || liveCatalogBusy) return;
  const dialogOpen = ['pdOverlay','coOverlay'].some(id=>document.getElementById(id).classList.contains('open'));
  if(dialogOpen) return;
  liveCatalogBusy = true;
  try {
    const response = await fetch('/api/catalog', {cache:'no-store'});
    if(!response.ok) return;
    const data = await response.json(), signature = JSON.stringify(data);
    if(signature === liveCatalogJSON) return;
    liveCatalogJSON = signature;
    PRODUCTS.splice(0, PRODUCTS.length, ...data.products);
    CATS.splice(0, CATS.length, ...data.categories);
    Object.keys(CATLABEL).forEach(key=>delete CATLABEL[key]);
    CATS.forEach(c=>{ CATLABEL[c.id] = c.name; });
    if(path.length && path[0] !== 'all' && !CATS.some(c=>c.id===path[0])) path = [];
    const cut = clampCart();
    renderCatalog(); renderCart();
    document.getElementById('statCount').textContent = PRODUCTS.length;
    if(cut) showToast('Кошик оновлено: деякі товари більше недоступні');
  } catch(error) { /* Статичний перегляд зберігає початковий каталог. */ }
  finally { liveCatalogBusy = false; }
}
refreshCatalog();
setInterval(()=>{ if(!document.hidden) refreshCatalog(); }, 60000);
document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) refreshCatalog(); });
