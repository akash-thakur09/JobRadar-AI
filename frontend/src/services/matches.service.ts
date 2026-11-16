import { apiGet, apiPost } from "@/lib/api-client";
import type { PaginatedResponse } from "@/types/api";
import type { JobMatchDetail, JobMatchSummary, MatchFilterParams } from "@/types/matches";

export const matchesService = {
  /**
   * List paginated job matches
   */
  async listMatches(params?: MatchFilterParams): Promise<PaginatedResponse<JobMatchSummary>> {
    return apiGet<PaginatedResponse<JobMatchSummary>>("/matches", { params });
  },

  /**
   * Fetch match details and score breakdown by ID
   */
  async getMatch(matchId: string): Promise<JobMatchDetail> {
    return apiGet<JobMatchDetail>(`/matches/${matchId}`);
  },

  /**
   * Re-evaluate match for a job on demand (Layer 1 & Layer 2)
   */
  async reEvaluateMatch(jobId: string, candidateProfileId?: string): Promise<JobMatchDetail> {
    return apiPost<JobMatchDetail>(`/matches/${jobId}/re-evaluate`, undefined, {
      params: candidateProfileId ? { candidate_profile_id: candidateProfileId } : undefined,
    });
  },

  /**
   * Trigger Layer 3 LLM Semantic Analysis for a qualified match
   */
  async triggerSemanticAnalysis(matchId: string): Promise<JobMatchDetail> {
    return apiPost<JobMatchDetail>(`/matches/${matchId}/semantic-analysis`);
  },
};
