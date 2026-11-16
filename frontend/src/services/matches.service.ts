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
   * Fetch match details by ID
   */
  async getMatch(matchId: string): Promise<JobMatchDetail> {
    return apiGet<JobMatchDetail>(`/matches/${matchId}`);
  },

  /**
   * Re-evaluate match for a job on demand
   */
  async reEvaluateMatch(jobId: string, candidateProfileId?: string): Promise<JobMatchDetail> {
    return apiPost<JobMatchDetail>(`/matches/${jobId}/re-evaluate`, undefined, {
      params: candidateProfileId ? { candidate_profile_id: candidateProfileId } : undefined,
    });
  },
};
