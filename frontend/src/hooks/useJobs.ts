import { useQuery } from "@tanstack/react-query";
import { jobsService } from "@/services/jobs.service";
import type { JobFilterParams } from "@/types/jobs";

export const jobKeys = {
  all: ["jobs"] as const,
  lists: () => [...jobKeys.all, "list"] as const,
  list: (params?: JobFilterParams) => [...jobKeys.lists(), params] as const,
  details: () => [...jobKeys.all, "detail"] as const,
  detail: (id: string) => [...jobKeys.details(), id] as const,
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

