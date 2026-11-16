import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { candidateService } from "@/services/candidate.service";
import type { CandidatePreferencesUpdate, CandidateProfileUpdate } from "@/types/candidate";

export const candidateKeys = {
  all: ["candidate"] as const,
  profile: () => [...candidateKeys.all, "profile"] as const,
  preferences: () => [...candidateKeys.all, "preferences"] as const,
  skills: () => [...candidateKeys.all, "skills"] as const,
};

export function useCandidateProfile() {
  return useQuery({
    queryKey: candidateKeys.profile(),
    queryFn: () => candidateService.getProfile(),
  });
}

export function useUpdateCandidateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CandidateProfileUpdate) => candidateService.updateProfile(payload),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(candidateKeys.profile(), updatedProfile);
      queryClient.invalidateQueries({ queryKey: candidateKeys.profile() });
    },
  });
}

export function useCandidatePreferences() {
  return useQuery({
    queryKey: candidateKeys.preferences(),
    queryFn: () => candidateService.getPreferences(),
  });
}

export function useUpdateCandidatePreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CandidatePreferencesUpdate) => candidateService.updatePreferences(payload),
    onSuccess: (updatedPreferences) => {
      queryClient.setQueryData(candidateKeys.preferences(), updatedPreferences);
      queryClient.invalidateQueries({ queryKey: candidateKeys.preferences() });
    },
  });
}

export function useCandidateSkills() {
  return useQuery({
    queryKey: candidateKeys.skills(),
    queryFn: () => candidateService.listSkills(),
  });
}

