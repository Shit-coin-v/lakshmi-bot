import { describe, expect, it } from 'vitest';
import { formatPrice, formatStock } from '../../src/utils/format.js';

describe('formatPrice', () => {
  it('форматирует целое число рублями', () => {
    expect(formatPrice(89)).toMatch(/89\s*₽/);
  });

  it('сохраняет дробную часть', () => {
    expect(formatPrice('1499.50')).toMatch(/1\s?499,5\s*₽/);
  });

  it('возвращает плейсхолдер для пустых значений', () => {
    expect(formatPrice(null)).toBe('—');
    expect(formatPrice(undefined)).toBe('—');
    expect(formatPrice('')).toBe('—');
  });

  it('отдаёт исходник при некорректном числе', () => {
    expect(formatPrice('abc')).toBe('abc');
  });
});

describe('formatStock', () => {
  it('форматирует целые числа без дробной части', () => {
    expect(formatStock(42)).toBe('42');
  });

  it('обрезает хвостовые нули у дробного остатка', () => {
    expect(formatStock(7.5)).toBe('7.5');
    expect(formatStock(3.1)).toBe('3.1');
    expect(formatStock(2.0)).toBe('2');
  });

  it('возвращает плейсхолдер для null/undefined', () => {
    expect(formatStock(null)).toBe('—');
    expect(formatStock(undefined)).toBe('—');
  });
});
