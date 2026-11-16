import { apiGet, apiPost } from "@/lib/api-client";
import type { MasterResume } from "@/types/resumes";

export const resumesService = {
  /**
   * List candidate resumes
   */
  async listResumes(): Promise<MasterResume[]> {
    return apiGet<MasterResume[]>("/resumes");
  },

  /**
   * Fetch master resume metadata by ID
   */
  async getResume(resumeId: string): Promise<MasterResume> {
    return apiGet<MasterResume>(`/resumes/${resumeId}`);
  },

  /**
   * Set a master resume as the active resume
   */
  async activateResume(resumeId: string): Promise<MasterResume> {
    return apiPost<MasterResume>(`/resumes/${resumeId}/activate`);
  },
};

