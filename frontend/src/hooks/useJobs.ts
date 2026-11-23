import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { jobsService } from "@/services/jobs.service";
import type { JobFilterParams } from "@/types/jobs";

export const jobKeys = {
  all: ["jobs"] as const,
  lists: () => [...jobKeys.all, "list"] as const,
  list: (params?: JobFilterParams) => [...jobKeys.lists(), params] as const,
  details: () => [...jobKeys.all, "detail"] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
  sources: (id: string) => [...jobKeys.detail(id), "sources"] as const,
};

export function useJobs(params?: JobFilterParams) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => jobsService.listJobs(params),
  });
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: jobKeys.detail(jobId),
    queryFn: () => jobsService.getJob(jobId),
    enabled: Boolean(jobId),
  });
}

export function useJobSources(jobId: string) {
  return useQuery({
    queryKey: jobKeys.sources(jobId),
    queryFn: () => jobsService.getJobSources(jobId),
    enabled: Boolean(jobId),
  });
}

export function useProcessPendingJobs() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (batchSize?: number) => jobsService.processPendingJobs(batchSize),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.lists() });
    },
  });
}
