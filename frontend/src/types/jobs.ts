/**
 * Canonical Jobs domain contracts matching backend schemas
 */
import type { EmploymentType, WorkplaceType } from "./candidate";

export type JobStatus =
  | "PENDING"
  | "CANONICALIZED"
  | "ACTIVE"
  | "EXPIRED"
  | "ARCHIVED"
  | string;

export interface JobSourceRecord {
  id: string;
  job_id: string | null;
  job_source_id: string;
  external_job_id: string;
  source_job_url: string;
  raw_payload: Record<string, unknown>;
  raw_posted_at: string | null;
  payload_hash_sha256: string;
  processing_status: string;
  processing_error: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
}

export interface JobSummary {
  id: string;
  canonical_company_name: string;
  title: string;
  canonical_application_url: string;
  workplace_type: WorkplaceType;
  normalized_location: string | null;
  employment_type: EmploymentType;
  posted_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: JobStatus;
  created_at: string;
}

export interface JobDetail extends JobSummary {
  description_text: string;
  dedup_fingerprint_sha256: string;
  source_count: number;
  sources: JobSourceRecord[];
}

// Backwards compatibility alias for components expecting CanonicalJob
export type CanonicalJob = JobSummary;

export interface JobFilterParams {
  search?: string;
  status?: JobStatus;
  workplace_type?: WorkplaceType;
  page?: number;
  page_size?: number;
}
