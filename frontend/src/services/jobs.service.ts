import { apiGet } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { CanonicalJob, JobFilterParams } from "@/types/jobs";

export const jobsService = {
  /**
   * List paginated canonical jobs
   */
  async listJobs(params?: JobFilterParams): Promise<PaginatedResponse<CanonicalJob>> {
    return apiGet<PaginatedResponse<CanonicalJob>>("/jobs", { params });
  },

  /**
   * Retrieve canonical job details by ID
   */
  async getJob(jobId: string): Promise<CanonicalJob> {
    return apiGet<CanonicalJob>(`/jobs/${jobId}`);
  },
};

