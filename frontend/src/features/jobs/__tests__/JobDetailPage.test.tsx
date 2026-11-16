import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobDetailPage } from "../pages/JobDetailPage";
import { jobsService } from "@/services/jobs.service";
import { matchesService } from "@/services/matches.service";
import type { JobDetail } from "@/types/jobs";

const mockJobDetail: JobDetail = {
  id: "job-100",
  canonical_company_name: "Airbnb",
  title: "Principal Distributed Systems Engineer",
  canonical_application_url: "https://careers.airbnb.com/positions/100",
  workplace_type: "REMOTE",
  normalized_location: "San Francisco, CA",
  employment_type: "FULL_TIME",
  posted_at: "2026-11-14T10:00:00Z",
  first_seen_at: "2026-11-14T10:00:00Z",
  last_seen_at: "2026-11-16T10:00:00Z",
  status: "ACTIVE",
  description_text: "We are seeking a Principal Engineer to scale our distributed database infrastructure.",
  dedup_fingerprint_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  source_count: 1,
  created_at: "2026-11-14T10:00:00Z",
  sources: [
    {
      id: "src-1",
      job_id: "job-100",
      job_source_id: "src-board-1",
      external_job_id: "gh-100",
      source_job_url: "https://boards.greenhouse.io/airbnb/jobs/100",
      raw_payload: {},
      raw_posted_at: "2026-11-14T10:00:00Z",
      payload_hash_sha256: "hash-123",
      processing_status: "PROCESSED",
      processing_error: null,
      first_seen_at: "2026-11-14T10:00:00Z",
      last_seen_at: "2026-11-16T10:00:00Z",
      created_at: "2026-11-14T10:00:00Z",
    },
  ],
};

describe("JobDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(jobsService, "getJob").mockResolvedValue(mockJobDetail);
    vi.spyOn(jobsService, "getJobSources").mockResolvedValue(mockJobDetail.sources || []);
    vi.spyOn(matchesService, "reEvaluateMatch").mockResolvedValue({
      id: "match-999",
      job_id: "job-100",
      candidate_profile_id: "c-123",
      eligibility_status: "ELIGIBLE",
      semantic_analysis_status: "PENDING",
      deterministic_score: 85,
      semantic_score: null,
      final_score: 85,
      skill_score: 90,
      experience_score: 80,
      title_score: 85,
      preference_score: 85,
      match_explanation: "Eligible candidate with matching experience.",
      is_qualified: true,
      created_at: "2026-11-16T12:00:00Z",
      updated_at: "2026-11-16T12:00:00Z",
      job_title: "Principal Distributed Systems Engineer",
      company_name: "Airbnb",
      workplace_type: "REMOTE",
      normalized_location: "San Francisco, CA",
      match_explanation_details: {},
    });
  });

  const renderDetailPage = (jobId = "job-100") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/jobs/${jobId}`]}>
          <Routes>
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders canonical job details with company, title, and workplace badge", async () => {
    renderDetailPage();

    expect(await screen.findByText("Principal Distributed Systems Engineer")).toBeInTheDocument();
    expect(screen.getByText("Airbnb")).toBeInTheDocument();
    expect(screen.getByText("San Francisco, CA")).toBeInTheDocument();
    expect(screen.getByText("REMOTE")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText(/We are seeking a Principal Engineer/i)).toBeInTheDocument();
  });

  it("renders external apply link with safe target and rel attributes", async () => {
    renderDetailPage();

    await screen.findByText("Principal Distributed Systems Engineer");
    const applyLink = screen.getByRole("link", { name: /Apply on Company Site/i });
    expect(applyLink).toBeInTheDocument();
    expect(applyLink).toHaveAttribute("href", "https://careers.airbnb.com/positions/100");
    expect(applyLink).toHaveAttribute("target", "_blank");
    expect(applyLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders sources provenance and deduplication fingerprint", async () => {
    renderDetailPage();

    expect(await screen.findByText(/Discovery Provenance & Ingestion Audit/i)).toBeInTheDocument();
    expect(screen.getByText("PROCESSED")).toBeInTheDocument();
    expect(screen.getByText("gh-100")).toBeInTheDocument();
    expect(
      screen.getByText("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    ).toBeInTheDocument();
  });

  it("triggers match evaluation on 'Evaluate Match' button click", async () => {
    renderDetailPage();

    const evaluateBtn = await screen.findByRole("button", { name: /Evaluate Match/i });
    fireEvent.click(evaluateBtn);

    await waitFor(() => {
      expect(matchesService.reEvaluateMatch).toHaveBeenCalledWith("job-100", undefined);
    });
  });

  it("displays error state when job is not found", async () => {
    vi.spyOn(jobsService, "getJob").mockRejectedValueOnce(new Error("Job not found"));

    renderDetailPage("invalid-job-id");

    expect(await screen.findByText("Job Not Found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to Job Discovery/i })).toBeInTheDocument();
  });
});
