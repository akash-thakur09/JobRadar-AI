import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationsService } from "@/services/notifications.service";
import type {
  NotificationFilterParams,
  NotificationRetryRequest,
} from "@/types/notifications";

export const notificationKeys = {
  all: ["notifications"] as const,
  lists: () => [...notificationKeys.all, "list"] as const,
  list: (params?: NotificationFilterParams) => [...notificationKeys.lists(), params] as const,
  details: () => [...notificationKeys.all, "detail"] as const,
  detail: (id: string) => [...notificationKeys.details(), id] as const,
};

export function useNotifications(params?: NotificationFilterParams) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => notificationsService.listNotifications(params),
    refetchInterval: (query) => {
      // Auto-poll every 5s if any notification in the list is PENDING or PROCESSING
      const items = query.state.data?.items;
      const hasActive = items?.some(
        (n) => n.status === "PENDING" || n.status === "PROCESSING"
      );
      return hasActive ? 5000 : false;
    },
  });
}

export function useNotification(notificationId: string) {
  return useQuery({
    queryKey: notificationKeys.detail(notificationId),
    queryFn: () => notificationsService.getNotification(notificationId),
    enabled: Boolean(notificationId),
    refetchInterval: (query) => {
      // Auto-poll while delivery is in flight, stop when terminal (SENT or FAILED)
      const status = query.state.data?.status;
      return status === "PENDING" || status === "PROCESSING" ? 3000 : false;
    },
  });
}

export function useRetryNotification() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      deliveryId,
      payload,
    }: {
      deliveryId: string;
      payload?: NotificationRetryRequest;
    }) => notificationsService.retryNotification(deliveryId, payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: notificationKeys.detail(variables.deliveryId),
      });
    },
  });
}

