/**
 * Notification Delivery domain contracts matching backend schemas
 */

export type NotificationDeliveryStatus = "PENDING" | "PROCESSING" | "SENT" | "FAILED";

export interface NotificationDeliverySummary {
  id: string;
  candidate_profile_id: string;
  job_id: string;
  job_match_id: string;
  tailored_resume_id: string;
  notification_type: string;
  recipient_email: string;
  status: NotificationDeliveryStatus;
  attempt_count: number;
  max_attempts: number;
  provider: string;
  provider_message_id: string | null;
  sent_at: string | null;
  failed_at: string | null;
  created_at: string;
  updated_at: string;
  // Optional enriched fields
  last_error?: string | null;
  job_title?: string | null;
  company_name?: string | null;
  match_score?: number | null;
}

export interface NotificationDeliveryRead extends NotificationDeliverySummary {
  last_error: string | null;
  job_title: string | null;
  company_name: string | null;
  match_score: number | null;
}

// Backwards-compatibility alias
export type NotificationDelivery = NotificationDeliveryRead;

export interface NotificationFilterParams {
  candidate_profile_id?: string;
  status?: NotificationDeliveryStatus;
  job_id?: string;
  page?: number;
  page_size?: number;
}

export interface NotificationRetryRequest {
  force?: boolean;
}

export interface NotificationRetryResponse {
  delivery_id: string;
  status: NotificationDeliveryStatus;
  message: string;
}
