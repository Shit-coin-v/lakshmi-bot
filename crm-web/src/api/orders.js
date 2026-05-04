import { apiGet } from './client.js';

export async function listOrders({ status, purchaseType, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/orders/', {
    status, purchaseType, page, page_size: pageSize,
  });
  return { results: data, pagination };
}
