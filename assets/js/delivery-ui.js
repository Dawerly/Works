/* Shared DOM and request helpers. Customer data is always inserted as text. */
'use strict';
const D = (()=>{
  const labels={new:'Нове',confirmed:'Підтверджено',ready:'Готове до доставки',assigned:'Прийняте кур’єром',delivering:'У дорозі',problem:'Проблема з доставкою',done:'Доставлено',cancelled:'Скасовано'};
  function el(tag,attrs,...children){const e=document.createElement(tag);for(const[k,v]of Object.entries(attrs||{})){if(v==null||v===false)continue;if(k.startsWith('on'))e.addEventListener(k.slice(2),v);else if(k==='class')e.className=v;else if(k in e)e[k]=v;else e.setAttribute(k,String(v));}children.flat().forEach(c=>{if(c!=null&&c!==false)e.append(c.nodeType?c:document.createTextNode(String(c)));});if(tag==='label'){const control=Array.from(e.children).find(n=>n.tagName==='SELECT');if(control&&!control.hasAttribute('aria-label'))control.setAttribute('aria-label',children.flat().filter(n=>typeof n==='string').join(' '));}return e;}
  let csrf='',timer;
  const cash=n=>(Number(n||0)/100).toLocaleString('uk-UA',{style:'currency',currency:'UAH'});
  const date=n=>n?new Date(n*1000).toLocaleString('uk-UA'):'—';
  function toast(message){const t=document.getElementById('toast');if(!t)return;t.textContent=message;t.classList.add('show');clearTimeout(timer);timer=setTimeout(()=>t.classList.remove('show'),4500);}
  async function request(path,data){let r;try{r=await fetch(path,{credentials:'same-origin',cache:'no-store',...(data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'dymok','X-CSRF-Token':csrf},body:JSON.stringify(data)})});}catch(e){throw new Error('Немає зв’язку із сервером. Спробуйте ще раз.');}const v=await r.json().catch(()=>({}));if(!r.ok){const e=new Error(v.error||'Не вдалося виконати дію.');e.status=r.status;throw e;}return v;}
  async function session(){const s=await request('/api/delivery/session');csrf=s.csrf_token;return s;}
  function input(label,attrs){const i=el('input',attrs);return {input:i,node:el('label',null,label,i)};}
  function button(label,fn,cls=''){return el('button',{type:'button',class:cls,onclick:async e=>{const b=e.currentTarget;b.disabled=true;try{await fn();}catch(err){toast(err.message);}finally{b.disabled=false;}}},label);}
  const key=()=>crypto.randomUUID?crypto.randomUUID():Date.now().toString(36)+Math.random().toString(36).slice(2)+Math.random().toString(36).slice(2);
  return {el,cash,date,toast,request,session,input,button,key,labels};
})();
