/**
 * Canonical Jobs domain contracts matching backend schemas
 */
import { EmploymentType, WorkplaceType } from "./candidate";

export type JobStatus = "DISCOVERED" | "NORMALIZED" | "MATCHED" | "NOTIFIED" | "ARCHIVED";

export interface CanonicalJob {
  id: string;
  source_type: string;
  external_job_id: string;
  canonical_company_name: string;
  company_domain: string | null;
  title: string;
  canonical_title: string;
  description_clean: string;
  employment_type: EmploymentType;
  workplace_type: WorkplaceType;
  normalized_location: string | null;
  country: string | null;
  city: string | null;
  salary_currency: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_interval: string | null;
  canonical_application_url: string;
  normalized_skills: string[];
  status: JobStatus;
  posted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobFilterParams {
  search?: string;
  workplace_type?: WorkplaceType;
  employment_type?: EmploymentType;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

