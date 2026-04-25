// Hook загрузки списка товаров с пагинацией и поиском.
// Автоматически перезагружается при изменении параметров. Поддерживает
// отмену предыдущего запроса через AbortController.

import { useCallback, useEffect, useRef, useState } from 'react';
import { getProducts } from '../api/catalog.js';

export default function useProducts({ search = '', categoryId = null, pageSize = 50 } = {}) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const load = useCallback(
    async (nextPage, replace) => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setLoading(true);
      setError(null);
      try {
        const result = await getProducts({
          search,
          categoryId,
          page: nextPage,
          pageSize,
          signal: controller.signal,
        });
        setItems((prev) => (replace ? result.items : [...prev, ...result.items]));
        setTotal(result.total);
        setPage(result.page);
      } catch (err) {
        if (err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
        setError(err);
      } finally {
        setLoading(false);
      }
    },
    [search, categoryId, pageSize]
  );

  // Сбрасываемся на 1-ю страницу при смене фильтров
  useEffect(() => {
    load(1, true);
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, categoryId]);

  const loadMore = useCallback(() => {
    if (loading) return;
    if (items.length >= total) return;
    load(page + 1, false);
  }, [load, loading, items.length, total, page]);

  const reload = useCallback(() => load(1, true), [load]);

  return { items, page, total, loading, error, loadMore, reload };
}
