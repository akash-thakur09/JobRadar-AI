import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DashboardPage } from "../pages/DashboardPage";
import { candidateService } from "@/services/candidate.service";
import { jobsService } from "@/services/jobs.service";
import { matchesService } from "@/services/matches.service";
import { pipelineService } from "@/services/pipeline.service";
import { healthService } from "@/services/health.service";
import type { CandidateProfile, CandidatePreferences, CandidateSkill } from "@/types/candidate";
import type { JobSummary } from "@/types/jobs";
import type { JobMatchSummary } from "@/types/matches";
import type { PipelineRunSummary } from "@/types/pipeline";

const mockProfile: CandidateProfile = {
  id: "c-123",
  user_id: "u-456",
  full_name: "Jane Developer",
  headline: "Senior Cloud Engineer",
  professional_summary: "Over 8 years experience building distributed microservices.",
  current_role: "Staff Backend Engineer",
  total_experience_months: 96,
  city: "Seattle",
  country: "United States",
  work_authorization: "US Citizen",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-05T12:00:00Z",
};

const mockPreferences: CandidatePreferences = {
  id: "pref-123",
  candidate_profile_id: "c-123",
  minimum_relevance_score: 75,
  preferred_titles: ["Staff Engineer", "Backend Architect"],
  preferred_workplace_types: ["REMOTE", "HYBRID"],
  preferred_locations: ["Seattle", "Remote"],
  preferred_employment_types: ["FULL_TIME"],
  max_job_age_days: 30,
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-05T12:00:00Z",
};

const mockSkills: CandidateSkill[] = [
  {
    id: "sk-1",
    candidate_profile_id: "c-123",
    skill_name: "python",
    category: "backend",
    experience_months: 72,
    is_core: true,
    created_at: "2026-11-01T10:00:00Z",
  },
  {
    id: "sk-2",
    candidate_profile_id: "c-123",
    skill_name: "postgresql",
    category: "database",
    experience_months: 60,
    is_core: false,
    created_at: "2026-11-01T10:00:00Z",
  },
];

const mockJobs: JobSummary[] = [
  {
    id: "job-1",
    canonical_company_name: "Acme Cloud",
    title: "Senior Python Architect",
    canonical_application_url: "https://acme.com/apply/1",
    workplace_type: "REMOTE",
    normalized_location: "Remote - US",
    employment_type: "FULL_TIME",
    posted_at: "2026-11-15T10:00:00Z",
    first_seen_at: "2026-11-15T10:00:00Z",
    last_seen_at: "2026-11-15T10:00:00Z",
    status: "ACTIVE",
    created_at: "2026-11-15T10:00:00Z",
  },
];

const mockMatches: JobMatchSummary[] = [
  {
    id: "match-1",
    job_id: "job-1",
    candidate_profile_id: "c-123",
    eligibility_status: "ELIGIBLE",
    semantic_analysis_status: "COMPLETED",
    deterministic_score: 88,
    semantic_score: 92,
    final_score: 90,
    skill_score: 95,
    experience_score: 85,
    title_score: 90,
    preference_score: 90,
    match_explanation: "Strong match on async Python and distributed backend requirements.",
    is_qualified: true,
    created_at: "2026-11-15T11:00:00Z",
    updated_at: "2026-11-15T11:00:00Z",
    job_title: "Senior Python Architect",
    company_name: "Acme Cloud",
    workplace_type: "REMOTE",
    normalized_location: "Remote - US",
  },
];

const mockRuns: PipelineRunSummary[] = [
  {
    id: "run-1234-5678-9999",
    candidate_profile_id: "c-123",
    trigger_type: "MANUAL",
    status: "COMPLETED",
    started_at: "2026-11-15T10:00:00Z",
    completed_at: "2026-11-15T10:02:00Z",
    created_at: "2026-11-15T09:59:00Z",
    updated_at: "2026-11-15T10:02:00Z",
    jobs_discovered: 12,
    matches_qualified: 4,
    resumes_generated: 4,
    notifications_sent: 4,
    error_summary: null,
  },
];

describe("DashboardPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(candidateService, "getProfile").mockResolvedValue(mockProfile);
    vi.spyOn(candidateService, "getPreferences").mockResolvedValue(mockPreferences);
    vi.spyOn(candidateService, "listSkills").mockResolvedValue(mockSkills);

    vi.spyOn(jobsService, "listJobs").mockResolvedValue({
      items: mockJobs,
      pagination: {
        page: 1,
        page_size: 5,
        total_items: 42,
        total_pages: 9,
        has_next: true,
        has_prev: false,
      },
    });

    vi.spyOn(matchesService, "listMatches").mockResolvedValue({
      items: mockMatches,
      pagination: {
        page: 1,
        page_size: 5,
        total_items: 18,
        total_pages: 4,
        has_next: true,
        has_prev: false,
      },
    });

    vi.spyOn(pipelineService, "listPipelineRuns").mockResolvedValue({
      items: mockRuns,
      pagination: {
        page: 1,
        page_size: 5,
        total_items: 7,
        total_pages: 2,
        has_next: false,
        has_prev: false,
      },
    });

    vi.spyOn(healthService, "checkReadiness").mockResolvedValue({
      status: "healthy",
      timestamp: "2026-11-16T10:00:00Z",
      components: {
        database: "connected",
        redis: "connected",
        ollama: "connected (llama3.1:8b)",
      },
    });

    vi.spyOn(healthService, "checkLiveness").mockResolvedValue({
      status: "alive",
      timestamp: "2026-11-16T10:00:00Z",
      version: "1.0.0",
      environment: "test",
    });
  });

  const renderDashboard = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <DashboardPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

  it("renders personalized greeting with candidate name", async () => {
    renderDashboard();

    expect(await screen.findByText(/Jane Developer/i)).toBeInTheDocument();
    expect(screen.getByText("Intelligence Dashboard")).toBeInTheDocument();
  });

  it("displays real metrics from backend API envelopes", async () => {
    renderDashboard();

    // 42 total jobs
    expect(await screen.findByText("42")).toBeInTheDocument();
    // 18 total evaluated matches
    expect(screen.getByText("18")).toBeInTheDocument();
    // 7 total pipeline runs
    expect(screen.getByText("7")).toBeInTheDocument();
    // Profile readiness percentage computed from criteria
    expect(screen.getByText(/complete/i)).toBeInTheDocument();
  });

  it("renders recently discovered jobs and evaluated matches", async () => {
    renderDashboard();

    // Discovered Job
    expect(await screen.findByText("Senior Python Architect")).toBeInTheDocument();
    expect(screen.getByText("Acme Cloud")).toBeInTheDocument();
    expect(screen.getByText("Remote - US")).toBeInTheDocument();

    // Evaluated Match with score
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("Eligible")).toBeInTheDocument();
  });

  it("opens trigger run modal on Trigger Run button click", async () => {
    renderDashboard();

    const triggerButtons = await screen.findAllByRole("button", { name: /Trigger Run/i });
    fireEvent.click(triggerButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Start Pipeline Run")).toBeInTheDocument();
      expect(screen.getByText("Orchestrated Lifecycle:")).toBeInTheDocument();
    });
  });
});

