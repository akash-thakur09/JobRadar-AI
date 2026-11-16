/**
 * System Liveness and Infrastructure Readiness types
 */

export interface LivenessResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  environment: string;
  version: string;
}

export interface ReadinessResponse {
  status: "healthy" | "unhealthy";
  timestamp: string;
  components: {
    database: string;
    redis: string;
    ollama?: string;
    [key: string]: string | undefined;
  };
}

