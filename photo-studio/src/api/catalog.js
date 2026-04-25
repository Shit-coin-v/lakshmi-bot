// HTTP-функции для каталога товаров и категорий.
// Возвращают распакованные данные + метаинформацию пагинации из заголовков.

import client from './client.js';

export async function getProducts({
  search = '',
  categoryId = null,
  page = 1,
  pageSize = 50,
  signal,
} = {}) {
  const params = { page, page_size: pageSize };
  if (search) params.search = search;
  if (categoryId !== null && categoryId !== undefined && categoryId !== '') {
    params.category_id = categoryId;
  }
  const response = await client.get('/api/products/', { params, signal });
  return {
    items: response.data,
    total: parseInt(response.headers['x-total-count'] || '0', 10),
    page: parseInt(response.headers['x-page'] || String(page), 10),
    pageSize: parseInt(response.headers['x-page-size'] || String(pageSize), 10),
  };
}

export async function getRootCategories({ signal } = {}) {
  const response = await client.get('/api/catalog/root/', { signal });
  return response.data;
}

export async function getCategoryChildren(parentId, { signal } = {}) {
  const response = await client.get(`/api/catalog/${parentId}/children/`, { signal });
  return response.data;
}
