import { useQuery } from "@tanstack/react-query";
import type { CfnewsVeilleResponse } from "@/types";

export function useCfnews(limite: number = 10) {
  return useQuery<CfnewsVeilleResponse>({
    queryKey: ["cfnews-veille", limite],
    queryFn: async () => {
      const res = await fetch(`/api/cfnews/veille?limite=${limite}`);
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
    retry: 2,
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  });
}
