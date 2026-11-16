import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TailoredResumesPage } from "../pages/TailoredResumesPage";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import { jobsService } from "@/services/jobs.service";
import type { TailoredResumeSummary } from "@/types/tailored-resumes";
import type { JobDetail } from "@/types/jobs";

const mockTailoredResumes: TailoredResumeSummary[] = [
  {
    id: "tailored-001",
    candidate_profile_id: "profile-123",
    job_id: "job-001",
    job_match_id: "match-001",
    resume_version_id: "ver-001",
    rendering_strategy: "PRESERVED",
    generation_status: "COMPLETED",
    file_name: "Alex_Chen_Stripe_Staff_Backend.pdf",
    file_size_bytes: 185000,
    checksum_sha256: "abc123sha256",
    generation_attempts: 1,
    created_at: "2026-11-14T10:00:00Z",
    updated_at: "2026-11-14T10:02:00Z",
    completed_at: "2026-11-14T10:02:00Z",
  },
  {
    id: "tailored-002",
    candidate_profile_id: "profile-123",
    job_id: "job-002",
    job_match_id: "match-002",
    resume_version_id: "ver-001",
    rendering_strategy: "FALLBACK",
    generation_status: "PROCESSING",
    file_name: null,
    file_size_bytes: null,
    checksum_sha256: null,
    generation_attempts: 1,
    created_at: "2026-11-15T12:00:00Z",
    updated_at: "2026-11-15T12:00:30Z",
    completed_at: null,
  },
];

const mockJob: JobDetail = {
  id: "job-001",
  canonical_company_name: "Stripe",
  title: "Staff Distributed Systems Engineer",
  canonical_application_url: "https://stripe.com/jobs/1",
  workplace_type: "REMOTE",
  normalized_location: "Remote - US",
  employment_type: "FULL_TIME",
  posted_at: "2026-11-10T10:00:00Z",
  first_seen_at: "2026-11-10T10:00:00Z",
  last_seen_at: "2026-11-16T12:00:00Z",
  status: "ACTIVE",
  created_at: "2026-11-10T10:00:00Z",
  description_text: "High throughput distributed systems",
  dedup_fingerprint_sha256: "sha123",
  source_count: 1,
  sources: [],
};

describe("TailoredResumesPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(tailoredResumesService, "listTailoredResumes").mockResolvedValue({
      items: mockTailoredResumes,
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });

    vi.spyOn(jobsService, "getJob").mockResolvedValue(mockJob);

    vi.spyOn(tailoredResumesService, "downloadTailoredPdf").mockResolvedValue({
      data: new Blob(["dummy pdf bytes"], { type: "application/pdf" }),
      filename: "Alex_Chen_Stripe_Staff_Backend.pdf",
    });
  });

  const renderPage = (initialEntries = ["/tailored-resumes"]) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <TailoredResumesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header, KPI summary counts, and tailored resume cards", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Tailored Resumes", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText("PRESERVED")).toBeInTheDocument();
    expect(screen.getByText("FALLBACK")).toBeInTheDocument();
    expect(screen.getByText("Total Tailored")).toBeInTheDocument();
    expect(screen.getByText("ATS Ready")).toBeInTheDocument();
  });

  it("filters items when clicking status filters", async () => {
    renderPage();

    expect(await screen.findByText("PRESERVED")).toBeInTheDocument();

    // Click "Ready" filter
    const readyFilterBtn = screen.getByRole("button", { name: "Ready" });
    fireEvent.click(readyFilterBtn);

    expect(screen.getByText("PRESERVED")).toBeInTheDocument();
    expect(screen.queryByText("FALLBACK")).not.toBeInTheDocument();
  });

  it("renders empty state when no tailored resumes exist", async () => {
    vi.spyOn(tailoredResumesService, "listTailoredResumes").mockResolvedValueOnce({
      items: [],
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 0,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });

    renderPage();

    expect(await screen.findByText("No Tailored Resumes Yet")).toBeInTheDocument();
    expect(screen.getByText("Explore Qualified Matches")).toBeInTheDocument();
  });
});
