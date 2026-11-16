import { apiClient, apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type {
  TailoredResumeDetail,
  TailoredResumeFilterParams,
  TailoredResumeSummary,
  TailorResumeRequest,
} from "@/types/tailored-resumes";

export const tailoredResumesService = {
  /**
   * List paginated tailored resumes for the candidate
   */
  async listTailoredResumes(
    params?: TailoredResumeFilterParams
  ): Promise<PaginatedResponse<TailoredResumeSummary>> {
    return apiGet<PaginatedResponse<TailoredResumeSummary>>("/tailored-resumes", { params });
  },

  /**
   * Fetch full details of a tailored resume by ID
   */
  async getTailoredResume(id: string): Promise<TailoredResumeDetail> {
    return apiGet<TailoredResumeDetail>(`/tailored-resumes/${id}`);
  },

  /**
   * Enqueue or re-run truthful resume tailoring pipeline
   */
  async createTailoredResume(request: TailorResumeRequest): Promise<TailoredResumeSummary> {
    return apiPost<TailoredResumeSummary, TailorResumeRequest>("/tailored-resumes", request);
  },

  /**
   * Download the compiled ATS-optimized PDF artifact
   */
  async downloadTailoredPdf(id: string): Promise<{ data: Blob; filename?: string }> {
    const response = await apiClient.get<Blob>(`/tailored-resumes/${id}/download`, {
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

