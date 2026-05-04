import { apiGet } from './client.js';

export async function getDashboard() {
  const { data } = await apiGet('/dashboard/');
  return data;
}
