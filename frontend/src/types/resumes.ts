/**
 * Master Resume and Resume Version contracts matching FastAPI backend schemas
 */

export type ResumeProcessingStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface ResumeContactInfo {
  email?: string | null;
  phone?: string | null;
  github?: string | null;
  linkedin?: string | null;
  location?: string | null;
  [key: string]: unknown;
}

export interface ResumeExperienceItem {
  role?: string;
  company?: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  bullet_points?: string[];
  [key: string]: unknown;
}

export interface ResumeEducationItem {
  institution?: string;
  degree?: string;
  field_of_study?: string;
  graduation_date?: string;
  [key: string]: unknown;
}

export interface ResumeProjectItem {
  name?: string;
  description?: string;
  technologies?: string[];
  link?: string;
  [key: string]: unknown;
}

export interface ResumeStructuredContent {
  contact_info?: ResumeContactInfo;
  summary?: string | string[];
  skills?: string[];
  experience?: Array<string | ResumeExperienceItem>;
  education?: Array<string | ResumeEducationItem>;
  projects?: Array<string | ResumeProjectItem>;
  certifications?: string[];
  raw_text?: string;
  [key: string]: unknown;
}

export interface ResumeVersionSummary {
  id: string;
  version_number: number;
  is_valid: boolean;
  processing_status: ResumeProcessingStatus;
  created_at: string;
}

export interface ResumeVersionResponse {
  id: string;
  master_resume_id: string;
  version_number: number;
  structured_content: ResumeStructuredContent;
  template_metadata?: Record<string, unknown> | null;
  checksum_sha256: string;
  is_valid: boolean;
  processing_status: ResumeProcessingStatus;
  parsing_error?: string | null;
  created_at: string;
}

export interface MasterResumeSummary {
  id: string;
  candidate_profile_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  latest_version?: ResumeVersionSummary | null;
}

export interface MasterResumeDetailResponse extends MasterResumeSummary {
  storage_key: string;
  active_version?: ResumeVersionResponse | null;
  versions: ResumeVersionSummary[];
}

// Backwards compatibility alias
export type MasterResume = MasterResumeSummary;
export type ResumeVersion = ResumeVersionSummary;
