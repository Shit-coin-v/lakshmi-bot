// Локальный статус фото товара. Backend пока не отдаёт явный image_status,
// поэтому различаем только "нет фото" и "готово". Архитектура hook'а
// рассчитана на расширение, когда статус будет приходить с backend.

export const PHOTO_STATUS = {
  MISSING: 'missing',
  READY: 'ready',
};

export function getPhotoStatus(product) {
  if (!product || !product.image_url) return PHOTO_STATUS.MISSING;
  return PHOTO_STATUS.READY;
}

export function getPhotoStatusLabel(status) {
  switch (status) {
    case PHOTO_STATUS.READY:
      return 'Готово';
    case PHOTO_STATUS.MISSING:
    default:
      return 'Нет фото';
  }
}

// Список значений фильтра + опция "Все"
export const PHOTO_STATUS_FILTERS = [
  { value: 'all', label: 'Все' },
  { value: PHOTO_STATUS.MISSING, label: 'Нет фото' },
  { value: PHOTO_STATUS.READY, label: 'Готово' },
];
