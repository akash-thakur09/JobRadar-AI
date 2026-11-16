/**
 * Resume and Resume Version contracts matching backend schemas
 */

export interface ResumeVersion {
  id: string;
  master_resume_id: string;
  version_number: number;
  structured_content: Record<string, unknown>;
  template_metadata?: Record<string, unknown>;
  is_valid: boolean;
  processing_status: string;
  created_at: string;
}

export interface MasterResume {
  id: string;
  candidate_profile_id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  versions?: ResumeVersion[];
}

