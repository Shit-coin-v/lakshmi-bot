// Hook для управления X-Api-Key: чтение из localStorage и установка с
// принудительной перезагрузкой страницы (нужно, чтобы axios подхватил
// ключ во всех существующих экземплярах).

import { useCallback, useEffect, useState } from 'react';
import { API_KEY_STORAGE } from '../api/client.js';

export default function useApiKey() {
  const [apiKey, setApiKey] = useState(() => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(API_KEY_STORAGE);
  });

  // Слушаем изменения ключа в других вкладках, чтобы не разойтись.
  useEffect(() => {
    function handleStorage(event) {
      if (event.key === API_KEY_STORAGE) {
        setApiKey(event.newValue);
      }
    }
    window.addEventListener('storage', handleStorage);
    return () => window.removeEventListener('storage', handleStorage);
  }, []);

  const save = useCallback((key) => {
    const trimmed = (key || '').trim();
    if (!trimmed) return;
    localStorage.setItem(API_KEY_STORAGE, trimmed);
    setApiKey(trimmed);
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem(API_KEY_STORAGE);
    setApiKey(null);
  }, []);

  return { apiKey, save, clear, isReady: Boolean(apiKey) };
}
