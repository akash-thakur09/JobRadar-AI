import { ApiError, apiGet } from "@/lib/api-client";
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
    const result = await apiGet<ReadinessResponse>("/health/ready", {
      validateStatus: (status) => status === 200 || status === 503,
    });
    if (!result?.components || typeof result.components.database !== "string") {
      throw new ApiError("The backend did not return infrastructure status.", 503);
    }
    return result;
  },
};

