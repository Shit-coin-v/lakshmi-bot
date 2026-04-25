import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import useDailyProgress from '../../src/hooks/useDailyProgress.js';

function todayKey() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `lps:progress:${y}-${m}-${dd}`;
}

describe('useDailyProgress', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('инициализируется нулём при пустом localStorage', () => {
    const { result } = renderHook(() => useDailyProgress());
    expect(result.current.count).toBe(0);
  });

  it('читает существующее значение из ключа сегодняшнего дня', () => {
    localStorage.setItem(todayKey(), '5');
    const { result } = renderHook(() => useDailyProgress());
    expect(result.current.count).toBe(5);
  });

  it('инкремент увеличивает счётчик и пишет в localStorage', () => {
    const { result } = renderHook(() => useDailyProgress());

    act(() => {
      result.current.increment();
    });

    expect(result.current.count).toBe(1);
    expect(localStorage.getItem(todayKey())).toBe('1');
  });

  it('не пересекается с ключом другого дня', () => {
    localStorage.setItem('lps:progress:2000-01-01', '999');
    const { result } = renderHook(() => useDailyProgress());
    expect(result.current.count).toBe(0);
  });
});
