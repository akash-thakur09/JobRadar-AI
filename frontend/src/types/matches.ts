/**
 * Candidate JobMatch domain contracts matching backend schemas
 */

export type EligibilityStatus = "ELIGIBLE" | "INELIGIBLE";
export type SemanticRecommendation = "STRONG_MATCH" | "POTENTIAL_MATCH" | "NOT_RECOMMENDED";

export interface ScoreBreakdown {
  skills_score: number;
  experience_score: number;
  title_score: number;
  workplace_score: number;
  bonus_score: number;
  matched_skills?: string[];
  missing_skills?: string[];
}

export interface SemanticAnalysisData {
  recommendation?: SemanticRecommendation;
  semantic_score?: number;
  confidence?: number;
  reasoning_summary?: string;
  strengths?: Array<{ claim: string; evidence: string; job_context: string }>;
  gaps?: Array<{ gap: string; impact: string; mitigation?: string }>;
}

export interface JobMatch {
  id: string;
  candidate_profile_id: string;
  job_id: string;
  eligibility_status: EligibilityStatus;
  eligibility_reasons: string[];
  deterministic_score: number;
  final_score: number;
  is_qualified: boolean;
  score_breakdown: ScoreBreakdown;
  match_explanation: string | null;
  match_explanation_details?: SemanticAnalysisData | null;
  created_at: string;
  updated_at: string;
}

export interface MatchFilterParams {
  candidate_profile_id?: string;
  min_score?: number;
  eligibility_status?: EligibilityStatus;
  page?: number;
  page_size?: number;
}

