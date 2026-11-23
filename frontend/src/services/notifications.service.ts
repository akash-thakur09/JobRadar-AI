import { apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type {
  NotificationDeliveryRead,
  NotificationDeliverySummary,
  NotificationFilterParams,
  NotificationRetryRequest,
  NotificationRetryResponse,
} from "@/types/notifications";

export const notificationsService = {
  /**
   * List notification delivery records with optional status and candidate filters
   */
  async listNotifications(
    params?: NotificationFilterParams
  ): Promise<PaginatedResponse<NotificationDeliverySummary>> {
    return apiGet<PaginatedResponse<NotificationDeliverySummary>>("/notifications", {
      params: {
        candidate_profile_id: params?.candidate_profile_id,
        status: params?.status,
        job_id: params?.job_id,
        page: params?.page || 1,
        page_size: params?.page_size || 20,
      },
    });
  },

  /**
   * Fetch complete notification delivery details by ID
   */
  async getNotification(deliveryId: string): Promise<NotificationDeliveryRead> {
    return apiGet<NotificationDeliveryRead>(`/notifications/${deliveryId}`);
  },

  /**
   * Trigger retry for a failed notification delivery (returns 202 Accepted)
   */
  async retryNotification(
    deliveryId: string,
    payload?: NotificationRetryRequest
  ): Promise<NotificationRetryResponse> {
    return apiPost<NotificationRetryResponse, NotificationRetryRequest>(
      `/notifications/${deliveryId}/retry`,
      payload ?? { force: false }
    );
  },
};
