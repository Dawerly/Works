/* Наявні категорії, назви рівнів, кольори та початкова обробка даних. */
const CATS = [
  {id:'liquid',name:'Рідини',desc:'Обери об\'єм і міцність, далі бренд та смак',icon:'💧'},
  {id:'pod',name:'Под-системи',desc:'Обери бренд, модель і колір',icon:'🔋'},
  {id:'disposable',name:'Одноразки',desc:'Обери бренд і смак',icon:'💨'},
  {id:'access',name:'Комплектуючі',desc:'Картриджі, бустери, кальянні суміші та інше',icon:'🧩'}
];
const CATLABEL = {disposable:'Одноразка',pod:'Под-система',liquid:'Рідина',access:'Аксесуар'};

/* Рівні вибору в каталозі для кожної категорії (по порядку) */
const LEVELS = { liquid:['vol','mg','brand'], pod:['brand','name'], disposable:['brand'], access:[] };
const LEVEL_TITLE = { vol:'Оберіть об\'єм', mg:'Оберіть міцність нікотину', brand:'Оберіть бренд', name:'Оберіть модель' };
const CAT_COLOR = {liquid:'#ff18e8', pod:'#8b2cff', disposable:'#19e7ff', access:'#b026ff'};

/* Об'єм (мл) і міцність (мг) рідин.
   Беруться з назви товару (напр. "30ml 50mg"), інакше з таблиці нижче, інакше DEFAULT.
   >>> ПЕРЕВІРТЕ ці значення й за потреби виправте. <<< */
const LIQUID_DEFAULT = { vol:30, mg:65 };
const LIQUID_BY_BRAND = {
  // 'Octobar': { vol:30, mg:65 },
  // 'Black Limit': { vol:10, mg:65 },
};
PRODUCTS.forEach(p=>{
  p.color = p.color || CAT_COLOR[p.cat] || '#b026ff';
  if(p.cat==='liquid'){
    const t = p.name + ' ' + p.spec;
    const v = t.match(/(\d+)\s?ml/i), m = t.match(/(\d+)\s?mg/i);
    const b = LIQUID_BY_BRAND[p.brand] || {};
    if(p.vol==null) p.vol = v ? +v[1] : (b.vol ?? LIQUID_DEFAULT.vol);
    if(p.mg==null)  p.mg  = m ? +m[1] : (b.mg  ?? LIQUID_DEFAULT.mg);
  }
});
