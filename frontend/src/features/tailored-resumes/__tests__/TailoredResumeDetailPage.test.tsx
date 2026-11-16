import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TailoredResumeDetailPage } from "../pages/TailoredResumeDetailPage";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import { jobsService } from "@/services/jobs.service";
import type { TailoredResumeDetail } from "@/types/tailored-resumes";
import type { JobDetail } from "@/types/jobs";

const mockTailoredDetail: TailoredResumeDetail = {
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
  tailored_content: {
    headline: "Staff Distributed Systems & Infrastructure Architect",
    professional_summary: "Distributed systems architect with deep expertise in high-throughput streaming systems, consensus engines, and event-driven architecture.",
    skills: ["Rust", "Python", "Kafka", "Distributed Systems", "Kubernetes"],
    experience: [
      {
        company: "CloudTech",
        title: "Staff Infrastructure Architect",
        location: "San Francisco, CA",
        start_date: "2021",
        end_date: "Present",
        bullet_points: [
          "Scaled distributed streaming infrastructure to 2M ops/sec with strict zero-loss consistency.",
          "Engineered resilient multi-datacenter data replication pipeline using custom Rust RPC engines.",
        ],
      },
    ],
    tailoring_notes: "Prioritized distributed consensus, high-throughput streaming, and low-latency storage based on Stripe staff job specifications.",
  },
  validation_metadata: {
    is_valid: true,
    supported_skills: ["Rust", "Python", "Kafka", "Distributed Systems"],
    unsupported_skills: [],
    supported_metrics: ["2M ops/sec", "99.999% availability"],
    repaired_claims: ["Sanitized throughput claim to mirror verified candidate profile evidence."],
    violations_detected: [],
  },
  validation_error: null,
};

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

describe("TailoredResumeDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(tailoredResumesService, "getTailoredResume").mockResolvedValue(mockTailoredDetail);
    vi.spyOn(jobsService, "getJob").mockResolvedValue(mockJob);
    vi.spyOn(tailoredResumesService, "createTailoredResume").mockResolvedValue(mockTailoredDetail);
    vi.spyOn(tailoredResumesService, "downloadTailoredPdf").mockResolvedValue({
      data: new Blob(["dummy pdf bytes"], { type: "application/pdf" }),
      filename: "Alex_Chen_Stripe_Staff_Backend.pdf",
    });
  });

  const renderPage = (id = "tailored-001") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/tailored-resumes/${id}`]}>
          <Routes>
            <Route path="/tailored-resumes/:tailoredResumeId" element={<TailoredResumeDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders target job title, company name, strategy badge, and ready status", async () => {
    renderPage();

    expect(await screen.findByText("Preserved Template")).toBeInTheDocument();
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();

    await waitFor(
      () => {
        expect(screen.getByRole("heading", { name: "Staff Distributed Systems Engineer", level: 1 })).toBeInTheDocument();
        expect(screen.getByText("Stripe")).toBeInTheDocument();
      },
      { timeout: 4000 }
    );
  });

  it("switches to Claim Validation & Audit tab to verify evidence checks", async () => {
    renderPage();

    const validationTab = await screen.findByRole("button", { name: /Claim Validation & Audit/i });
    fireEvent.click(validationTab);

    expect(await screen.findByText(/Truthful Claim Validation & Audit Trail/i)).toBeInTheDocument();
    expect(screen.getByText("Audit Passed")).toBeInTheDocument();
    expect(screen.getByText(/Verified Supported Skills \(4\)/i)).toBeInTheDocument();
    expect(screen.getByText("2M ops/sec")).toBeInTheDocument();
    expect(screen.getByText(/Sanitized throughput claim to mirror verified candidate profile evidence/i)).toBeInTheDocument();
  });

  it("switches to Tailored Content Structure tab to inspect aligned bullets and notes", async () => {
    renderPage();

    const contentTab = await screen.findByRole("button", { name: /Tailored Content Structure/i });
    fireEvent.click(contentTab);

    expect(await screen.findByText("Staff Distributed Systems & Infrastructure Architect")).toBeInTheDocument();
    expect(screen.getByText(/Scaled distributed streaming infrastructure to 2M ops\/sec/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritized distributed consensus, high-throughput streaming/i)).toBeInTheDocument();
  });

  it("renders live processing alert when generation is still running", async () => {
    const processingResume: TailoredResumeDetail = {
      ...mockTailoredDetail,
      generation_status: "RENDERING",
    };

    vi.spyOn(tailoredResumesService, "getTailoredResume").mockResolvedValueOnce(processingResume);

    renderPage();

    expect(await screen.findByText("Generation in Progress")).toBeInTheDocument();
    expect(screen.getByText(/The truthful tailoring and PDF rendering pipeline is actively running/i)).toBeInTheDocument();
  });

  it("triggers force regeneration when button is clicked", async () => {
    renderPage();

    const regenBtn = await screen.findByRole("button", { name: /Force Regenerate/i });
    fireEvent.click(regenBtn);

    await waitFor(() => {
      expect(tailoredResumesService.createTailoredResume).toHaveBeenCalledWith({
        job_match_id: "match-001",
        resume_version_id: "ver-001",
        force_regenerate: true,
      });
    });
  });
});
