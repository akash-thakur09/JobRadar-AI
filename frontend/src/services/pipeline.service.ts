import { apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type {
  PipelineRun,
  PipelineRunCancelResponse,
  PipelineRunCreateRequest,
  PipelineRunFilterParams,
  PipelineRunSummary,
} from "@/types/pipeline";

export const pipelineService = {
  /**
   * Enqueue and start a new orchestrated pipeline run
   */
  async startPipelineRun(payload: PipelineRunCreateRequest): Promise<PipelineRun> {
    return apiPost<PipelineRun, PipelineRunCreateRequest>("/pipeline-runs", payload);
  },

  /**
   * List paginated pipeline run summaries
   */
  async listPipelineRuns(params?: PipelineRunFilterParams): Promise<PaginatedResponse<PipelineRunSummary>> {
    return apiGet<PaginatedResponse<PipelineRunSummary>>("/pipeline-runs", {
      params: {
        candidate_profile_id: params?.candidate_profile_id,
        status: params?.status,
        trigger_type: params?.trigger_type,
        page: params?.page || 1,
        page_size: params?.page_size || 20,
      },
    });
  },

  /**
   * Fetch full operational metrics and details for a specific run
   */
  async getPipelineRun(runId: string): Promise<PipelineRun> {
    return apiGet<PipelineRun>(`/pipeline-runs/${runId}`);
  },

  /**
   * Cancel an active pipeline run
   */
  async cancelPipelineRun(runId: string): Promise<PipelineRunCancelResponse> {
    return apiPost<PipelineRunCancelResponse>(`/pipeline-runs/${runId}/cancel`);
  },
};

