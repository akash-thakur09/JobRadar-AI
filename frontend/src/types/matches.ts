/**
 * Candidate JobMatch domain contracts matching backend schemas
 */
import type { WorkplaceType } from "./candidate";
import type { JobSummary } from "./jobs";

export type EligibilityStatus =
  | "ELIGIBLE"
  | "INELIGIBLE_EXPERIENCE"
  | "INELIGIBLE_LOCATION"
  | "INELIGIBLE_WORK_AUTH"
  | "INELIGIBLE_MANDATORY_SKILL"
  | string;

export type SemanticAnalysisStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED" | "SKIPPED" | string;

export interface JobMatchSummary {
  id: string;
  job_id: string;
  candidate_profile_id: string;
  eligibility_status: EligibilityStatus;
  semantic_analysis_status: SemanticAnalysisStatus;
  deterministic_score: number | string;
  semantic_score: number | string | null;
  final_score: number | string;
  skill_score: number | string;
  experience_score: number | string;
  title_score: number | string;
  preference_score: number | string;
  match_explanation: string;
  is_qualified: boolean;
  created_at: string;
  updated_at: string;
  job_title: string | null;
  company_name: string | null;
  workplace_type: WorkplaceType | null;
  normalized_location: string | null;
}

export interface JobMatchDetail extends JobMatchSummary {
  match_explanation_details: Record<string, unknown>;
  job?: JobSummary | null;
}

// Backwards compatibility alias
export type JobMatch = JobMatchSummary;

export interface MatchFilterParams {
  candidate_profile_id?: string;
  min_score?: number;
  eligibility?: EligibilityStatus;
  eligibility_status?: EligibilityStatus;
  page?: number;
  page_size?: number;
}
