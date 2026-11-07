'use strict';

const $ = (selector) => document.querySelector(selector);
const productForm = $('#product-form');
const categoryForm = $('#category-form');
const state = { csrf: '', categories: [], page: 1, limit: 20, total: 0, listRequest: 0, drafts: new Map(), activeCategory: '', previewURL: null, imageURL: null };
const money = (value) => new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(Number(value));

function el(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function notify(message = '', error = false) {
  $('#status').textContent = message;
  $('#status').className = message ? (error ? 'error' : 'success') : '';
}

function showAuthenticated(authenticated) {
  $('#workspace').hidden = !authenticated;
  $('#login-panel').hidden = authenticated;
  $('#logout').hidden = !authenticated;
}

async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' };
  if (method !== 'GET') headers['X-CSRF-Token'] = state.csrf;
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const response = await fetch(path, { method, body, headers, credentials: 'same-origin' });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401) showAuthenticated(false);
    throw new Error(data?.error || `Помилка HTTP ${response.status}`);
  }
  return data;
}

function guard(handler) {
  return async (event) => {
    try { await handler(event); } catch (error) { notify(error.message || 'Помилка мережі.', true); }
  };
}

async function withBusy(form, action) {
  const fieldset = form.querySelector('fieldset');
  fieldset.disabled = true;
  try { return await action(); } finally { fieldset.disabled = false; }
}

function actionButton(label, handler, dangerous = false) {
  const button = el('button', label, dangerous ? 'danger' : 'secondary');
  button.type = 'button';
  button.addEventListener('click', guard(async () => {
    button.disabled = true;
    try { await handler(); } finally { button.disabled = false; }
  }));
  return button;
}

function option(value, label) {
  const result = el('option', label);
  result.value = value;
  return result;
}

function readAttributes() {
  return Object.fromEntries([...$('#dynamic-fields').querySelectorAll('input')].map((input) => [input.dataset.key, input.value]));
}

function renderAttributes(categoryId, attributes = {}) {
  $('#dynamic-fields').replaceChildren();
  const category = state.categories.find((item) => String(item.id) === String(categoryId));
  if (!category || !category.attribute_schema.length) {
    $('#dynamic-fields').append(el('p', category ? 'Для категорії немає додаткових полів.' : 'Спочатку створіть категорію.', 'hint'));
    return;
  }
  for (const field of category.attribute_schema) {
    const label = el('label', field.label + (field.required ? ' *' : ''));
    const input = el('input');
    input.type = 'text';
    input.maxLength = 500;
    input.required = field.required;
    input.dataset.key = field.key;
    input.value = attributes[field.key] ?? '';
    label.append(input);
    $('#dynamic-fields').append(label);
  }
}

function renderCategories() {
  const selected = $('#product-category').value;
  const filter = $('#filter-category').value;
  const attributes = readAttributes();
  $('#product-category').replaceChildren(...state.categories.map((category) => option(category.id, category.name)));
  $('#filter-category').replaceChildren(option('', 'Усі категорії'), ...state.categories.map((category) => option(category.id, category.name)));
  if (state.categories.some((category) => String(category.id) === selected)) $('#product-category').value = selected;
  if (state.categories.some((category) => String(category.id) === filter)) $('#filter-category').value = filter;
  state.activeCategory = $('#product-category').value;
  renderAttributes(state.activeCategory, selected === state.activeCategory ? attributes : {});
  $('#save-product').disabled = !state.categories.length;
  const rows = state.categories.map((category) => {
    const row = el('tr');
    const name = el('td');
    name.append(el('strong', category.name), el('p', category.attribute_schema.map((field) => field.label).join(' · ') || 'Без додаткових полів', 'hint'));
    const actions = el('td');
    const group = el('div', undefined, 'actions');
    group.append(actionButton('Редагувати', () => editCategory(category)), actionButton('Видалити', async () => {
      if (!confirm(`Видалити категорію «${category.name}»?`)) return;
      await api(`/api/categories/${category.id}`, { method: 'DELETE' });
      if (categoryForm.elements.id.value === String(category.id)) resetCategory();
      await refresh();
      notify('Категорію видалено.');
    }, true));
    actions.append(group);
    row.append(name, el('td', category.product_count), actions);
    return row;
  });
  $('#categories-body').replaceChildren(...rows);
}

async function loadProducts() {
  const requestNumber = ++state.listRequest;
  const params = new URLSearchParams({ page: state.page, limit: state.limit, q: $('#search').value, category_id: $('#filter-category').value });
  const data = await api(`/api/products?${params}`);
  if (requestNumber !== state.listRequest) return;
  state.total = data.total;
  const lastPage = Math.max(1, Math.ceil(data.total / state.limit));
  if (state.page > lastPage) { state.page = lastPage; return loadProducts(); }
  const rows = data.items.map((product) => {
    const row = el('tr');
    const picture = el('td');
    if (product.image_url) {
      const image = el('img', undefined, 'thumb');
      image.src = product.image_url;
      image.alt = product.name;
      image.loading = 'lazy';
      picture.append(image);
    } else picture.textContent = '—';
    const attributes = el('td');
    const list = el('ul', undefined, 'attribute-list');
    const schema = state.categories.find((item) => item.id === product.category_id)?.attribute_schema || [];
    for (const [key, value] of Object.entries(product.attributes)) {
      if (value) list.append(el('li', `${schema.find((field) => field.key === key)?.label || key}: ${value}`));
    }
    attributes.append(list.childElementCount ? list : el('span', '—'));
    const actions = el('td');
    const group = el('div', undefined, 'actions');
    group.append(actionButton('Редагувати', async () => withBusy(productForm, async () => editProduct(await api(`/api/products/${product.id}`)))), actionButton('Видалити', async () => {
      if (!confirm(`Видалити товар «${product.name}»?`)) return;
      await api(`/api/products/${product.id}`, { method: 'DELETE' });
      if (productForm.elements.id.value === String(product.id)) resetProduct();
      await refresh();
      notify('Товар видалено.');
    }, true));
    actions.append(group);
    row.append(picture, el('td', product.name), el('td', product.category_name), attributes,
      el('td', money(product.original_price), 'money'), el('td', `${product.discount_percentage}%`),
      el('td', money(product.final_price), 'money'), actions);
    return row;
  });
  if (!rows.length) {
    const cell = el('td', 'Товарів не знайдено.');
    cell.colSpan = 8;
    const row = el('tr');
    row.append(cell);
    rows.push(row);
  }
  $('#products-body').replaceChildren(...rows);
  $('#product-count').textContent = `Усього: ${data.total}`;
  $('#page-info').textContent = `${state.page} / ${lastPage}`;
  $('#previous').disabled = state.page <= 1;
  $('#next').disabled = state.page >= lastPage;
}

async function refresh() {
  const data = await api('/api/categories');
  state.categories = data.items;
  renderCategories();
  await loadProducts();
}

function updatePreview() {
  // Decimal integer math matches the server's ROUND_HALF_UP, including half-cent cases.
  function hundredths(value) {
    if (!/^\d{1,10}(\.\d{1,2})?$/.test(value)) return null;
    const [whole, fraction = ''] = value.split('.');
    return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  }
  const price = hundredths($('#price').value), discount = hundredths($('#discount').value);
  if (price === null || discount === null || discount > 10000n || price > 99999999999n) {
    $('#final-price').textContent = '—';
    return;
  }
  const finalCents = (price * (10000n - discount) + 5000n) / 10000n;
  $('#final-price').textContent = money(Number(finalCents) / 100);
}

function setImagePreview(url) {
  if (state.previewURL) URL.revokeObjectURL(state.previewURL);
  state.previewURL = null;
  const image = $('#image-preview');
  image.hidden = !url;
  if (url) image.src = url; else image.removeAttribute('src');
}

function resetProduct() {
  productForm.reset();
  productForm.elements.id.value = '';
  state.drafts.clear();
  state.activeCategory = $('#product-category').value;
  state.imageURL = null;
  renderAttributes(state.activeCategory);
  setImagePreview(null);
  $('#product-title').textContent = 'Новий товар';
  updatePreview();
}

function editProduct(product) {
  resetProduct();
  for (const name of ['id', 'name', 'brand', 'spec', 'description', 'category_id', 'discount_percentage']) productForm.elements[name].value = product[name];
  $('#price').value = product.original_price;
  state.activeCategory = String(product.category_id);
  renderAttributes(product.category_id, product.attributes);
  state.imageURL = product.image_url;
  setImagePreview(product.image_url);
  $('#product-title').textContent = `Редагування товару #${product.id}`;
  updatePreview();
  productForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  productForm.elements.name.focus({ preventScroll: true });
}

function addSchemaField(field = {}) {
  const row = el('div', undefined, 'schema-row');
  for (const [key, label, maximum] of [['key', 'Ключ', 50], ['label', 'Назва поля', 100]]) {
    const wrapper = el('label', label);
    const input = el('input');
    input.dataset.part = key;
    input.value = field[key] || '';
    input.required = true;
    input.maxLength = maximum;
    if (key === 'key') input.pattern = '[a-z][a-z0-9_]{0,49}';
    wrapper.append(input);
    row.append(wrapper);
  }
  const requiredLabel = el('label', undefined, 'checkbox');
  const required = el('input');
  required.type = 'checkbox';
  required.dataset.part = 'required';
  required.checked = Boolean(field.required);
  requiredLabel.append(required, document.createTextNode('Обов’язкове'));
  row.append(requiredLabel, actionButton('Прибрати', () => row.remove(), true));
  $('#schema-fields').append(row);
}

function resetCategory() {
  categoryForm.reset();
  categoryForm.elements.id.value = '';
  $('#schema-fields').replaceChildren();
  $('#category-title').textContent = 'Нова категорія';
}

function editCategory(category) {
  resetCategory();
  categoryForm.elements.id.value = category.id;
  categoryForm.elements.name.value = category.name;
  category.attribute_schema.forEach(addSchemaField);
  $('#category-title').textContent = `Редагування категорії #${category.id}`;
  categoryForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  categoryForm.elements.name.focus({ preventScroll: true });
}

$('#login-form').addEventListener('submit', guard(async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const body = { username: form.elements.username.value, password: form.elements.password.value };
  await withBusy(form, async () => {
    // Refresh a token after logout or an expired session.
    state.csrf = (await api('/api/session')).csrf_token;
    const data = await api('/api/login', { method: 'POST', body });
    state.csrf = data.csrf_token;
    showAuthenticated(true);
    form.reset();
    resetProduct();
    resetCategory();
    await refresh();
    notify();
  });
}));

$('#logout').addEventListener('click', guard(async () => {
  await api('/api/logout', { method: 'POST' });
  state.csrf = '';
  resetProduct();
  resetCategory();
  showAuthenticated(false);
  notify();
}));

productForm.addEventListener('submit', guard(async (event) => {
  event.preventDefault();
  const id = productForm.elements.id.value;
  const body = new FormData(productForm);
  body.delete('id');
  body.set('attributes', JSON.stringify(readAttributes()));
  body.set('remove_image', $('#remove-image').checked ? '1' : '0');
  await withBusy(productForm, async () => {
    const product = await api(id ? `/api/products/${id}` : '/api/products', { method: id ? 'PUT' : 'POST', body });
    await refresh();
    editProduct(product);
    notify('Товар збережено.');
  });
}));

categoryForm.addEventListener('submit', guard(async (event) => {
  event.preventDefault();
  const id = categoryForm.elements.id.value;
  const attribute_schema = [...$('#schema-fields').children].map((row) => ({
    key: row.querySelector('[data-part="key"]').value.trim(),
    label: row.querySelector('[data-part="label"]').value.trim(),
    required: row.querySelector('[data-part="required"]').checked,
  }));
  const body = { name: categoryForm.elements.name.value, attribute_schema };
  await withBusy(categoryForm, async () => {
    await api(id ? `/api/categories/${id}` : '/api/categories', { method: id ? 'PUT' : 'POST', body });
    resetCategory();
    await refresh();
    notify('Категорію збережено.');
  });
}));

$('#product-category').addEventListener('change', () => {
  state.drafts.set(state.activeCategory, readAttributes());
  state.activeCategory = $('#product-category').value;
  renderAttributes(state.activeCategory, state.drafts.get(state.activeCategory) || {});
});
$('#price').addEventListener('input', updatePreview);
$('#discount').addEventListener('input', updatePreview);
$('#new-product').addEventListener('click', resetProduct);
$('#new-category').addEventListener('click', resetCategory);
$('#add-field').addEventListener('click', () => addSchemaField());
$('#image-input').addEventListener('change', () => {
  const file = $('#image-input').files[0];
  if (file && file.size > 5 * 1024 * 1024) {
    $('#image-input').value = '';
    setImagePreview(state.imageURL);
    notify('Максимальний розмір фото — 5 МіБ.', true);
    return;
  }
  setImagePreview(null);
  if (file) {
    $('#remove-image').checked = false;
    state.previewURL = URL.createObjectURL(file);
    $('#image-preview').src = state.previewURL;
    $('#image-preview').hidden = false;
  } else setImagePreview($('#remove-image').checked ? null : state.imageURL);
});
$('#remove-image').addEventListener('change', () => {
  if ($('#remove-image').checked) $('#image-input').value = '';
  setImagePreview($('#remove-image').checked ? null : state.imageURL);
});
$('#search-form').addEventListener('submit', guard(async (event) => { event.preventDefault(); state.page = 1; await loadProducts(); }));
$('#filter-category').addEventListener('change', guard(async () => { state.page = 1; await loadProducts(); }));
$('#previous').addEventListener('click', guard(async () => { state.page = Math.max(1, state.page - 1); await loadProducts(); }));
$('#next').addEventListener('click', guard(async () => { state.page = Math.min(Math.max(1, Math.ceil(state.total / state.limit)), state.page + 1); await loadProducts(); }));

guard(async () => {
  const data = await api('/api/session');
  state.csrf = data.csrf_token;
  showAuthenticated(data.authenticated);
  if (data.authenticated) await refresh();
  updatePreview();
})();
