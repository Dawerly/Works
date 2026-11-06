/* Наявна логіка відображення каталогу та переходів між рівнями. */
/* ---------- catalog ---------- */
const plural = (n,a,b,c)=>{ const m=n%10, h=n%100; return (m===1&&h!==11)?a:(m>=2&&m<=4&&(h<10||h>=20))?b:c; };
const posWord = n => n+' '+plural(n,'позиція','позиції','позицій');
const fmtLevel = (k,v) => k==='vol' ? v+' мл' : k==='mg' ? v+' мг' : v;
const esc2 = s => String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function sortList(list){
  list = list.slice();
  if(sortMode==='price-asc') list.sort((a,b)=>a.price-b.price);
  if(sortMode==='price-desc') list.sort((a,b)=>b.price-a.price);
  if(sortMode==='name') list.sort((a,b)=>a.name.localeCompare(b.name,'uk'));
  return list;
}
function productCard(p){
  const meta = p.cat==='liquid' ? `<div class="meta"><span>${p.vol} мл</span><span>${p.mg} мг</span></div>` : '';
  return `<div class="card" data-pid="${p.id}" tabindex="0" role="button" aria-label="Відкрити: ${esc2(p.name+' '+p.spec)}">
    ${thumbHTML(p)}
    <span class="tag">${CATLABEL[p.cat]}</span>
    <div><h3>${esc2(p.name)}</h3><div class="brand">${esc2(p.brand)}</div></div>
    <div class="spec">${esc2(p.spec)}</div>${meta}
    <div class="row"><span class="price">${money(p.price)}</span><button class="add" data-id="${p.id}">До кошика</button></div>
  </div>`;
}
function productGrid(list, group){
  if(!list.length) return '<div class="empty">Нічого не знайдено.</div>';
  list = sortList(list);
  if(!group) return `<div class="grid">${list.map(productCard).join('')}</div>`;
  const groups = new Map();
  list.forEach(p=>{ if(!groups.has(p.name)) groups.set(p.name, []); groups.get(p.name).push(p); });
  return [...groups].map(([name,items])=>{
    const min = Math.min(...items.map(i=>i.price));
    return `<div class="grp"><h3>${esc2(name)}</h3><span>${posWord(items.length)} · від ${money(min)}</span></div>
      <div class="grid">${items.map(productCard).join('')}</div>`;
  }).join('');
}
function levelOptions(list, key){
  const map = new Map();
  list.forEach(p=>{
    const v = p[key];
    if(!map.has(v)) map.set(v, {value:v, items:[]});
    map.get(v).items.push(p);
  });
  let opts = [...map.values()];
  if(key==='vol' || key==='mg') opts.sort((a,b)=>a.value-b.value);
  return opts;
}
function tileHTML(attrs, big, title, sub, price, img, icon){
  const visual = img
    ? `<div class="lv-img"><img src="${esc2(img)}" alt="" loading="lazy" onerror="this.parentNode.style.display='none'"></div>`
    : (icon ? `<div class="lv-ico">${icon}</div>` : '');
  return `<button type="button" class="lv-tile" ${attrs}>
    ${visual}
    <div class="lv-main">${big ? `<b class="lv-big">${title}</b>` : `<b>${title}</b>`}<span>${sub}</span>${price ? `<em>від ${money(price)}</em>` : ''}</div>
    <i aria-hidden="true">→</i>
  </button>`;
}
function renderCrumbs(labels){
  const el = document.getElementById('crumbs');
  if(!labels.length){ el.innerHTML = ''; el.style.display='none'; return; }
  el.style.display='flex';
  const parts = [`<button type="button" class="crumb" data-depth="0">Каталог</button>`];
  labels.forEach((l,i)=>{
    const last = i===labels.length-1;
    parts.push('<span class="sep">›</span>');
    parts.push(last ? `<span class="crumb cur">${esc2(l)}</span>` : `<button type="button" class="crumb" data-depth="${i+1}">${esc2(l)}</button>`);
  });
  el.innerHTML = parts.join('');
  el.querySelectorAll('button.crumb').forEach(b=>b.onclick = ()=>{ goTo(path.slice(0, +b.dataset.depth), 'back'); });
}
function catTile(c){
  const items = PRODUCTS.filter(p=>p.cat===c.id);
  const min = Math.min(...items.map(i=>i.price));
  return `<button type="button" class="lv-tile lv-cat" data-cat="${c.id}">
    <div class="lv-ico">${c.icon}</div>
    <div class="lv-main"><b>${c.name}</b><span>${c.desc}</span><em>${posWord(items.length)} · від ${money(min)}</em></div>
    <i aria-hidden="true">→</i></button>`;
}
function goTo(newPath, dir){
  path = newPath;
  if(dir==='back' && query){ query=''; const s=document.getElementById('search'); if(s) s.value=''; }
  renderCatalog(true, dir);
}
function goBack(){
  if(query){ query=''; const s=document.getElementById('search'); if(s) s.value=''; renderCatalog(true,'back'); return; }
  if(path.length) goTo(path.slice(0,-1), 'back');
}
document.getElementById('winBack').onclick = goBack;

function renderCatalog(scroll, dir){
  const view = document.getElementById('catView');
  const sortEl = document.getElementById('sort');
  let html = '', labels = [], showSort = false, step = null;

  if(query){
    const list = PRODUCTS.filter(p => (p.name+' '+p.brand+' '+p.spec).toLowerCase().includes(query));
    labels = ['Пошук: «'+query+'»'];
    html = `<div class="lv-title">Знайдено: ${posWord(list.length)}</div>` + productGrid(list, false);
    showSort = true;
  }
  else if(!path.length){
    html = `<div class="lv-title">Що шукаєте?</div><div class="lv-grid lv-cats">`
      + CATS.map(catTile).join('')
      + `<button type="button" class="lv-tile lv-cat" data-cat="all"><div class="lv-ico">✨</div><div class="lv-main"><b>Усі товари</b><span>Весь асортимент одним списком</span><em>${posWord(PRODUCTS.length)}</em></div><i aria-hidden="true">→</i></button>`
      + `</div>`;
    step = {n:1,total:null};
  }
  else if(path[0]==='all'){
    labels = ['Усі товари'];
    html = productGrid(PRODUCTS, false); showSort = true; step = {n:2,total:2};
  }
  else {
    const cat = path[0], catInfo = CATS.find(c=>c.id===cat);
    const levels = LEVELS[cat] || [];
    const chosen = path.slice(1);
    let list = PRODUCTS.filter(p=>p.cat===cat);
    labels = [catInfo ? catInfo.name : cat];
    chosen.forEach((val,i)=>{
      list = list.filter(p=>String(p[levels[i]])===String(val));
      labels.push(fmtLevel(levels[i], val));
    });
    const depth = chosen.length;
    step = {n:path.length+1, total:levels.length+2};
    if(depth < levels.length){
      const key = levels[depth];
      const opts = levelOptions(list, key);
      const big = key==='vol' || key==='mg';
      html = `<div class="lv-title">${LEVEL_TITLE[key]}</div><div class="lv-grid ${big?'lv-big-grid':''}">`
        + opts.map(o=>{
            const min = Math.min(...o.items.map(i=>i.price));
            const img = (!big && o.items[0].image) ? o.items[0].image : null;
            return tileHTML(`data-val="${esc2(o.value)}"`, big, esc2(fmtLevel(key,o.value)), posWord(o.items.length), min, img, null);
          }).join('')
        + `</div>`;
    } else {
      html = `<div class="lv-title">${labels.length>1 ? esc2(labels.slice(1).join(' · '))+' — ' : ''}${posWord(list.length)}</div>`
        + productGrid(list, cat==='liquid');
      showSort = true;
    }
  }

  view.className = 'win-body ' + (dir||'');
  view.innerHTML = html;
  sortEl.style.display = showSort ? '' : 'none';
  renderCrumbs(query ? [] : labels);

  const atRoot = !query && !path.length;
  document.getElementById('winBack').style.visibility = atRoot ? 'hidden' : 'visible';
  const stepsEl = document.getElementById('winSteps');
  if(step && step.total){
    stepsEl.innerHTML = `<span>Крок ${step.n} з ${step.total}</span><div class="dots">${Array.from({length:step.total},(_,i)=>`<i class="${i<step.n?'on':''}"></i>`).join('')}</div>`;
  } else stepsEl.innerHTML = step ? '<span>Оберіть категорію</span>' : '<span>Пошук по каталогу</span>';

  view.querySelectorAll('.lv-tile').forEach(t=>t.onclick = ()=>{
    if(t.dataset.cat) goTo([t.dataset.cat], 'fwd');
    else goTo(path.concat(t.dataset.val), 'fwd');
  });
  view.querySelectorAll('.card').forEach(card=>{
    const open = ()=>openProduct(+card.dataset.pid);
    card.addEventListener('click', e=>{ if(e.target.closest('.add')) return; open(); });
    card.addEventListener('keydown', e=>{ if(e.key==='Enter' && !e.target.closest('.add')) open(); });
  });
  view.querySelectorAll('.add').forEach(btn=>{
    btn.onclick = ()=>{ addToCart(+btn.dataset.id, 1);
      btn.textContent = '✓ Додано'; setTimeout(()=>{ btn.textContent = 'До кошика'; }, 900); };
  });
  if(scroll){ const top = document.getElementById('win').getBoundingClientRect().top + window.scrollY - 130; window.scrollTo({top:Math.max(0,top),behavior:'smooth'}); }
}

