import { useQuery } from '@tanstack/react-query';
import { listClients, getClient } from '../api/clients.js';

export function useClients(filters) {
  return useQuery({
    queryKey: ['clients', filters],
    queryFn: () => listClients(filters),
    keepPreviousData: true,
  });
}

export function useClient(cardId) {
  return useQuery({
    queryKey: ['client', cardId],
    queryFn: () => getClient(cardId),
    enabled: !!cardId,
    retry: (failureCount, error) => error?.status !== 404 && failureCount < 2,
  });
}
