import { apiGet } from './client.js';

export async function listCategories() {
  const { data } = await apiGet('/categories/');
  return data;
}

export async function getCategory(slug) {
  const { data } = await apiGet(`/categories/${encodeURIComponent(slug)}/`);
  return data;
}
