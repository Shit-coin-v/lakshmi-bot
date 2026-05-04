import { useQuery } from '@tanstack/react-query';
import { listOrders } from '../api/orders.js';

export function useOrders(filters) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => listOrders(filters),
    keepPreviousData: true,
  });
}
