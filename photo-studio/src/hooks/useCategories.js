// Hook загрузки корневых категорий товаров. Достаточно плоского списка
// первого уровня для фильтра в каталоге.

import { useEffect, useState } from 'react';
import { getRootCategories } from '../api/catalog.js';

export default function useCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getRootCategories({ signal: controller.signal })
      .then((data) => setCategories(Array.isArray(data) ? data : []))
      .catch((err) => {
        if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
        setError(err);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return { categories, loading, error };
}
