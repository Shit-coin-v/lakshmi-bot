import { useQuery } from '@tanstack/react-query';
import { listCampaigns } from '../api/campaigns.js';

export function useCampaigns({ status } = {}) {
  return useQuery({
    queryKey: ['campaigns', status],
    queryFn: () => listCampaigns({ status, pageSize: 100 }),
    keepPreviousData: true,
  });
}
