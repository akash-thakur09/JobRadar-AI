import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import type {
  TailoredResumeDetail,
  TailoredResumeFilterParams,
  TailorResumeRequest,
} from "@/types/tailored-resumes";

export const tailoredResumeKeys = {
  all: ["tailored-resumes"] as const,
  lists: () => [...tailoredResumeKeys.all, "list"] as const,
  list: (params?: TailoredResumeFilterParams) => [...tailoredResumeKeys.lists(), params] as const,
  details: () => [...tailoredResumeKeys.all, "detail"] as const,
  detail: (id: string) => [...tailoredResumeKeys.details(), id] as const,
};

export function useTailoredResumes(params?: TailoredResumeFilterParams) {
  return useQuery({
    queryKey: tailoredResumeKeys.list(params),
    queryFn: () => tailoredResumesService.listTailoredResumes(params),
  });
}

export function useTailoredResume(id: string, options?: { autoPoll?: boolean }) {
  const autoPoll = options?.autoPoll ?? true;

  return useQuery({
    queryKey: tailoredResumeKeys.detail(id),
    queryFn: () => tailoredResumesService.getTailoredResume(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      if (!autoPoll) return false;
      const data = query.state.data as TailoredResumeDetail | undefined;
      if (!data) return false;
      const isProcessing =
        data.generation_status === "PENDING" ||
        data.generation_status === "PROCESSING" ||
        data.generation_status === "VALIDATING" ||
        data.generation_status === "RENDERING";
      return isProcessing ? 2500 : false;
    },
  });
}

export function useCreateTailoredResume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: TailorResumeRequest) => tailoredResumesService.createTailoredResume(request),
    onSuccess: (newTailored) => {
      queryClient.invalidateQueries({ queryKey: tailoredResumeKeys.lists() });
      queryClient.setQueryData(tailoredResumeKeys.detail(newTailored.id), newTailored);
    },
  });
}

