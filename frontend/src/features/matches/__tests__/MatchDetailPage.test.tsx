import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MatchDetailPage } from "../pages/MatchDetailPage";
import { matchesService } from "@/services/matches.service";
import type { JobMatchDetail } from "@/types/matches";

const mockMatchDetail: JobMatchDetail = {
  id: "match-888",
  job_id: "job-101",
  candidate_profile_id: "c-123",
  eligibility_status: "ELIGIBLE",
  semantic_analysis_status: "COMPLETED",
  deterministic_score: 88,
  semantic_score: 94,
  final_score: 91,
  skill_score: 95,
  experience_score: 85,
  title_score: 90,
  preference_score: 90,
  match_explanation: "Strong deterministic and semantic qualification across all architectural dimensions.",
  is_qualified: true,
  created_at: "2026-11-15T12:00:00Z",
  updated_at: "2026-11-15T12:05:00Z",
  job_title: "Staff Distributed Systems Architect",
  company_name: "Cloudflare",
  workplace_type: "REMOTE",
  normalized_location: "Austin, TX",
  match_explanation_details: {
    is_qualified: true,
    qualification_status: "QUALIFIED",
    eligibility: {
      is_eligible: true,
      status: "ELIGIBLE",
      explanation: "All deterministic hard requirements satisfied (experience, location, work authorization).",
      checks: {
        experience: { passed: true, message: "96 months satisfies >= 60 months required" },
        location: { passed: true, message: "Remote arrangement matches preference" },
        work_auth: { passed: true, message: "US Citizen matches requirements" },
      },
    },
    deterministic_breakdown: {
      total_score: 88,
      skills: {
        score: 38,
        matched_skills: ["Python", "PostgreSQL", "Distributed Systems", "Redis"],
        missing_skills: ["Rust"],
        coverage_ratio: 0.8,
      },
      experience: {
        score: 18,
        candidate_months: 96,
        required_months: 60,
      },
      title: {
        score: 14,
        candidate_title: "Senior Cloud Engineer",
        job_title: "Staff Distributed Systems Architect",
        similarity_ratio: 0.85,
      },
      workplace: {
        score: 10,
        workplace_match: true,
      },
      bonus: {
        score: 8,
        freshness_bonus: 8,
      },
    },
    semantic_evaluation: {
      semantic_score: 94,
      recommendation: "STRONG_MATCH",
      confidence: 0.95,
      reasoning_summary:
        "The candidate has deep demonstrated expertise leading distributed key-value storage designs that directly maps to Cloudflare's core requirements.",
      strengths: [
        {
          claim: "Expertise in high-throughput distributed systems",
          evidence: "Led architecture of distributed caching serving 50M ops/sec",
          job_context: "Requires massive scale streaming pipelines",
        },
      ],
      gaps: [
        {
          gap: "Production Rust experience",
          impact: "LOW",
          mitigation: "Proven capability to ramp quickly on systems programming languages (C++, Go).",
        },
      ],
      transferable_skills: [
        {
          candidate_skill: "Python/Go microservices",
          target_technology: "Rust distributed actors",
          rationale: "Core concurrency primitives and async paradigms transfer directly.",
        },
      ],
    },
  },
  job: {
    id: "job-101",
    canonical_company_name: "Cloudflare",
    title: "Staff Distributed Systems Architect",
    canonical_application_url: "https://cloudflare.com/careers/101",
    workplace_type: "REMOTE",
    normalized_location: "Austin, TX",
    employment_type: "FULL_TIME",
    posted_at: "2026-11-15T10:00:00Z",
    first_seen_at: "2026-11-15T10:00:00Z",
    last_seen_at: "2026-11-16T12:00:00Z",
    status: "ACTIVE",
    created_at: "2026-11-15T10:00:00Z",
  },
};

describe("MatchDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(matchesService, "getMatch").mockResolvedValue(mockMatchDetail);
    vi.spyOn(matchesService, "reEvaluateMatch").mockResolvedValue({
      ...mockMatchDetail,
      deterministic_score: 90,
      final_score: 92,
    });
    vi.spyOn(matchesService, "triggerSemanticAnalysis").mockResolvedValue(mockMatchDetail);
  });

  const renderDetailPage = (matchId = "match-888") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/matches/${matchId}`]}>
          <Routes>
            <Route path="/matches/:matchId" element={<MatchDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders match header with title, company, score badge, and eligibility badge", async () => {
    renderDetailPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Staff Distributed Systems Architect" })
    ).toBeInTheDocument();
    expect(screen.getAllByText("Cloudflare").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Austin, TX").length).toBeGreaterThan(0);
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getAllByText("Eligible").length).toBeGreaterThan(0);
  });

  it("renders Layer 1 deterministic eligibility audit section", async () => {
    renderDetailPage();

    expect(await screen.findByText(/Layer 1: Deterministic Eligibility Audit/i)).toBeInTheDocument();
    expect(
      screen.getByText(/All Mandatory Eligibility Criteria Satisfied/i)
    ).toBeInTheDocument();
  });

  it("renders Layer 2 deterministic scoring breakdown with matched and missing skills", async () => {
    renderDetailPage();

    expect(
      await screen.findByText(/Layer 2: Deterministic Weighted Score Breakdown/i)
    ).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
  });

  it("renders Layer 3 LLM semantic analysis with strengths, gaps, and transferable skills", async () => {
    renderDetailPage();

    expect(
      await screen.findByText(/Layer 3: LLM Semantic Analysis & Contextual Intelligence/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Strong Match Recommendation/i)).toBeInTheDocument();
    expect(screen.getByText(/The candidate has deep demonstrated expertise/i)).toBeInTheDocument();
    expect(screen.getByText("Expertise in high-throughput distributed systems")).toBeInTheDocument();
    expect(screen.getByText("Production Rust experience")).toBeInTheDocument();
    expect(screen.getByText("Python/Go microservices")).toBeInTheDocument();
  });

  it("triggers re-evaluation when 'Re-evaluate' button is clicked", async () => {
    renderDetailPage();

    const reevaluateBtn = await screen.findByRole("button", { name: /Re-evaluate/i });
    fireEvent.click(reevaluateBtn);

    await waitFor(() => {
      expect(matchesService.reEvaluateMatch).toHaveBeenCalledWith("job-101", undefined);
    });
  });

  it("triggers semantic analysis when 'Run Layer 3 Semantic Analysis' button is clicked", async () => {
    vi.spyOn(matchesService, "getMatch").mockResolvedValueOnce({
      ...mockMatchDetail,
      semantic_analysis_status: "PENDING",
      semantic_score: null,
      match_explanation_details: {
        ...mockMatchDetail.match_explanation_details,
        semantic_evaluation: undefined,
      },
    });

    renderDetailPage();

    const runSemanticBtn = await screen.findByRole("button", { name: /Run Layer 3 Semantic Analysis/i });
    fireEvent.click(runSemanticBtn);

    await waitFor(() => {
      expect(matchesService.triggerSemanticAnalysis).toHaveBeenCalledWith("match-888");
    });
  });

  it("renders error state when match is not found", async () => {
    vi.spyOn(matchesService, "getMatch").mockRejectedValueOnce(new Error("Match not found"));

    renderDetailPage("unknown-id");

    expect(await screen.findByText("Match Not Found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to Matches/i })).toBeInTheDocument();
  });
});
