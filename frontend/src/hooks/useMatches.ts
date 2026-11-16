import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { matchesService } from "@/services/matches.service";
import type { MatchFilterParams } from "@/types/matches";

export const matchKeys = {
  all: ["matches"] as const,
  lists: () => [...matchKeys.all, "list"] as const,
  list: (params?: MatchFilterParams) => [...matchKeys.lists(), params] as const,
  details: () => [...matchKeys.all, "detail"] as const,
  detail: (id: string) => [...matchKeys.details(), id] as const,
};

export function useMatches(params?: MatchFilterParams) {
  return useQuery({
    queryKey: matchKeys.list(params),
    queryFn: () => matchesService.listMatches(params),
  });
}

export function useMatch(matchId: string) {
  return useQuery({
    queryKey: matchKeys.detail(matchId),
    queryFn: () => matchesService.getMatch(matchId),
    enabled: Boolean(matchId),
  });
}

export function useReevaluateMatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ jobId, candidateProfileId }: { jobId: string; candidateProfileId?: string }) =>
      matchesService.reEvaluateMatch(jobId, candidateProfileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: matchKeys.lists() });
    },
  });
}

