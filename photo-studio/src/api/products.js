// HTTP-функции загрузки фото товара через backend.
// Сама обработка через OpenAI происходит на сервере — frontend только шлёт RAW.

import client from './client.js';

/**
 * Загрузить фото товара по внутреннему product_id.
 *
 * @param {number} productId — внутренний идентификатор Product.
 * @param {File|Blob} file — RAW-файл с камеры или из галереи.
 * @param {(progressEvent: any) => void} [onProgress] — колбэк прогресса аплоада.
 * @returns {Promise<{id:number, product_code:string, name:string, image_url:string, updated_at:string}>}
 */
export async function uploadProductImage(productId, file, onProgress) {
  const fd = new FormData();
  fd.append('image', file);
  const response = await client.post(`/api/products/${productId}/image/`, fd, {
    onUploadProgress: onProgress,
  });
  return response.data;
}

// Карта типичных HTTP-ошибок endpoint в человеко-читаемые сообщения.
// Используется в Preview/Form экранах при показе toast/alert.
export function describeUploadError(error) {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;
  if (status === 400) {
    return detail || 'Файл некорректен. Проверьте, что выбрано изображение.';
  }
  if (status === 401 || status === 403) {
    return 'Нет прав на загрузку. Проверьте ключ доступа.';
  }
  if (status === 404) {
    return 'Товар не найден. Вернитесь в каталог и выберите снова.';
  }
  if (status === 413) {
    return detail || 'Файл слишком большой.';
  }
  if (status === 415) {
    return detail || 'Недопустимый формат. Используйте JPG, PNG или WebP.';
  }
  if (status === 429) {
    return 'Слишком частая загрузка. Подождите минуту и попробуйте снова.';
  }
  if (status === 502) {
    return 'Не удалось обработать фото. Попробуйте переснять или отправить позже.';
  }
  if (!error?.response) {
    return 'Нет сети. Проверьте соединение и попробуйте снова.';
  }
  return 'Не удалось загрузить фото. Попробуйте снова.';
}
