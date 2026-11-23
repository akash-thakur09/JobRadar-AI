import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { pipelineService } from "@/services/pipeline.service";
import type { PipelineRunCreateRequest, PipelineRunFilterParams } from "@/types/pipeline";

export const pipelineKeys = {
  all: ["pipeline"] as const,
  lists: () => [...pipelineKeys.all, "list"] as const,
  list: (params?: PipelineRunFilterParams) => [...pipelineKeys.lists(), params] as const,
  details: () => [...pipelineKeys.all, "detail"] as const,
  detail: (id: string) => [...pipelineKeys.details(), id] as const,
};

export function usePipelineRuns(params?: PipelineRunFilterParams) {
  return useQuery({
    queryKey: pipelineKeys.list(params),
    queryFn: () => pipelineService.listPipelineRuns(params),
    refetchInterval: (query) => {
      // Auto-poll every 4s if any run in the list is PENDING or RUNNING
      const items = query.state.data?.items;
      const hasActive = items?.some((r) => r.status === "PENDING" || r.status === "RUNNING");
      return hasActive ? 4000 : false;
    },
  });
}

export function usePipelineRun(runId: string) {
  return useQuery({
    queryKey: pipelineKeys.detail(runId),
    queryFn: () => pipelineService.getPipelineRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PENDING" || status === "RUNNING" ? 3000 : false;
    },
  });
}

export function useStartPipelineRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PipelineRunCreateRequest) => pipelineService.startPipelineRun(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}

export function useCancelPipelineRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (runId: string) => pipelineService.cancelPipelineRun(runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.lists() });
      queryClient.invalidateQueries({ queryKey: pipelineKeys.detail(runId) });
    },
  });
}

