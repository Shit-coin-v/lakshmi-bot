import { apiGet } from './client.js';

export async function listBroadcastHistory({ page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/broadcasts/history/', {
    page, page_size: pageSize,
  });
  return { results: data, pagination };
}
