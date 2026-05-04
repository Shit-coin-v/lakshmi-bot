import { apiGet } from './client.js';

export async function listClients({ q, segment, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/clients/', {
    q, segment, page, page_size: pageSize,
  });
  return { results: data, pagination };
}

export async function getClient(cardId) {
  const { data } = await apiGet(`/clients/${encodeURIComponent(cardId)}/`);
  return data;
}
