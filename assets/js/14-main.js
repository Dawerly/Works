/* Запуск застосунку після підключення всіх попередніх файлів. */
renderCatalog(); renderCart(); routeFromHash();
document.getElementById('statCount').textContent = PRODUCTS.length;
