import { apiGet } from "@/lib/api-client";
import type { LivenessResponse, ReadinessResponse } from "@/types/health";

export const healthService = {
  /**
   * Application liveness probe
   */
  async getLiveness(): Promise<LivenessResponse> {
    return apiGet<LivenessResponse>("/health/live");
  },

  /**
   * Deep infrastructure readiness probe (Database, Redis, Ollama)
   */
  async getReadiness(): Promise<ReadinessResponse> {
    return apiGet<ReadinessResponse>("/health/ready");
  },
};

