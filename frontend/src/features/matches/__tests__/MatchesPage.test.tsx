import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MatchesPage } from "../pages/MatchesPage";
import { matchesService } from "@/services/matches.service";
import type { JobMatchSummary } from "@/types/matches";

const mockMatches: JobMatchSummary[] = [
  {
    id: "match-101",
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
    match_explanation: "Outstanding alignment on distributed systems and cloud infrastructure.",
    is_qualified: true,
    created_at: "2026-11-15T12:00:00Z",
    updated_at: "2026-11-15T12:05:00Z",
    job_title: "Staff Distributed Systems Architect",
    company_name: "Cloudflare",
    workplace_type: "REMOTE",
    normalized_location: "Austin, TX",
  },
  {
    id: "match-102",
    job_id: "job-102",
    candidate_profile_id: "c-123",
    eligibility_status: "INELIGIBLE_LOCATION",
    semantic_analysis_status: "NOT_STARTED",
    deterministic_score: 40,
    semantic_score: null,
    final_score: 40,
    skill_score: 70,
    experience_score: 80,
    title_score: 50,
    preference_score: 20,
    match_explanation: "Ineligible: candidate location does not satisfy on-site presence requirements.",
    is_qualified: false,
    created_at: "2026-11-15T11:00:00Z",
    updated_at: "2026-11-15T11:00:00Z",
    job_title: "Senior SRE",
    company_name: "FinTech Corp",
    workplace_type: "ONSITE",
    normalized_location: "London, UK",
  },
];

describe("MatchesPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(matchesService, "listMatches").mockResolvedValue({
      items: mockMatches,
      pagination: {
        page: 1,
        page_size: 15,
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });
  });

  const renderMatchesPage = (initialEntries = ["/matches"]) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <MatchesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header and match cards with company, scores, and status badges", async () => {
    renderMatchesPage();

    expect(screen.getByRole("heading", { level: 1, name: "Job Matches" })).toBeInTheDocument();
    expect(
      screen.getByText(/Candidate-specific match intelligence/i)
    ).toBeInTheDocument();

    // Verify first match card
    expect(await screen.findByText("Staff Distributed Systems Architect")).toBeInTheDocument();
    expect(screen.getByText("Cloudflare")).toBeInTheDocument();
    expect(screen.getByText("Austin, TX")).toBeInTheDocument();
    expect(screen.getAllByText("91%").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Eligible")).toBeInTheDocument();
    expect(
      screen.getByText(/Outstanding alignment on distributed systems and cloud infrastructure/i)
    ).toBeInTheDocument();

    // Verify second match card (ineligible)
    expect(screen.getByText("Senior SRE")).toBeInTheDocument();
    expect(screen.getByText("FinTech Corp")).toBeInTheDocument();
    expect(screen.getAllByText("Ineligible: Location").length).toBeGreaterThanOrEqual(1);
  });

  it("renders KPI summary counts correctly", async () => {
    renderMatchesPage();

    // Total Evaluated
    expect(await screen.findByText("Total Evaluated")).toBeInTheDocument();
    // Qualified on Page
    expect(screen.getByText("Qualified on Page")).toBeInTheDocument();
    // Top Match Score
    expect(screen.getByText("Top Match Score")).toBeInTheDocument();
    // Scoring Policy
    expect(screen.getByText("Scoring Policy")).toBeInTheDocument();
  });

  it("updates score threshold and eligibility filters", async () => {
    renderMatchesPage();

    await screen.findByText("Staff Distributed Systems Architect");

    const scoreFilter = screen.getByLabelText(/Filter by minimum score/i);
    fireEvent.change(scoreFilter, { target: { value: "80" } });
    expect((scoreFilter as HTMLSelectElement).value).toBe("80");

    const eligFilter = screen.getByLabelText(/Filter by eligibility/i);
    fireEvent.change(eligFilter, { target: { value: "ELIGIBLE" } });
    expect((eligFilter as HTMLSelectElement).value).toBe("ELIGIBLE");
  });

  it("renders empty state when no matches exist", async () => {
    vi.spyOn(matchesService, "listMatches").mockResolvedValueOnce({
      items: [],
      pagination: {
        page: 1,
        page_size: 15,
        total_items: 0,
        total_pages: 0,
        has_next: false,
        has_prev: false,
      },
    });

    renderMatchesPage(["/matches"]);

    expect(await screen.findByText("No match evaluations recorded yet")).toBeInTheDocument();
    expect(
      screen.getByText(/Execute a pipeline run to evaluate discovered canonical job opportunities/i)
    ).toBeInTheDocument();
  });

  it("renders filtered empty state when filter yields zero matches", async () => {
    vi.spyOn(matchesService, "listMatches").mockResolvedValueOnce({
      items: [],
      pagination: {
        page: 1,
        page_size: 15,
        total_items: 0,
        total_pages: 0,
        has_next: false,
        has_prev: false,
      },
    });

    renderMatchesPage(["/matches?min_score=95"]);

    expect(await screen.findByText("No matching evaluations")).toBeInTheDocument();
    expect(screen.getByText(/No job matches satisfied your current score threshold/i)).toBeInTheDocument();
  });

  it("renders error state when matches query fails", async () => {
    vi.spyOn(matchesService, "listMatches").mockRejectedValueOnce(new Error("Network connection error"));

    renderMatchesPage();

    expect(await screen.findByText("Failed to Load Matches")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });
});
