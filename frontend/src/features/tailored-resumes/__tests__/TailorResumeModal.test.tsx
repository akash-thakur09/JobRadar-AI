import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TailorResumeModal } from "../components/TailorResumeModal";
import { resumesService } from "@/services/resumes.service";
import { matchesService } from "@/services/matches.service";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import type { MasterResumeSummary } from "@/types/resumes";
import type { JobMatchDetail } from "@/types/matches";
import type { TailoredResumeSummary } from "@/types/tailored-resumes";

const mockResumes: MasterResumeSummary[] = [
  {
    id: "resume-001",
    candidate_profile_id: "profile-123",
    original_filename: "Alex_Chen_Principal_Engineer.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 145000,
    checksum_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    is_active: true,
    created_at: "2026-11-10T10:00:00Z",
    updated_at: "2026-11-10T10:00:00Z",
    latest_version: {
      id: "ver-001",
      version_number: 1,
      is_valid: true,
      processing_status: "COMPLETED",
      created_at: "2026-11-10T10:00:00Z",
    },
  },
];

const mockMatchQualified: JobMatchDetail = {
  id: "match-001",
  job_id: "job-001",
  candidate_profile_id: "profile-123",
  job_title: "Staff Systems Engineer",
  company_name: "Stripe",
  normalized_location: "Remote",
  workplace_type: "REMOTE",
  eligibility_status: "ELIGIBLE",
  semantic_analysis_status: "COMPLETED",
  deterministic_score: 85,
  semantic_score: 90,
  final_score: 88,
  skill_score: 85,
  experience_score: 85,
  title_score: 90,
  preference_score: 90,
  match_explanation: "Strong match for distributed systems experience",
  is_qualified: true,
  created_at: "2026-11-10T10:00:00Z",
  updated_at: "2026-11-10T10:00:00Z",
  match_explanation_details: {
    is_qualified: true,
  },
};

const mockTailoredSummary: TailoredResumeSummary = {
  id: "tailored-001",
  candidate_profile_id: "profile-123",
  job_id: "job-001",
  job_match_id: "match-001",
  resume_version_id: "ver-001",
  rendering_strategy: "PRESERVED",
  generation_status: "PROCESSING",
  generation_attempts: 1,
  created_at: "2026-11-16T12:00:00Z",
  updated_at: "2026-11-16T12:00:00Z",
};

describe("TailorResumeModal Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(resumesService, "listResumes").mockResolvedValue({
      items: mockResumes,
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 1,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });

    vi.spyOn(matchesService, "reEvaluateMatch").mockResolvedValue(mockMatchQualified);
    vi.spyOn(tailoredResumesService, "createTailoredResume").mockResolvedValue(mockTailoredSummary);
  });

  const renderModal = (props: Partial<Parameters<typeof TailorResumeModal>[0]> = {}) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <TailorResumeModal
            isOpen={true}
            onClose={vi.fn()}
            jobId="job-001"
            jobTitle="Staff Systems Engineer"
            companyName="Stripe"
            jobMatchId="match-001"
            isQualified={true}
            {...props}
          />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("strictly disables tailoring when position is marked disqualified (isQualified=false)", async () => {
    renderModal({ isQualified: false });

    expect(await screen.findByText("Ineligible for Resume Tailoring")).toBeInTheDocument();
    expect(screen.getByText(/The deterministic matching engine evaluated this position as/i)).toBeInTheDocument();

    const generateBtn = screen.getByRole("button", { name: /Generate Tailored Resume/i });
    expect(generateBtn).toBeDisabled();
  });

  it("allows submission when match is qualified", async () => {
    renderModal({ isQualified: true });

    expect(await screen.findByText("Candidate Profile Qualified for Tailoring")).toBeInTheDocument();

    const generateBtn = screen.getByRole("button", { name: /Generate Tailored Resume/i });
    await waitFor(() => {
      expect(generateBtn).toBeEnabled();
    });

    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(tailoredResumesService.createTailoredResume).toHaveBeenCalledWith({
        job_match_id: "match-001",
        resume_version_id: "ver-001",
        force_regenerate: false,
      });
    });
  });

  it("enables force_regenerate option via checkbox", async () => {
    renderModal({ isQualified: true });

    const checkbox = await screen.findByLabelText(/Force re-generation/i);
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    const generateBtn = screen.getByRole("button", { name: /Generate Tailored Resume/i });
    await waitFor(() => {
      expect(generateBtn).toBeEnabled();
    });

    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(tailoredResumesService.createTailoredResume).toHaveBeenCalledWith({
        job_match_id: "match-001",
        resume_version_id: "ver-001",
        force_regenerate: true,
      });
    });
  });

  it("requires match evaluation if match not yet evaluated", async () => {
    renderModal({ jobMatchId: undefined, isQualified: undefined });

    expect(await screen.findByText("Match Evaluation Required")).toBeInTheDocument();

    const evalBtn = screen.getByRole("button", { name: /Evaluate Match Now/i });
    fireEvent.click(evalBtn);

    await waitFor(() => {
      expect(matchesService.reEvaluateMatch).toHaveBeenCalledWith("job-001", undefined);
    });

    expect(await screen.findByText("Candidate Profile Qualified for Tailoring")).toBeInTheDocument();
  });
});
