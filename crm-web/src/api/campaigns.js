import { apiGet } from './client.js';

export async function listCampaigns({ status, page, pageSize } = {}) {
  const { data, pagination } = await apiGet('/campaigns/', {
    status, page, page_size: pageSize,
  });
  return { results: data, pagination };
}
