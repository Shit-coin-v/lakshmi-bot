import { beforeEach, describe, expect, it, vi } from 'vitest';

// client.js — это default export axios instance; для тестов мокаем целиком.
vi.mock('../../src/api/client.js', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  API_KEY_STORAGE: 'lps:apiKey',
}));

import client from '../../src/api/client.js';
import {
  describeUploadError,
  uploadProductImage,
} from '../../src/api/products.js';

describe('uploadProductImage', () => {
  beforeEach(() => {
    client.post.mockReset();
  });

  it('шлёт POST на /api/products/<id>/image/ с FormData', async () => {
    client.post.mockResolvedValue({
      data: {
        id: 42,
        product_code: 'MLK-032',
        name: 'Молоко',
        image_url: '/media/products/mlk-032_1.png',
        updated_at: '2026-04-25T10:00:00Z',
      },
    });
    const file = new File(['fake'], 'photo.png', { type: 'image/png' });

    const result = await uploadProductImage(42, file);

    expect(client.post).toHaveBeenCalledTimes(1);
    const [url, body, options] = client.post.mock.calls[0];
    expect(url).toBe('/api/products/42/image/');
    expect(body).toBeInstanceOf(FormData);
    expect(body.get('image')).toBe(file);
    expect(options).toHaveProperty('onUploadProgress');
    expect(result.image_url).toBe('/media/products/mlk-032_1.png');
  });

  it('передаёт колбэк прогресса аплоада в axios', async () => {
    client.post.mockResolvedValue({ data: {} });
    const file = new File(['x'], 'p.png', { type: 'image/png' });
    const onProgress = vi.fn();

    await uploadProductImage(7, file, onProgress);

    const options = client.post.mock.calls[0][2];
    expect(options.onUploadProgress).toBe(onProgress);
  });
});

describe('describeUploadError', () => {
  it('возвращает текст для типичных HTTP-кодов', () => {
    expect(describeUploadError({ response: { status: 401 } })).toMatch(/Нет прав/);
    expect(describeUploadError({ response: { status: 403 } })).toMatch(/Нет прав/);
    expect(describeUploadError({ response: { status: 404 } })).toMatch(/не найден/);
    expect(describeUploadError({ response: { status: 429 } })).toMatch(/Слишком частая/);
    expect(describeUploadError({ response: { status: 502 } })).toMatch(/обработать фото/);
  });

  it('пробрасывает detail из 400/413/415, если он задан', () => {
    expect(
      describeUploadError({ response: { status: 413, data: { detail: 'Файл 50 МБ' } } })
    ).toBe('Файл 50 МБ');
    expect(
      describeUploadError({ response: { status: 415, data: { detail: 'Только JPG' } } })
    ).toBe('Только JPG');
  });

  it('возвращает сообщение про сеть когда response отсутствует', () => {
    expect(describeUploadError({})).toMatch(/Нет сети/);
    expect(describeUploadError(undefined)).toMatch(/Нет сети/);
  });
});
