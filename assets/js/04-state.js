/* Стан застосунку та робота з localStorage. */
let cart = {}, profile = null, orders = [], editingProfile = false;
try { cart = JSON.parse(localStorage.getItem('dymok_cart') || '{}'); } catch(e) {}
try { profile = JSON.parse(localStorage.getItem('dymok_profile') || 'null'); } catch(e) {}
try { orders = JSON.parse(localStorage.getItem('dymok_orders') || '[]'); } catch(e) {}
let path = [], query = '', sortMode = 'default';

function saveCart(){ try{ localStorage.setItem('dymok_cart', JSON.stringify(cart)); }catch(e){} }
function saveProfile(){ try{ localStorage.setItem('dymok_profile', JSON.stringify(profile)); }catch(e){} }
function saveOrders(){ try{ localStorage.setItem('dymok_orders', JSON.stringify(orders)); }catch(e){} }

