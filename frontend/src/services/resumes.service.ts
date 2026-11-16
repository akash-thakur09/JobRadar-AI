import { apiClient, apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type {
  MasterResumeDetailResponse,
  MasterResumeSummary,
  ResumeStructuredContent,
  ResumeVersionResponse,
} from "@/types/resumes";

export const resumesService = {
  /**
   * List paginated master resumes for the candidate
   */
  async listResumes(params?: { page?: number; page_size?: number }): Promise<PaginatedResponse<MasterResumeSummary>> {
    return apiGet<PaginatedResponse<MasterResumeSummary>>("/resumes", { params });
  },

  /**
   * Fetch complete master resume detail by ID with active version and versions list
   */
  async getResume(resumeId: string): Promise<MasterResumeDetailResponse> {
    return apiGet<MasterResumeDetailResponse>(`/resumes/${resumeId}`);
  },

  /**
   * Retrieve parsed structured JSON content for the master resume
   */
  async getResumeContent(resumeId: string): Promise<ResumeStructuredContent> {
    return apiGet<ResumeStructuredContent>(`/resumes/${resumeId}/content`);
  },

  /**
   * Upload a new master resume file (PDF or DOCX) as multipart/form-data
   */
  async uploadResume(file: File): Promise<MasterResumeDetailResponse> {
    const formData = new FormData();
    formData.append("file", file, file.name);

    const response = await apiClient.post<MasterResumeDetailResponse>("/resumes/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  /**
   * Designate a master resume as the active resume for matching and tailoring
   */
  async activateResume(resumeId: string): Promise<MasterResumeDetailResponse> {
    return apiPost<MasterResumeDetailResponse>(`/resumes/${resumeId}/activate`);
  },

  /**
   * List all parsed versions and extraction histories for a master resume
   */
  async listResumeVersions(resumeId: string): Promise<ResumeVersionResponse[]> {
    return apiGet<ResumeVersionResponse[]>(`/resumes/${resumeId}/versions`);
  },

  /**
   * Download the original resume binary file (PDF or DOCX)
   */
  async downloadResumeFile(resumeId: string): Promise<{ data: Blob; filename?: string }> {
    const response = await apiClient.get<Blob>(`/resumes/${resumeId}/download`, {
      responseType: "blob",
    });

    let filename: string | undefined;
    const disposition = response.headers["content-disposition"] as string | undefined;
    if (disposition) {
      const match = /filename=["']?([^"';]+)["']?/.exec(disposition);
      if (match && match[1]) {
        filename = match[1];
      }
    }

    return { data: response.data, filename };
  },
};
