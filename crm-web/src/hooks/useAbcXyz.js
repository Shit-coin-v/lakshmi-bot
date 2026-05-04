import { useQuery } from '@tanstack/react-query';
import { getAbcXyz } from '../api/abcXyz.js';

export function useAbcXyz() {
  return useQuery({
    queryKey: ['abc-xyz'],
    queryFn: getAbcXyz,
  });
}
