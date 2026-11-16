import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useJobs, useJob } from "../useJobs";
import { useMatches, useMatch } from "../useMatches";
import { jobsService } from "@/services/jobs.service";
import { matchesService } from "@/services/matches.service";
import type { PaginatedResponse } from "@/types/api";
import type { JobSummary, JobDetail } from "@/types/jobs";
import type { JobMatchSummary, JobMatchDetail } from "@/types/matches";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useJobs and useMatches hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("useJobs fetches paginated jobs from jobsService", async () => {
    const mockJobsResponse: PaginatedResponse<JobSummary> = {
      items: [
        {
          id: "j-1",
          canonical_company_name: "TechCorp",
          title: "Senior Backend Engineer",
          canonical_application_url: "https://example.com/apply",
          workplace_type: "REMOTE",
          normalized_location: "Remote",
          employment_type: "FULL_TIME",
          posted_at: "2026-11-10T00:00:00Z",
          first_seen_at: "2026-11-10T00:00:00Z",
          last_seen_at: "2026-11-10T00:00:00Z",
          status: "ACTIVE",
          created_at: "2026-11-10T00:00:00Z",
        },
      ],
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    };

    const spy = vi.spyOn(jobsService, "listJobs").mockResolvedValue(mockJobsResponse);

    const { result } = renderHook(() => useJobs({ page: 1, page_size: 10 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(spy).toHaveBeenCalledWith({ page: 1, page_size: 10 });
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]?.title).toBe("Senior Backend Engineer");
  });

  it("useJob fetches single job detail", async () => {
    const mockJobDetail: JobDetail = {
      id: "j-1",
      canonical_company_name: "TechCorp",
      title: "Senior Backend Engineer",
      canonical_application_url: "https://example.com/apply",
      workplace_type: "REMOTE",
      normalized_location: "Remote",
      employment_type: "FULL_TIME",
      description_text: "Full job description text",
      dedup_fingerprint_sha256: "abc123sha",
      source_count: 1,
      sources: [],
      posted_at: "2026-11-10T00:00:00Z",
      first_seen_at: "2026-11-10T00:00:00Z",
      last_seen_at: "2026-11-10T00:00:00Z",
      status: "ACTIVE",
      created_at: "2026-11-10T00:00:00Z",
    };

    const spy = vi.spyOn(jobsService, "getJob").mockResolvedValue(mockJobDetail);

    const { result } = renderHook(() => useJob("j-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(spy).toHaveBeenCalledWith("j-1");
    expect(result.current.data?.title).toBe("Senior Backend Engineer");
  });

  it("useMatches fetches paginated matches from matchesService", async () => {
    const mockMatchesResponse: PaginatedResponse<JobMatchSummary> = {
      items: [
        {
          id: "m-1",
          job_id: "j-1",
          candidate_profile_id: "c-1",
          eligibility_status: "ELIGIBLE",
          semantic_analysis_status: "COMPLETED",
          deterministic_score: 85,
          semantic_score: 90,
          final_score: 88,
          skill_score: 90,
          experience_score: 80,
          title_score: 95,
          preference_score: 85,
          match_explanation: "High alignment with requirements.",
          is_qualified: true,
          created_at: "2026-11-12T00:00:00Z",
          updated_at: "2026-11-12T00:00:00Z",
          job_title: "Senior Backend Engineer",
          company_name: "TechCorp",
          workplace_type: "REMOTE",
          normalized_location: "Remote",
        },
      ],
      pagination: {
        page: 1,
        page_size: 5,
        total_items: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    };

    const spy = vi.spyOn(matchesService, "listMatches").mockResolvedValue(mockMatchesResponse);

    const { result } = renderHook(() => useMatches({ page_size: 5 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(spy).toHaveBeenCalledWith({ page_size: 5 });
    expect(result.current.data?.items).toHaveLength(1);
    expect(result.current.data?.items[0]?.final_score).toBe(88);
  });

  it("useMatch fetches single match detail", async () => {
    const mockMatchDetail: JobMatchDetail = {
      id: "m-1",
      job_id: "j-1",
      candidate_profile_id: "c-1",
      eligibility_status: "ELIGIBLE",
      semantic_analysis_status: "COMPLETED",
      deterministic_score: 85,
      semantic_score: 90,
      final_score: 88,
      skill_score: 90,
      experience_score: 80,
      title_score: 95,
      preference_score: 85,
      match_explanation: "High alignment with requirements.",
      match_explanation_details: { matched_skills: ["Python", "FastAPI"] },
      is_qualified: true,
      created_at: "2026-11-12T00:00:00Z",
      updated_at: "2026-11-12T00:00:00Z",
      job_title: "Senior Backend Engineer",
      company_name: "TechCorp",
      workplace_type: "REMOTE",
      normalized_location: "Remote",
    };

    const spy = vi.spyOn(matchesService, "getMatch").mockResolvedValue(mockMatchDetail);

    const { result } = renderHook(() => useMatch("m-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(spy).toHaveBeenCalledWith("m-1");
    expect(result.current.data?.final_score).toBe(88);
  });
});
