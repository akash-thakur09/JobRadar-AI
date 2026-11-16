/**
 * Notification Delivery contracts matching backend schemas
 */

export type NotificationDeliveryStatus = "PENDING" | "PROCESSING" | "SENT" | "FAILED";

export interface NotificationDelivery {
  id: string;
  candidate_profile_id: string;
  job_id: string;
  job_match_id: string;
  tailored_resume_id: string | null;
  recipient_email: string;
  status: NotificationDeliveryStatus;
  attempt_count: number;
  max_attempts: number;
  last_attempt_at: string | null;
  sent_at: string | null;
  provider: string;
  provider_message_id: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationFilterParams {
  candidate_profile_id?: string;
  status?: NotificationDeliveryStatus;
  page?: number;
  page_size?: number;
}

