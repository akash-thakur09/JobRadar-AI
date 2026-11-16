import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { resumesService } from "@/services/resumes.service";

export const resumeKeys = {
  all: ["resumes"] as const,
  lists: () => [...resumeKeys.all, "list"] as const,
  list: (params?: { page?: number; page_size?: number }) => [...resumeKeys.lists(), params] as const,
  details: () => [...resumeKeys.all, "detail"] as const,
  detail: (id: string) => [...resumeKeys.details(), id] as const,
  contents: () => [...resumeKeys.all, "content"] as const,
  content: (id: string) => [...resumeKeys.contents(), id] as const,
  versions: (id: string) => [...resumeKeys.detail(id), "versions"] as const,
};

export function useResumes(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: resumeKeys.list(params),
    queryFn: () => resumesService.listResumes(params),
  });
}

export function useResume(resumeId: string) {
  return useQuery({
    queryKey: resumeKeys.detail(resumeId),
    queryFn: () => resumesService.getResume(resumeId),
    enabled: Boolean(resumeId),
  });
}

export function useResumeContent(resumeId: string) {
  return useQuery({
    queryKey: resumeKeys.content(resumeId),
    queryFn: () => resumesService.getResumeContent(resumeId),
    enabled: Boolean(resumeId),
  });
}

export function useResumeVersions(resumeId: string) {
  return useQuery({
    queryKey: resumeKeys.versions(resumeId),
    queryFn: () => resumesService.listResumeVersions(resumeId),
    enabled: Boolean(resumeId),
  });
}

export function useUploadResume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => resumesService.uploadResume(file),
    onSuccess: (newResume) => {
      queryClient.setQueryData(resumeKeys.detail(newResume.id), newResume);
      queryClient.invalidateQueries({ queryKey: resumeKeys.lists() });
    },
  });
}

export function useActivateResume() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (resumeId: string) => resumesService.activateResume(resumeId),
    onSuccess: (updatedResume) => {
      queryClient.setQueryData(resumeKeys.detail(updatedResume.id), updatedResume);
      queryClient.invalidateQueries({ queryKey: resumeKeys.lists() });
    },
  });
}

