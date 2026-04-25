// HTTP-функции для каталога товаров и категорий.
// Возвращают распакованные данные + метаинформацию пагинации из заголовков.

import client from './client.js';

// include_hidden=true — Photo Studio показывает сотрудникам полный
// каталог, включая категории с hide_from_app=True. Backend проверяет
// X-Api-Key и игнорирует параметр для обычных клиентов.
const STAFF_PARAMS = { include_hidden: 'true' };

export async function getProducts({
  search = '',
  categoryId = null,
  hasImage = null,
  page = 1,
  pageSize = 50,
  signal,
} = {}) {
  const params = { ...STAFF_PARAMS, page, page_size: pageSize };
  if (search) params.search = search;
  if (categoryId !== null && categoryId !== undefined && categoryId !== '') {
    params.category_id = categoryId;
  }
  // has_image=true|false — серверная фильтрация по наличию фото.
  // Без неё фильтр "Готово"/"Нет фото" работал бы только локально по
  // загруженной странице и не находил товары вне первых 50.
  if (hasImage === true) params.has_image = 'true';
  else if (hasImage === false) params.has_image = 'false';
  const response = await client.get('/api/products/', { params, signal });
  return {
    items: response.data,
    total: parseInt(response.headers['x-total-count'] || '0', 10),
    page: parseInt(response.headers['x-page'] || String(page), 10),
    pageSize: parseInt(response.headers['x-page-size'] || String(pageSize), 10),
  };
}

export async function getRootCategories({ signal } = {}) {
  const response = await client.get('/api/catalog/root/', {
    params: STAFF_PARAMS,
    signal,
  });
  return response.data;
}

export async function getCategoryChildren(parentId, { signal } = {}) {
  const response = await client.get(`/api/catalog/${parentId}/children/`, {
    params: STAFF_PARAMS,
    signal,
  });
  return response.data;
}
