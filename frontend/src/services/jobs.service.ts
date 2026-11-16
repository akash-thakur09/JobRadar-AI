import { apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { JobDetail, JobFilterParams, JobSourceRecord, JobSummary } from "@/types/jobs";

export const jobsService = {
  /**
   * List paginated canonical jobs with optional search and filters
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

  /**
   * Retrieve linked discovery source records and provenance for a canonical job
   */
  async getJobSources(jobId: string): Promise<JobSourceRecord[]> {
    return apiGet<JobSourceRecord[]>(`/jobs/${jobId}/sources`);
  },

  /**
   * Trigger processing of pending raw job postings into canonical jobs
   */
  async processPendingJobs(batchSize = 100): Promise<{ queued_count: number; processed_count: number }> {
    return apiPost<{ queued_count: number; processed_count: number }>("/jobs/process-pending", undefined, {
      params: { batch_size: batchSize },
    });
  },
};
