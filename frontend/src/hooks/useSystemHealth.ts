import { useQuery } from "@tanstack/react-query";
import { healthService } from "@/services/health.service";

export const healthKeys = {
  all: ["health"] as const,
  liveness: () => [...healthKeys.all, "liveness"] as const,
  readiness: () => [...healthKeys.all, "readiness"] as const,
};

export function useSystemLiveness() {
  return useQuery({
    queryKey: healthKeys.liveness(),
    queryFn: () => healthService.getLiveness(),
    refetchInterval: 30000, // poll liveness every 30s
  });
}

export function useSystemReadiness() {
  return useQuery({
    queryKey: healthKeys.readiness(),
    queryFn: () => healthService.getReadiness(),
    refetchInterval: 15000, // poll readiness every 15s
  });
}

