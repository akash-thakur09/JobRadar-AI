import { apiGet } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { NotificationDelivery, NotificationFilterParams } from "@/types/notifications";

export const notificationsService = {
  /**
   * List notification delivery records
   */
  async listNotifications(params?: NotificationFilterParams): Promise<PaginatedResponse<NotificationDelivery>> {
    return apiGet<PaginatedResponse<NotificationDelivery>>("/notifications", { params });
  },

  /**
   * Fetch notification delivery details by ID
   */
  async getNotification(deliveryId: string): Promise<NotificationDelivery> {
    return apiGet<NotificationDelivery>(`/notifications/${deliveryId}`);
  },
};

