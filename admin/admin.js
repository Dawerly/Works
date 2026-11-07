/* Адмін-панель Dymok. Усі дані вставляються через textContent — без innerHTML, щоб текст клієнтів не міг виконати код. */
'use strict';

const app = document.getElementById('app');
const STATUS_LABEL = {new:'Нове', confirmed:'Підтверджене', ready:'Готове до доставки', assigned:'Прийняте кур’єром', problem:'Проблема з доставкою', delivering:'Доставляється', done:'Доставлено', cancelled:'Скасоване'};
const CAT_LABEL = {liquid:'Рідини', pod:'Под-системи', disposable:'Одноразки', access:'Комплектуючі'};
const LOW = 5;
const money = n => Number(n).toLocaleString('uk-UA') + ' ₴';
const fmtDate = ts => new Date(ts*1000).toLocaleString('uk-UA', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'});

function h(tag, attrs, ...kids){
  const el = document.createElement(tag);
  for(const [k,v] of Object.entries(attrs || {})){
    if(v === false || v == null) continue;
    if(k === 'class') el.className = v;
    else if(k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if(k in el && k !== 'list') el[k] = v;
    else el.setAttribute(k, v);
  }
  kids.flat().forEach(c => { if(c != null && c !== false) el.append(c.nodeType ? c : document.createTextNode(String(c))); });
  return el;
}

let toastTimer;
function toast(msg, bad){
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast show' + (bad ? ' bad' : '');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>t.classList.remove('show'), 2600);
}

async function api(path, body){
  const opt = body === undefined
    ? {credentials:'same-origin'}
    : {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-Requested-With':'dymok'}, body:JSON.stringify(body)};
  if(body !== undefined){ const sessionResponse = await fetch('/api/delivery/session', {credentials:'same-origin',cache:'no-store'}); const security = await sessionResponse.json(); opt.headers['X-CSRF-Token'] = security.csrf_token; }
  let res;
  try { res = await fetch('/api/admin/' + path, opt); }
  catch(e){ throw new Error('Немає звʼязку із сервером.'); }
  const data = await res.json().catch(()=>({}));
  if(res.status === 401 && path !== 'login'){ showLogin(); throw new Error('Сесія завершилась. Увійдіть знову.'); }
  if(!res.ok) throw new Error(data.error || 'Помилка ' + res.status);
  return data;
}

/* ───────── вхід ───────── */
function showLogin(msg){
  stopPolling();
  const err = h('div', {class:'err', role:'alert'}, msg || '');
  const user = h('input', {type:'text', autocomplete:'username', required:true, autocapitalize:'off', spellcheck:false});
  const pass = h('input', {type:'password', autocomplete:'current-password', required:true});
  const btn = h('button', {class:'btn block', type:'submit'}, 'Увійти');
  const form = h('form', {onsubmit: async e=>{
    e.preventDefault(); err.textContent = ''; btn.disabled = true;
    try { await api('login', {username:user.value.trim(), password:pass.value}); pass.value = ''; start(); }
    catch(ex){ err.textContent = ex.message; pass.value = ''; pass.focus(); }
    btn.disabled = false;
  }},
    h('h1', null, 'Dymok · Адмін'), h('p', null, 'Вхід лише для власника магазину.'),
    h('label', {class:'f'}, 'Логін', user), h('label', {class:'f'}, 'Пароль', pass), err, btn);
  app.replaceChildren(h('div', {class:'login'}, form));
  user.focus();
}

/* ───────── каркас ───────── */
let tab = 'stock', pollTimer = null, pendingNew = 0;
const state = {products:[], orders:[], filter:{q:'', cat:'', mode:''}, orderFilter:''};

async function start(){
  try { await api('me'); } catch(e){ return showLogin(); }
  await Promise.all([loadProducts(), loadOrders()]);
  render();
  stopPolling(); pollTimer = setInterval(pollOrders, 30000);
}
function stopPolling(){ clearInterval(pollTimer); pollTimer = null; }

async function loadProducts(){ state.products = (await api('products')).products;
  Object.keys(CAT_LABEL).forEach(k=>delete CAT_LABEL[k]);
  state.products.forEach(p=>{ CAT_LABEL[p.cat] = p.category_name || p.cat; });
}
async function loadOrders(){
  const q = state.orderFilter ? '?status=' + state.orderFilter : '';
  state.orders = (await api('orders' + q)).orders;
}
async function pollOrders(){
  if(document.hidden) return;
  try {
    const beforeJson = JSON.stringify(state.orders);
    const before = state.orders.filter(o=>o.status==='new').length;
    await loadOrders();
    const after = state.orders.filter(o=>o.status==='new').length;
    if(!state.orderFilter && after > before) toast('Нове замовлення!');
    const changed = beforeJson !== JSON.stringify(state.orders);
    // не перемальовуємо, якщо менеджер зараз щось вводить і ще не зберіг
    const editing = document.querySelector('.manage[data-dirty]');
    if(tab === 'orders' && changed && !editing) renderTab(); else updateBadge();
  } catch(e){}
}
function newCount(){ return state.orders.filter(o=>o.status==='new').length; }
function updateBadge(){
  const b = document.querySelector('[data-tab=orders] .badge');
  if(b){ b.textContent = newCount(); b.hidden = !newCount(); }
}

function render(){
  const mk = (id, label) => h('button', {class:'tab', role:'tab', 'data-tab':id, 'aria-selected':String(tab===id), onclick:()=>{ tab = id; render(); }},
    label, id==='orders' ? h('span', {class:'badge', hidden:!newCount()}, newCount()) : null);
  app.replaceChildren(h('div', {class:'wrap'},
    h('div', {class:'top'}, h('h1', null, 'Dymok · Адмін-панель'),
      h('a', {href:'/admin/catalog/', class:'btn ghost sm'}, 'Каталог і знижки'),
      h('a', {href:'/admin/delivery/', class:'btn ghost sm'}, 'Доставка та кур’єри'),
      h('a', {href:'/', class:'btn ghost sm', target:'_blank', rel:'noopener', style:'text-decoration:none'}, 'Відкрити сайт'),
      h('button', {class:'btn ghost sm', onclick: async ()=>{ try{ await api('logout', {}); }catch(e){} showLogin(); }}, 'Вийти')),
    h('div', {class:'tabs', role:'tablist'}, mk('stock','Склад'), mk('orders','Замовлення'), mk('security','Безпека')),
    h('div', {id:'tabBody'})));
  renderTab();
}
function renderTab(){
  const body = document.getElementById('tabBody');
  body.replaceChildren(tab==='stock' ? stockView() : tab==='orders' ? ordersView() : securityView());
}

/* ───────── склад ───────── */
function stockClass(q){ return q === null ? 'ok' : q === 0 ? 'out' : q <= LOW ? 'low' : 'ok'; }

function stockView(){
  const P = state.products, f = state.filter;
  const cnt = {all:P.length, out:P.filter(p=>p.qty===0).length, low:P.filter(p=>p.qty!==null && p.qty>0 && p.qty<=LOW).length, untracked:P.filter(p=>p.qty===null).length};
  const stat = (mode, label, n) => h('button', {class:'stat' + (f.mode===mode ? ' on':''), onclick:()=>{ f.mode = f.mode===mode ? '' : mode; renderTab(); }}, h('b', null, n), h('span', null, label));

  let list = P.filter(p =>
    (!f.cat || p.cat===f.cat) &&
    (!f.q || (p.brand+' '+p.name+' '+p.spec).toLowerCase().includes(f.q.toLowerCase())) &&
    (!f.mode || (f.mode==='out' && p.qty===0) || (f.mode==='low' && p.qty!==null && p.qty>0 && p.qty<=LOW) || (f.mode==='untracked' && p.qty===null)));

  const search = h('input', {type:'search', placeholder:'Пошук: бренд, назва, смак…', value:f.q, 'aria-label':'Пошук', oninput:e=>{
    f.q = e.target.value; const pos = e.target.selectionStart; renderTab(); const s = document.querySelector('.tools input[type=search]'); s.focus(); s.setSelectionRange(pos,pos); }});
  const cat = h('select', {'aria-label':'Категорія', onchange:e=>{ f.cat = e.target.value; renderTab(); }},
    h('option', {value:''}, 'Усі категорії'), ...Object.entries(CAT_LABEL).map(([k,v])=>h('option', {value:k, selected:f.cat===k}, v)));
  const bulkVal = h('input', {type:'number', min:0, max:100000, value:10, 'aria-label':'Кількість для всіх'});
  const bulk = h('div', {class:'bulk'}, 'Для всіх у списку (' + list.length + '):', bulkVal,
    h('button', {class:'btn ghost sm', onclick: async ()=>{
      const n = parseInt(bulkVal.value, 10);
      if(!(n >= 0) || !list.length) return;
      if(!confirm(`Встановити залишок ${n} шт. для ${list.length} товарів?`)) return;
      await saveStock(list.map(p=>({id:p.id, qty:n})));
    }}, 'Встановити'));

  const rows = list.map(p => {
    const input = h('input', {type:'number', min:0, max:100000, inputmode:'numeric', 'aria-label':'Залишок: '+p.name+' '+p.spec,
      value: p.qty === null ? '' : p.qty, placeholder:'∞'});
    const commit = async () => {
      const raw = input.value.trim();
      const val = raw === '' ? null : parseInt(raw, 10);
      if(val !== null && !(val >= 0)) { input.value = p.qty ?? ''; return; }
      if(val === p.qty) { input.classList.remove('dirty'); return; }
      await saveStock([{id:p.id, qty:val}], input);
    };
    input.addEventListener('input', ()=>input.classList.add('dirty'));
    input.addEventListener('change', commit);
    input.addEventListener('keydown', e=>{ if(e.key==='Enter') input.blur(); });
    const step = d => h('button', {type:'button', 'aria-label': d>0 ? 'Додати 1' : 'Забрати 1', onclick: async ()=>{
      const cur = p.qty === null ? 0 : p.qty;
      await saveStock([{id:p.id, qty:Math.max(0, cur + d)}], input);
    }}, d>0 ? '+' : '−');
    return h('tr', {class: p.qty===0 ? 'out' : (p.qty!==null && p.qty<=LOW ? 'low' : '')},
      h('td', null, h('div', {class:'n'}, p.name), h('div', {class:'s'}, p.spec)),
      h('td', null, h('span', {class:'pill ' + stockClass(p.qty)}, p.qty===null ? 'не облік.' : p.qty===0 ? 'немає' : p.qty<=LOW ? 'мало' : 'є')),
      h('td', null, p.brand), h('td', null, money(p.price)),
      h('td', null, h('span', {class:'qty'}, step(-1), input, step(1)),
        p.qty!==null ? h('button', {class:'untrack', type:'button', title:'Не вести облік цього товару (завжди доступний)', onclick:()=>saveStock([{id:p.id, qty:null}])}, 'без обліку') : null));
  });

  return h('div', null,
    h('div', {class:'stats'}, stat('', 'Усього товарів', cnt.all), stat('out', 'Немає в наявності', cnt.out), stat('low', 'Закінчується (≤'+LOW+')', cnt.low), stat('untracked', 'Без обліку', cnt.untracked)),
    h('div', {class:'tools'}, search, cat, bulk),
    list.length ? h('div', {class:'tablewrap'}, h('table', null,
      h('thead', null, h('tr', null, ...['Товар','Статус','Бренд','Ціна','Залишок, шт.'].map(t=>h('th', null, t)))),
      h('tbody', null, rows))) : h('div', {class:'empty'}, 'Нічого не знайдено.'));
}

async function saveStock(items, input){
  try {
    const r = await api('stock', {items});
    for(const [id, q] of Object.entries(r.stock)){ const p = state.products.find(x=>x.id===+id); if(p) p.qty = q; }
    if(items.length === 1 && input){
      input.value = r.stock[items[0].id] ?? ''; input.classList.remove('dirty'); input.classList.add('saved');
      const y = window.scrollY; renderTab(); window.scrollTo(0, y);
    } else renderTab();
    toast('Збережено');
  } catch(e){ toast(e.message, true); if(input){ const p = state.products.find(x=>x.id===items[0].id); input.value = p.qty ?? ''; } }
}

/* ───────── замовлення ───────── */
function ordersView(){
  const filt = h('select', {'aria-label':'Фільтр за статусом', onchange: async e=>{ state.orderFilter = e.target.value; await loadOrders(); renderTab(); }},
    h('option', {value:''}, 'Активні замовлення'), ...Object.entries(STATUS_LABEL).map(([k,v])=>h('option', {value:k, selected:state.orderFilter===k}, v + (k==='done'||k==='cancelled' ? ' (архів)' : '')),
    ), h('option', {value:'all', selected:state.orderFilter==='all'}, 'Усі, разом з архівом'));
  const refresh = h('button', {class:'btn ghost sm', onclick: async ()=>{ await loadOrders(); renderTab(); toast('Оновлено'); }}, 'Оновити');
  return h('div', null, h('div', {class:'tools'}, filt, refresh),
    state.orders.length ? h('div', {class:'orders'}, state.orders.map(orderCard)) : h('div', {class:'empty'}, 'Замовлень немає.'));
}

function orderCard(o){
  const sel = h('select', {'aria-label':'Статус'}, ...Object.entries(STATUS_LABEL).map(([k,v])=>h('option', {value:k, selected:o.status===k, disabled:o.status==='cancelled' && k!=='cancelled'}, v)));
  const when = h('input', {type:'text', maxLength:120, value:o.delivery_time||'', placeholder:'напр. Сьогодні 18:00–19:00'});
  const note = h('textarea', {rows:2, maxLength:500, placeholder:'Повідомлення клієнту (за бажанням)'}, o.manager_note||'');
  note.value = o.manager_note || '';
  const save = h('button', {class:'btn sm', onclick: async ()=>{
    if(sel.value==='done' && o.status!=='done' && o.pay==='Готівкою при отриманні' && !confirm('Підтверджуєте отримання кур’єром готівки '+money(o.total)+'?')) return;
    if(sel.value==='cancelled' && o.status!=='cancelled' && !confirm('Скасувати замовлення №'+o.id+'? Товари повернуться на склад.')) return;
    try {
      const r = await api('order', {id:o.id, version:o.version, status:sel.value, ...(sel.value==='done' && o.pay==='Готівкою при отриманні' ? {cash_received_cents:o.total_cents} : {}), delivery_time:when.value, manager_note:note.value});
      Object.assign(o, r.order);
      for(const [id,q] of Object.entries(r.stock)){ const p = state.products.find(x=>x.id===+id); if(p) p.qty = q; }
      const finished = (o.status === 'done' || o.status === 'cancelled');
      if(finished && !state.orderFilter){          // доставлене чи скасоване зникає зі списку активних
        state.orders = state.orders.filter(x=>x.id !== o.id);
        toast(o.status === 'done' ? 'Доставлено — замовлення прибрано зі списку' : 'Скасовано — товар повернено на склад, замовлення прибрано зі списку');
      } else toast('Замовлення збережено');
      renderTab(); updateBadge();
    } catch(e){ toast(e.message, true); }
  }}, 'Зберегти');
  const copy = h('button', {class:'btn ghost sm', onclick: async ()=>{
    const text = `Вітаю, ${o.name}! Ваше замовлення №${o.id} прийнято.` + (when.value ? ` Орієнтовний час доставки: ${when.value}.` : '') + (note.value ? ' ' + note.value : '') + ' Дякуємо, що обрали Dymok!';
    try { await navigator.clipboard.writeText(text); toast('Текст скопійовано — вставте в Telegram'); } catch(e){ prompt('Скопіюйте текст:', text); }
  }}, 'Копіювати повідомлення клієнту');
  const tg = (o.tg || '').replace(/^@/, '');
  return h('article', {class:'order ' + o.status},
    h('div', null,
      h('h3', null, '№' + o.id, h('span', {class:'st ' + o.status}, STATUS_LABEL[o.status])),
      h('div', {class:'meta'}, fmtDate(o.created)),
      h('div', {class:'info'},
        h('div', null, h('b', null, 'Клієнт: '), o.name),
        h('div', null, h('b', null, 'Телефон: '), h('a', {href:'tel:' + o.phone.replace(/[^\d+]/g,'')}, o.phone)),
        tg && /^[A-Za-z0-9_]{3,64}$/.test(tg) ? h('div', null, h('b', null, 'Telegram: '), h('a', {href:'https://t.me/'+tg, target:'_blank', rel:'noopener noreferrer'}, '@'+tg)) : (o.tg ? h('div', null, h('b', null, 'Telegram: '), o.tg) : null),
        h('div', null, h('b', null, 'Адреса: '), o.address),
        o.wish_time ? h('div', null, h('b', null, 'Бажаний час: '), o.wish_time) : null,
        h('div', null, h('b', null, 'Кур’єр: '), o.courier_name || 'Не призначений'),
        o.courier_note ? h('div', {class:'err'}, 'Проблема: '+o.courier_note) : null,
        h('div', null, h('b', null, 'Доставка: '), money((o.delivery_fee_cents||0)/100)),
        h('div', null, h('b', null, 'Оплата: '), o.pay || '—'),
        o.note ? h('div', null, h('b', null, 'Коментар: '), o.note) : null),
      h('ul', null, o.items.map(i=>h('li', null, `${i.name}${i.spec ? ' — ' + i.spec : ''} × ${i.qty} = ${money(i.price*i.qty)}`))),
      h('div', {class:'total'}, 'Разом: ' + money(o.total) + ' (з доставкою)')),
    h('div', {class:'manage', oninput:e=>e.currentTarget.setAttribute('data-dirty','1'), onchange:e=>e.currentTarget.setAttribute('data-dirty','1')},
      h('a', {href:'/admin/delivery/', class:'btn ghost sm'}, 'Призначення та керування доставкою'),
      h('label', {class:'f'}, 'Статус', sel),
      h('label', {class:'f'}, 'Час доставки для клієнта', when),
      h('label', {class:'f'}, 'Повідомлення', note),
      h('div', {class:'row'}, save, copy,
        (o.status === 'done' || o.status === 'cancelled') ? h('button', {class:'btn danger sm', onclick: async ()=>{
          if(!confirm('Приховати замовлення №' + o.id + ' в архів? Історія та облік грошей збережуться.')) return;
          try { await api('order-delete', {id:o.id}); state.orders = state.orders.filter(x=>x.id !== o.id); toast('Замовлення архівовано'); renderTab(); }
          catch(e){ toast(e.message, true); }
        }}, 'Приховати в архів') : null)));
}

/* ───────── безпека ───────── */
function securityView(){
  const cur = h('input', {type:'password', autocomplete:'current-password', required:true});
  const nw = h('input', {type:'password', autocomplete:'new-password', minLength:10, required:true});
  const nw2 = h('input', {type:'password', autocomplete:'new-password', minLength:10, required:true});
  const err = h('div', {class:'err', role:'alert'});
  return h('form', {class:'settings', onsubmit: async e=>{
    e.preventDefault(); err.textContent = '';
    if(nw.value !== nw2.value){ err.textContent = 'Нові паролі не збігаються.'; return; }
    try { await api('password', {current:cur.value, new:nw.value}); cur.value = nw.value = nw2.value = ''; toast('Пароль змінено'); }
    catch(ex){ err.textContent = ex.message; }
  }},
    h('h2', {style:'margin-bottom:12px;font-size:1.05rem'}, 'Зміна пароля'),
    h('label', {class:'f'}, 'Поточний пароль', cur), h('label', {class:'f'}, 'Новий пароль (від 10 символів)', nw),
    h('label', {class:'f'}, 'Повторіть новий пароль', nw2), err,
    h('button', {class:'btn', type:'submit'}, 'Змінити пароль'),
    h('p', {style:'color:var(--muted);font-size:.8rem;margin:14px 0 0'}, 'Забули пароль? На комп’ютері, де працює сервер, виконайте: python3 server.py --set-password'));
}

start();
