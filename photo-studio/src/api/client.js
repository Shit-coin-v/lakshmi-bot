// axios-клиент Lakshmi Photo Studio.
// X-Api-Key подставляется автоматически из localStorage (ключ "lps:apiKey").
// При 401 ключ удаляется, страница перезагружается — это вернёт пользователя
// на экран ApiKeySetup.

import axios from 'axios';

export const API_KEY_STORAGE = 'lps:apiKey';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 180000, // загрузка фото с обработкой OpenAI может длиться до 2 мин
});

client.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem(API_KEY_STORAGE);
  if (apiKey) {
    config.headers = config.headers || {};
    config.headers['X-Api-Key'] = apiKey;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(API_KEY_STORAGE);
      // window может отсутствовать в SSR — в Vite его всегда есть
      if (typeof window !== 'undefined') {
        window.location.reload();
      }
    }
    return Promise.reject(error);
  }
);

export default client;
