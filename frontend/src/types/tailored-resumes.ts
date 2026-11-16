/**
 * Tailored Resumes domain contracts matching FastAPI backend schemas
 */

export type RenderingStrategy = "PRESERVED" | "FALLBACK";

export type TailoredResumeStatus =
  | "PENDING"
  | "PROCESSING"
  | "VALIDATING"
  | "RENDERING"
  | "COMPLETED"
  | "FAILED";

export interface TailoredExperienceItem {
  company: string;
  title: string;
  location?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  bullet_points: string[];
}

export interface TailoredProjectItem {
  name: string;
  description: string;
  technologies?: string[];
  link?: string | null;
}

export interface TailoredEducationItem {
  institution: string;
  degree: string;
  field_of_study?: string | null;
  graduation_date?: string | null;
}

export interface TailoredResumeContent {
  headline?: string;
  professional_summary?: string;
  skills?: string[];
  experience?: TailoredExperienceItem[];
  projects?: TailoredProjectItem[];
  education?: TailoredEducationItem[];
  tailoring_notes?: string | null;
  [key: string]: unknown;
}

export interface ClaimValidationReport {
  is_valid: boolean;
  supported_skills?: string[];
  unsupported_skills?: string[];
  supported_metrics?: string[];
  unsupported_metrics?: string[];
  repaired_claims?: string[];
  violations_detected?: string[];
  [key: string]: unknown;
}

export interface TailorResumeRequest {
  job_match_id: string;
  resume_version_id?: string | null;
  force_regenerate?: boolean;
}

export interface TailoredResumeSummary {
  id: string;
  candidate_profile_id: string;
  job_id: string;
  job_match_id: string;
  resume_version_id: string;
  rendering_strategy: RenderingStrategy;
  generation_status: TailoredResumeStatus;
  file_name?: string | null;
  file_size_bytes?: number | null;
  checksum_sha256?: string | null;
  generation_attempts: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface TailoredResumeDetail extends TailoredResumeSummary {
  tailored_content: TailoredResumeContent;
  validation_metadata: ClaimValidationReport;
  validation_error?: string | null;
}

export interface TailoredResumeFilterParams {
  candidate_profile_id?: string;
  page?: number;
  page_size?: number;
}

