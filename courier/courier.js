'use strict';
const {el,cash,date,request,session,input,button,toast,labels}=D;
const app=document.getElementById('app');
let me=null,tab='available',balance=0,rows=[],loading=false;
const brand=()=>el('div',{class:'brand'},'DYMOK / ДОСТАВКА');
async function boot(){try{const s=await session();me=s.courier;if(!me)return login();if(me.must_change)return passwordForm(true);if(!me.tg)return contactForm(true);await load();}catch(e){app.replaceChildren(el('p',{class:'error'},e.message),button('Повторити',boot));}}
function login(){
  const u=input('Логін',{required:true,autocomplete:'username',autocapitalize:'off',spellcheck:false});
  const p=input('Пароль',{type:'password',required:true,autocomplete:'current-password'});const err=el('div',{class:'error',role:'alert'});
  const submit=el('button',{type:'submit'},'Увійти');
  app.replaceChildren(el('div',{class:'card login'},brand(),el('h1',null,'Кабінет кур’єра'),el('p',{class:'muted'},'Ваші доставки та робоча зміна.'),el('form',{onsubmit:async e=>{e.preventDefault();submit.disabled=true;err.textContent='';try{await session();await request('/api/courier/login',{username:u.input.value.trim(),password:p.input.value});p.input.value='';await boot();}catch(x){err.textContent=x.message;p.input.value='';}finally{submit.disabled=false;}}},u.node,p.node,err,submit),el('p',null,el('a',{href:'/'},'До магазину'))));
}
function passwordForm(required=false){
  const old=input('Поточний пароль',{type:'password',required:true,autocomplete:'current-password'}),nw=input('Новий пароль — від 10 символів',{type:'password',minLength:10,maxLength:256,required:true,autocomplete:'new-password'}),again=input('Повторіть новий пароль',{type:'password',minLength:10,required:true,autocomplete:'new-password'}),err=el('div',{class:'error',role:'alert'}),save=el('button',{type:'submit'},'Зберегти пароль');
  app.replaceChildren(el('div',{class:'card login'},brand(),el('h1',null,required?'Змініть тимчасовий пароль':'Зміна пароля'),el('p',{class:'muted'},required?'Перед початком роботи встановіть власний пароль.':'Інші сеанси будуть завершені.'),el('form',{onsubmit:async e=>{e.preventDefault();err.textContent='';if(nw.input.value!==again.input.value){err.textContent='Паролі не збігаються.';return;}save.disabled=true;try{await request('/api/courier/password',{current:old.input.value,new:nw.input.value});await boot();}catch(x){err.textContent=x.message;}finally{save.disabled=false;}}},old.node,nw.node,again.node,err,save),!required?button('Назад',boot,'secondary'):button('Вийти',logout,'secondary')));
}
function contactForm(required=false){
  const tg=input('Ваш Telegram-нік',{required:true,maxLength:33,value:me.tg||'',placeholder:'@username',autocomplete:'off',autocapitalize:'off',spellcheck:false}),error=el('div',{class:'error',role:'alert'}),save=el('button',{type:'submit'},'Зберегти контакт');
  app.replaceChildren(el('div',{class:'card login'},brand(),el('h1',null,'Контакт для покупця'),el('p',{class:'muted'},'Покупець побачить ваш Telegram лише після призначення вам його доставки.'),el('form',{onsubmit:async e=>{e.preventDefault();save.disabled=true;error.textContent='';try{await request('/api/courier/profile',{tg:tg.input.value});await boot();}catch(x){error.textContent=x.message;}finally{save.disabled=false;}}},tg.node,error,save),required?button('Вийти',logout,'secondary'):button('Назад',boot,'secondary')));
}
async function logout(){try{await request('/api/courier/logout',{});}finally{me=null;rows=[];login();}}
async function load(background=false){if(loading)return;loading=true;try{const r=await request('/api/courier/orders?view='+tab);rows=r.orders;balance=r.cash_balance_cents;render();}catch(e){if(e.status===401){me=null;rows=[];login();}else if(e.status===403)await boot();else if(!background)toast(e.message);}finally{loading=false;}}
function render(){
  app.replaceChildren(el('header',{class:'top'},el('div',null,brand(),el('h1',null,me.name),el('p',{class:'muted'},me.on_shift?'Ви на зміні':'Зміна не розпочата')),el('div',{class:'row'},button(me.on_shift?'Завершити зміну':'Почати зміну',async()=>{await request('/api/courier/shift',{on_shift:!me.on_shift});me.on_shift=!me.on_shift;await load();},me.on_shift?'secondary':''),button('Профіль',()=>contactForm(),'secondary'),button('Пароль',()=>passwordForm(),'secondary'),button('Вийти',logout,'secondary'))),
    el('div',{class:'notice row spread'},el('span',null,'Готівка до передачі адміністратору'),el('span',{class:'cash'},cash(balance))),
    el('nav',{class:'tabs','aria-label':'Розділи'},...[['available','Доступні'],['mine','Мої доставки'],['history','Історія']].map(([id,label])=>el('button',{'aria-selected':String(tab===id),onclick:async()=>{tab=id;await load();}},label))),
    el('div',{class:'row spread'},el('p',{class:'muted small'},tab==='available'?'Контакти й точна адреса відкриються після прийняття.':tab==='history'?'Історія без персональних даних покупців.':'Прийняті вами доставки.'),button('Оновити',()=>load(),'secondary')),
    rows.length?el('div',{class:'grid'},rows.map(card)):el('div',{class:'empty'},tab==='available'&&!me.on_shift?'Почніть зміну, щоб переглядати доступні доставки.':'У цьому розділі поки немає замовлень.'));
}
function card(o){
  const owned=tab==='mine';const box=el('article',{class:'card'},el('div',{class:'row spread'},el('h2',null,'Замовлення №'+o.id),el('span',{class:'badge'},labels[o.status]||o.status)),el('p',{class:'muted small'},date(o.created)),el('div',{class:'details'},el('div',null,'Район: '+o.zone_name),el('div',null,'Час: '+(o.delivery_time||o.wish_time||'Узгоджується')),el('div',null,'Оплата: '+o.pay),el('div',null,'Винагорода: '+cash(o.reward_cents))),el('p',{class:'total'},cash(o.total_cents)));
  if(tab==='available')box.append(button('Взяти замовлення',async()=>{await request('/api/courier/orders/'+o.id+'/claim',{version:o.version});tab='mine';await load();}));
  if(owned){
    box.append(el('div',{class:'details'},el('b',null,o.name),el('div',null,o.address),el('div',null,'Телефон: '+o.phone),el('div',null,'Telegram клієнта: ',/^@[A-Za-z0-9_]{3,32}$/.test(o.tg||'')?el('a',{href:'https://t.me/'+o.tg.slice(1),target:'_blank',rel:'noopener noreferrer'},o.tg):o.tg),o.note?el('p',{class:'notice'},o.note):null,o.courier_note?el('p',{class:'error'},'Проблема: '+o.courier_note):null,o.release_requested?el('p',{class:'notice'},'Запит відмови очікує рішення адміністратора.'):null),el('ul',null,o.items.map(i=>el('li',null,i.name+(i.spec?' · '+i.spec:'')+' × '+i.qty))));
    box.append(el('div',{class:'actions'},el('a',{class:'button secondary',href:'tel:'+o.phone.replace(/[^\d+]/g,'')},'Подзвонити'),el('a',{class:'button secondary',href:'https://www.google.com/maps/dir/?api=1&destination='+encodeURIComponent(o.address),target:'_blank',rel:'noopener noreferrer'},'Маршрут')));
    const actions=el('div',{class:'actions'});
    if(o.status==='assigned'||o.status==='problem')actions.append(button('В дорозі',()=>change(o,'delivering')));
    if(o.status==='delivering')actions.append(button('Доставлено',async()=>{if(!confirm('Підтвердити доставку №'+o.id+'?'+(o.pay==='Готівкою при отриманні'?' Отримано '+cash(o.total_cents)+' готівкою.':'')))return;await change(o,'done',{cash_received_cents:o.pay==='Готівкою при отриманні'?o.total_cents:0});}));
    actions.append(button('Проблема',async()=>{const note=prompt('Опишіть проблему з доставкою:');if(note?.trim())await change(o,'problem',{note});},'secondary'),button('Запит відмови',async()=>{const note=prompt('Причина відмови (рішення приймає адміністратор):');if(note?.trim())await change(o,'release_requested',{note});},'danger'));box.append(actions);
  }return box;
}
async function change(o,status,extra={}){try{await request('/api/courier/orders/'+o.id+'/status',{version:o.version,status,...extra});toast('Статус оновлено');}finally{await load();}}
setInterval(async()=>{if(!document.hidden&&me&&!me.must_change&&document.querySelector('.tabs')){const s=await session().catch(()=>null);if(s?.courier){me=s.courier;await load(true);}else if(s){me=null;rows=[];login();}}},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)boot();});
boot();
