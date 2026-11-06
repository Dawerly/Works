/* Стан застосунку та робота з localStorage. */
let cart = {}, profile = null, orders = [], editingProfile = false;
try { cart = JSON.parse(localStorage.getItem('dymok_cart') || '{}'); } catch(e) {}
try { profile = JSON.parse(localStorage.getItem('dymok_profile') || 'null'); } catch(e) {}
try { orders = JSON.parse(localStorage.getItem('dymok_orders') || '[]'); } catch(e) {}
let path = [], query = '', sortMode = 'default';

/* Залишки з сервера: id -> число. Немає запису або null — облік не ведеться (товар завжди доступний). */
let STOCK = {};
const LOW_STOCK = 5;
function stockLeft(id){ const q = STOCK[id]; return (q === undefined || q === null) ? Infinity : q; }
function canAddMore(id){ return stockLeft(id) - (cart[id] || 0); }

function saveCart(){ try{ localStorage.setItem('dymok_cart', JSON.stringify(cart)); }catch(e){} }
function saveProfile(){ try{ localStorage.setItem('dymok_profile', JSON.stringify(profile)); }catch(e){} }
function saveOrders(){ try{ localStorage.setItem('dymok_orders', JSON.stringify(orders)); }catch(e){} }


/* Підписи статусів замовлення для кабінету покупця */
const ORDER_STATUS = {
  new:'⏳ Менеджер скоро напише вам і повідомить час доставки',
  confirmed:'✅ Замовлення підтверджено',
  delivering:'🚚 Замовлення в дорозі',
  done:'🎉 Замовлення доставлено',
  cancelled:'✖ Замовлення скасовано'
};
