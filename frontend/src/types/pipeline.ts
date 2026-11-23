/**
 * Pipeline Run types and metrics matching backend schemas
 */

export type PipelineRunStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "PARTIALLY_COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type PipelineTriggerType = "MANUAL" | "SCHEDULED" | "API";

export interface PipelineRunMetrics {
  jobs_discovered: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_normalized: number;
  jobs_deduplicated: number;
  jobs_evaluated: number;
  matches_created: number;
  matches_qualified: number;
  semantic_analyses_completed: number;
  semantic_analyses_failed: number;
  resumes_generated: number;
  resumes_failed: number;
  notifications_sent: number;
  notifications_failed: number;
}

export interface PipelineRunSummary {
  id: string;
  candidate_profile_id: string;
  trigger_type: PipelineTriggerType;
  status: PipelineRunStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  jobs_discovered: number;
  matches_qualified: number;
  resumes_generated: number;
  notifications_sent: number;
  error_summary: string | null;
}

export interface PipelineRun {
  id: string;
  candidate_profile_id: string;
  trigger_type: PipelineTriggerType;
  status: PipelineRunStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  metrics: PipelineRunMetrics;
  error_summary: string | null;
  metadata?: Record<string, unknown>;
}

export interface PipelineRunCreateRequest {
  candidate_profile_id: string;
  trigger_type?: PipelineTriggerType;
  metadata?: Record<string, unknown>;
}

export interface PipelineRunCancelResponse {
  pipeline_run_id: string;
  status: PipelineRunStatus;
  message: string;
}

export interface PipelineRunFilterParams {
  candidate_profile_id?: string;
  status?: PipelineRunStatus;
  trigger_type?: PipelineTriggerType;
  page?: number;
  page_size?: number;
}

