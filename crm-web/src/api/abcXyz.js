import { apiGet } from './client.js';

export async function getAbcXyz() {
  const { data } = await apiGet('/abc-xyz/');
  return data;
}
