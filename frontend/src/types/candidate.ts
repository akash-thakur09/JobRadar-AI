/**
 * Candidate Profile, Preferences, and Skills contracts matching FastAPI schemas
 */

export type WorkplaceType = "REMOTE" | "HYBRID" | "ONSITE";
export type EmploymentType = "FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERNSHIP";

export interface CandidateProfile {
  id: string;
  user_id: string;
  full_name: string;
  headline: string | null;
  professional_summary: string | null;
  current_role: string | null;
  total_experience_months: number;
  city: string | null;
  country: string | null;
  work_authorization: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateProfileUpdate {
  full_name?: string;
  headline?: string | null;
  professional_summary?: string | null;
  current_role?: string | null;
  total_experience_months?: number;
  city?: string | null;
  country?: string | null;
  work_authorization?: string | null;
}

export interface CandidatePreferences {
  id: string;
  candidate_profile_id: string;
  minimum_relevance_score: string | number;
  preferred_titles: string[];
  preferred_workplace_types: WorkplaceType[];
  preferred_locations: string[];
  preferred_employment_types: EmploymentType[];
  max_job_age_days: number;
  created_at: string;
  updated_at: string;
}

export interface CandidatePreferencesUpdate {
  minimum_relevance_score?: number;
  preferred_titles?: string[];
  preferred_workplace_types?: WorkplaceType[];
  preferred_locations?: string[];
  preferred_employment_types?: EmploymentType[];
  max_job_age_days?: number;
}

export interface CandidateSkill {
  id: string;
  candidate_profile_id: string;
  skill_name: string;
  category: string;
  experience_months: number;
  is_core: boolean;
  created_at: string;
}

export interface CandidateSkillCreate {
  skill_name: string;
  category?: string;
  experience_months?: number;
  is_core?: boolean;
}

