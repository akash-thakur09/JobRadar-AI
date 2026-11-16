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

export type SemanticAnalysisStatus =
  | "PENDING"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED"
  | string;

export type SemanticRecommendation =
  | "STRONG_MATCH"
  | "GOOD_MATCH"
  | "BORDERLINE"
  | "NOT_RECOMMENDED"
  | string;

export interface SemanticStrength {
  claim: string;
  evidence?: string;
  job_context?: string;
}

export interface SemanticRisk {
  gap: string;
  impact?: "LOW" | "MEDIUM" | "HIGH" | string;
  mitigation?: string | null;
}

export interface TransferableSkill {
  candidate_skill: string;
  target_technology: string;
  rationale?: string;
}

export interface SemanticEvaluationDetails {
  semantic_score?: number;
  recommendation?: SemanticRecommendation;
  confidence?: number;
  reasoning_summary?: string;
  strengths?: SemanticStrength[];
  gaps?: SemanticRisk[];
  transferable_skills?: TransferableSkill[];
  unsupported_claims?: string[];
  [key: string]: unknown;
}

export interface DeterministicBreakdownDetails {
  total_score?: number;
  skills?: {
    matched_skills?: string[];
    missing_skills?: string[];
    candidate_skills_count?: number;
    job_skills_count?: number;
    coverage_ratio?: number;
    score?: number;
    [key: string]: unknown;
  };
  experience?: {
    candidate_months?: number;
    required_months?: number;
    candidate_seniority?: string;
    job_seniority?: string;
    score?: number;
    [key: string]: unknown;
  };
  title?: {
    candidate_title?: string;
    job_title?: string;
    similarity_ratio?: number;
    score?: number;
    [key: string]: unknown;
  };
  workplace?: {
    workplace_match?: boolean;
    location_match?: boolean;
    score?: number;
    [key: string]: unknown;
  };
  bonus?: {
    freshness_bonus?: number;
    score?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface MatchExplanationDetails {
  is_qualified?: boolean;
  qualification_status?: string;
  eligibility?: {
    is_eligible?: boolean;
    status?: EligibilityStatus;
    explanation?: string;
    checks?: Record<string, { passed: boolean; message?: string }>;
    [key: string]: unknown;
  };
  deterministic_breakdown?: DeterministicBreakdownDetails;
  semantic_evaluation?: SemanticEvaluationDetails;
  llm_degraded?: boolean;
  llm_error?: string | null;
  final_score?: number;
  [key: string]: unknown;
}

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
  match_explanation_details: MatchExplanationDetails;
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
