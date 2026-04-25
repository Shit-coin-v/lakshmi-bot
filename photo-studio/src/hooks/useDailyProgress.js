// Локальный счётчик отснятых сегодня товаров. Хранится в localStorage по
// ключу с датой; при смене даты значение начинает с нуля автоматически.

import { useCallback, useEffect, useState } from 'react';

function todayKey() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `lps:progress:${y}-${m}-${dd}`;
}

export default function useDailyProgress() {
  const [count, setCount] = useState(() => {
    if (typeof window === 'undefined') return 0;
    const raw = localStorage.getItem(todayKey());
    return raw ? parseInt(raw, 10) || 0 : 0;
  });

  // Раз в минуту проверяем, не сменилась ли дата (например, ночная смена).
  useEffect(() => {
    const interval = setInterval(() => {
      const raw = localStorage.getItem(todayKey());
      const next = raw ? parseInt(raw, 10) || 0 : 0;
      setCount((prev) => (prev !== next ? next : prev));
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  const increment = useCallback(() => {
    setCount((prev) => {
      const next = prev + 1;
      localStorage.setItem(todayKey(), String(next));
      return next;
    });
  }, []);

  return { count, increment };
}
