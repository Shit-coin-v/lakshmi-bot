import { useQuery } from '@tanstack/react-query';
import { listBroadcastHistory } from '../api/broadcasts.js';

export function useBroadcastHistory({ page = 1, pageSize = 50 } = {}) {
  return useQuery({
    queryKey: ['broadcasts/history', page, pageSize],
    queryFn: () => listBroadcastHistory({ page, pageSize }),
    keepPreviousData: true,
  });
}
