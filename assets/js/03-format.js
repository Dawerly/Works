/* Спільна функція форматування суми. */
const money = n => n.toLocaleString('uk-UA') + ' ₴';


function priceHTML(p){
  const current = money(p.price);
  return Number(p.discount_percentage) > 0
    ? `<del class="original-price">${money(Number(p.original_price))}</del> <span>${current}</span> <small class="discount-badge">−${Number(p.discount_percentage)}%</small>`
    : current;
}
const centsOf = p => p.price_cents ?? Math.round(p.price * 100);
