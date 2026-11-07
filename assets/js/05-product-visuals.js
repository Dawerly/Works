/* Наявні функції SVG-заглушок та мініатюр. */
function svgIcon(p){
  const c = p.color, id = 'g'+p.id;
  const grad = `<defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${c}"/><stop offset="1" stop-color="${c}" stop-opacity=".55"/></linearGradient></defs>`;
  if(p.cat==='liquid'){
    return `<svg viewBox="0 0 60 100">${grad}<ellipse cx="30" cy="92" rx="16" ry="4" fill="#000" opacity=".35"/><rect x="22" y="6" width="16" height="10" rx="2" fill="${c}" opacity=".5"/><rect x="24" y="14" width="12" height="14" fill="${c}" opacity=".75"/><path d="M20 28h20l4 10v48a6 6 0 01-6 6H22a6 6 0 01-6-6V38z" fill="url(#${id})" stroke="${c}" stroke-width="1"/><rect x="18" y="46" width="24" height="10" fill="#fff" opacity=".08"/></svg>`;
  }
  if(p.cat==='access'){
    return `<svg viewBox="0 0 60 100">${grad}<ellipse cx="30" cy="92" rx="16" ry="4" fill="#000" opacity=".35"/><rect x="16" y="30" width="28" height="42" rx="7" fill="url(#${id})" stroke="${c}" stroke-width="1"/><rect x="22" y="16" width="16" height="18" rx="4" fill="${c}"/><circle cx="30" cy="80" r="6" fill="${c}" opacity=".6"/></svg>`;
  }
  return `<svg viewBox="0 0 60 100">${grad}<ellipse cx="30" cy="92" rx="17" ry="4" fill="#000" opacity=".35"/><rect x="13" y="8" width="34" height="84" rx="16" fill="${c}" opacity=".14"/><rect x="19" y="16" width="22" height="68" rx="11" fill="url(#${id})" stroke="${c}" stroke-width="1"/><rect x="23" y="4" width="14" height="16" rx="4" fill="${c}" opacity=".7"/><rect x="24" y="30" width="4" height="30" rx="2" fill="#fff" opacity=".18"/></svg>`;
}
function thumbHTML(p){
  const visual = p.image
    ? `<img src="${esc2(p.image)}" alt="${esc2(p.name)}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'" style="max-width:78%;max-height:86%;object-fit:contain;position:relative;z-index:2;filter:drop-shadow(0 0 16px ${p.color}66)"><span style="display:none;position:relative;z-index:2;color:var(--muted);font-size:12px;text-align:center;padding:18px">Фото товару недоступне</span>`
    : svgIcon(p);
  return `<div class="thumb" style="background:radial-gradient(ellipse at 50% 72%, ${p.color}28, transparent 48%), linear-gradient(135deg,rgba(255,255,255,.035),rgba(255,24,232,.025))">${visual}</div>`;
}

