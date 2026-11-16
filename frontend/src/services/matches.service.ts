import { apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { JobMatch, MatchFilterParams } from "@/types/matches";

export const matchesService = {
  /**
   * List paginated job matches
   */
  async listMatches(params?: MatchFilterParams): Promise<PaginatedResponse<JobMatch>> {
    return apiGet<PaginatedResponse<JobMatch>>("/matches", { params });
  },

  /**
   * Fetch match details by ID
   */
  async getMatch(matchId: string): Promise<JobMatch> {
    return apiGet<JobMatch>(`/matches/${matchId}`);
  },

  /**
   * Re-evaluate match for a job on demand
   */
  async reEvaluateMatch(jobId: string): Promise<JobMatch> {
    return apiPost<JobMatch>(`/matches/${jobId}/re-evaluate`);
  },

  /**
   * Trigger Layer 3 LLM semantic analysis for a match
   */
  async triggerSemanticAnalysis(matchId: string): Promise<JobMatch> {
    return apiPost<JobMatch>(`/matches/${matchId}/semantic-analysis`);
  },
};

