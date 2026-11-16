import { apiGet } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { JobDetail, JobFilterParams, JobSummary } from "@/types/jobs";

export const jobsService = {
  /**
   * List paginated canonical jobs
   */
  async listJobs(params?: JobFilterParams): Promise<PaginatedResponse<JobSummary>> {
    return apiGet<PaginatedResponse<JobSummary>>("/jobs", { params });
  },

  /**
   * Retrieve canonical job details by ID
   */
  async getJob(jobId: string): Promise<JobDetail> {
    return apiGet<JobDetail>(`/jobs/${jobId}`);
  },
};
