/* Стан застосунку та робота з localStorage. */
let cart = {}, profile = null, orders = [];
try { cart = JSON.parse(localStorage.getItem('dymok_cart') || '{}'); } catch(e) {}
let legacyReceipts=[];
try { legacyReceipts=JSON.parse(localStorage.getItem('dymok_orders')||'[]').filter(o=>o&&o.id&&o.trackingToken).map(o=>({id:o.id,trackingToken:o.trackingToken})); localStorage.setItem('dymok_orders',JSON.stringify(legacyReceipts)); localStorage.removeItem('dymok_profile');localStorage.removeItem('dymok_addr'); } catch(e) {}
let path = [], query = '', sortMode = 'default';

/* Залишки з сервера: id -> число. Немає запису або null — облік не ведеться (товар завжди доступний). */
let STOCK = {};
const LOW_STOCK = 5;
function stockLeft(id){ const q = STOCK[id]; return (q === undefined || q === null) ? Infinity : q; }
function canAddMore(id){ return stockLeft(id) - (cart[id] || 0); }

function saveCart(){ try{ localStorage.setItem('dymok_cart', JSON.stringify(cart)); }catch(e){} }


/* Підписи статусів замовлення для кабінету покупця */
const ORDER_STATUS = {
  new:'⏳ Замовлення прийнято, очікує підтвердження адміністратора',
  confirmed:'✅ Замовлення підтверджено',
  ready:'📦 Готове до доставки',
  assigned:'🧑‍🚀 Кур’єр прийняв доставку',
  problem:'⚠️ Уточнюємо доставку',
  delivering:'🚚 Замовлення в дорозі',
  done:'🎉 Замовлення доставлено',
  cancelled:'✖ Замовлення скасовано'
};
