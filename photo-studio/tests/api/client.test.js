import { beforeEach, describe, expect, it, vi } from 'vitest';

// reload в jsdom не реализован — подменяем перед импортом client.js.
const reloadSpy = vi.fn();
Object.defineProperty(window, 'location', {
  configurable: true,
  value: { ...window.location, reload: reloadSpy },
});

import client, { API_KEY_STORAGE } from '../../src/api/client.js';

describe('axios client interceptors', () => {
  beforeEach(() => {
    reloadSpy.mockReset();
    localStorage.clear();
  });

  it('подставляет X-Api-Key из localStorage в заголовки запроса', () => {
    localStorage.setItem(API_KEY_STORAGE, 'secret-key');
    const requestHandler = client.interceptors.request.handlers[0].fulfilled;

    const config = requestHandler({ headers: {} });

    expect(config.headers['X-Api-Key']).toBe('secret-key');
  });

  it('не падает, если ключа нет — просто не добавляет заголовок', () => {
    const requestHandler = client.interceptors.request.handlers[0].fulfilled;

    const config = requestHandler({ headers: {} });

    expect(config.headers['X-Api-Key']).toBeUndefined();
  });

  it('на 401 чистит сохранённый ключ и инициирует reload', async () => {
    localStorage.setItem(API_KEY_STORAGE, 'stale');
    const errorHandler = client.interceptors.response.handlers[0].rejected;

    await expect(
      errorHandler({ response: { status: 401 } })
    ).rejects.toEqual({ response: { status: 401 } });

    expect(localStorage.getItem(API_KEY_STORAGE)).toBeNull();
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });

  it('на остальные ошибки ключ не трогает', async () => {
    localStorage.setItem(API_KEY_STORAGE, 'still-good');
    const errorHandler = client.interceptors.response.handlers[0].rejected;

    await expect(
      errorHandler({ response: { status: 500 } })
    ).rejects.toBeDefined();

    expect(localStorage.getItem(API_KEY_STORAGE)).toBe('still-good');
    expect(reloadSpy).not.toHaveBeenCalled();
  });
});
