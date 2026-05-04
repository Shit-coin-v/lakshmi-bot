import { useQuery } from '@tanstack/react-query';
import { listCategories, getCategory } from '../api/categories.js';

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: listCategories,
  });
}

export function useCategory(slug) {
  return useQuery({
    queryKey: ['category', slug],
    queryFn: () => getCategory(slug),
    enabled: !!slug,
    retry: (failureCount, error) => error?.status !== 404 && failureCount < 2,
  });
}
