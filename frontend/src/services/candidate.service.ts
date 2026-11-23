import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api-client";
import type {
  CandidatePreferences,
  CandidatePreferencesUpdate,
  CandidateProfile,
  CandidateProfileUpdate,
  CandidateSkill,
  CandidateSkillCreate,
} from "@/types/candidate";

export const candidateService = {
  /**
   * Retrieve active candidate profile
   */
  async getProfile(): Promise<CandidateProfile> {
    return apiGet<CandidateProfile>("/candidate/profile");
  },

  /**
   * Update candidate profile details
   */
  async updateProfile(payload: CandidateProfileUpdate): Promise<CandidateProfile> {
    return apiPut<CandidateProfile, CandidateProfileUpdate>("/candidate/profile", payload);
  },

  /**
   * Retrieve candidate job matching preferences
   */
  async getPreferences(): Promise<CandidatePreferences> {
    return apiGet<CandidatePreferences>("/candidate/preferences");
  },

  /**
   * Update candidate preferences
   */
  async updatePreferences(payload: CandidatePreferencesUpdate): Promise<CandidatePreferences> {
    return apiPut<CandidatePreferences, CandidatePreferencesUpdate>("/candidate/preferences", payload);
  },

  /**
   * List verified candidate skills
   */
  async listSkills(): Promise<CandidateSkill[]> {
    return apiGet<CandidateSkill[]>("/candidate/skills");
  },

  /**
   * Add a new verified skill
   */
  async addSkill(payload: CandidateSkillCreate): Promise<CandidateSkill> {
    return apiPost<CandidateSkill, CandidateSkillCreate>("/candidate/skills", payload);
  },

  /**
   * Remove a verified skill
   */
  async deleteSkill(skillId: string): Promise<void> {
    return apiDelete<void>(`/candidate/skills/${skillId}`);
  },
};

