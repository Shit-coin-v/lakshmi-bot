import { describe, expect, it } from 'vitest';
import {
  PHOTO_STATUS,
  PHOTO_STATUS_FILTERS,
  getPhotoStatus,
  getPhotoStatusLabel,
} from '../../src/utils/photoStatus.js';

describe('getPhotoStatus', () => {
  it('возвращает MISSING при пустом image_url', () => {
    expect(getPhotoStatus({ image_url: null })).toBe(PHOTO_STATUS.MISSING);
    expect(getPhotoStatus({ image_url: '' })).toBe(PHOTO_STATUS.MISSING);
    expect(getPhotoStatus({})).toBe(PHOTO_STATUS.MISSING);
    expect(getPhotoStatus(null)).toBe(PHOTO_STATUS.MISSING);
  });

  it('возвращает READY когда image_url задан', () => {
    expect(getPhotoStatus({ image_url: '/media/products/x.png' })).toBe(
      PHOTO_STATUS.READY
    );
  });
});

describe('getPhotoStatusLabel', () => {
  it('маппит статусы в русские лейблы', () => {
    expect(getPhotoStatusLabel(PHOTO_STATUS.READY)).toBe('Готово');
    expect(getPhotoStatusLabel(PHOTO_STATUS.MISSING)).toBe('Нет фото');
  });

  it('по умолчанию считает статус missing', () => {
    expect(getPhotoStatusLabel('unknown')).toBe('Нет фото');
  });
});

describe('PHOTO_STATUS_FILTERS', () => {
  it('содержит "all", "missing", "ready"', () => {
    const values = PHOTO_STATUS_FILTERS.map((f) => f.value);
    expect(values).toEqual(['all', PHOTO_STATUS.MISSING, PHOTO_STATUS.READY]);
  });
});
