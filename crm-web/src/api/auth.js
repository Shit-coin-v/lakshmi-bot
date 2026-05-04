import { apiGet, apiPost, UnauthorizedError } from './client.js';

export async function me() {
  try {
    const { data } = await apiGet('/auth/me/');
    return data.user;
  } catch (err) {
    if (err instanceof UnauthorizedError) return null;
    throw err;
  }
}

export async function login({ email, password }) {
  const { data } = await apiPost('/auth/login/', { email, password });
  return data.user;
}

export async function logout() {
  await apiPost('/auth/logout/');
}
