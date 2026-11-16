import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResumeDetailPage } from "../pages/ResumeDetailPage";
import { resumesService } from "@/services/resumes.service";
import type { MasterResumeDetailResponse } from "@/types/resumes";

const mockResumeDetail: MasterResumeDetailResponse = {
  id: "resume-001",
  candidate_profile_id: "profile-123",
  original_filename: "Alex_Chen_Principal_Engineer.pdf",
  mime_type: "application/pdf",
  file_size_bytes: 145000,
  checksum_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  storage_key: "resumes/profile-123/resume-001.pdf",
  is_active: true,
  created_at: "2026-11-10T10:00:00Z",
  updated_at: "2026-11-10T10:00:00Z",
  active_version: {
    id: "ver-001",
    master_resume_id: "resume-001",
    version_number: 1,
    checksum_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    is_valid: true,
    processing_status: "COMPLETED",
    parsing_error: null,
    structured_content: {
      contact_info: {
        email: "alex.chen@example.com",
        phone: "+1-555-0199",
        linkedin: "linkedin.com/in/alexchen",
        github: "github.com/alexchen",
        location: "San Francisco, CA",
      },
      summary: "Principal distributed systems architect with 12+ years of experience building resilient microservices.",
      skills: ["Rust", "Python", "Kubernetes", "PostgreSQL", "Kafka", "Distributed Systems"],
      experience: [
        {
          role: "Staff Infrastructure Architect",
          company: "CloudTech",
          location: "San Francisco, CA",
          start_date: "2021",
          end_date: "Present",
          bullet_points: [
            "Architected multi-region event stream handling 2M ops/sec with 99.999% availability.",
            "Reduced p99 tail latency by 45% via custom epoll IO pooling.",
          ],
        },
      ],
      education: [
        {
          institution: "University of California, Berkeley",
          degree: "B.S. in Computer Science",
          field_of_study: "Computer Science",
          graduation_date: "2014",
        },
      ],
      projects: [
        {
          name: "Raft Consensus Engine",
          description: "Production-grade Raft consensus algorithm in Rust.",
          technologies: ["Rust", "Tokio", "gRPC"],
          link: "https://github.com/alexchen/raft-engine",
        },
      ],
      certifications: ["AWS Certified Solutions Architect - Professional"],
      raw_text: "ALEX CHEN\nalex.chen@example.com\nPrincipal Distributed Systems Architect...",
    },
    created_at: "2026-11-10T10:00:00Z",
  },
  versions: [
    {
      id: "ver-001",
      version_number: 1,
      is_valid: true,
      processing_status: "COMPLETED",
      created_at: "2026-11-10T10:00:00Z",
    },
  ],
};

describe("ResumeDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(resumesService, "getResume").mockResolvedValue(mockResumeDetail);
    vi.spyOn(resumesService, "getResumeContent").mockResolvedValue(mockResumeDetail.active_version!.structured_content);
    vi.spyOn(resumesService, "listResumeVersions").mockResolvedValue([mockResumeDetail.active_version!]);
  });

  const renderPage = (resumeId = "resume-001") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/resumes/${resumeId}`]}>
          <Routes>
            <Route path="/resumes/:resumeId" element={<ResumeDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders master resume metadata, filename, storage key, and active badge", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Alex_Chen_Principal_Engineer.pdf", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("resumes/profile-123/resume-001.pdf")).toBeInTheDocument();
    expect(screen.getByText(/ACTIVE MASTER RESUME/i)).toBeInTheDocument();
    expect((await screen.findAllByText("COMPLETED")).length).toBeGreaterThanOrEqual(1);
  });

  it("displays parsed structured sections: contact info and professional summary", async () => {
    renderPage();

    expect(await screen.findByText("alex.chen@example.com")).toBeInTheDocument();
    expect(screen.getByText("+1-555-0199")).toBeInTheDocument();
    expect(screen.getByText(/Principal distributed systems architect with 12\+ years/i)).toBeInTheDocument();
  });

  it("switches tabs to inspect parsed technical skills", async () => {
    renderPage();

    const skillsTab = await screen.findByRole("button", { name: /Skills/i });
    fireEvent.click(skillsTab);

    expect(await screen.findByText("Parsed Technical Skills (6)")).toBeInTheDocument();
    expect(screen.getByText("Rust")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("Kafka")).toBeInTheDocument();
  });

  it("switches tabs to inspect parsed work experience", async () => {
    renderPage();

    const expTab = await screen.findByRole("button", { name: /Experience/i });
    fireEvent.click(expTab);

    expect(await screen.findByText(/Staff Infrastructure Architect/i)).toBeInTheDocument();
    expect(screen.getByText("CloudTech")).toBeInTheDocument();
    expect(screen.getByText(/Architected multi-region event stream/i)).toBeInTheDocument();
  });

  it("switches tabs to inspect projects and education", async () => {
    renderPage();

    const projEduTab = await screen.findByRole("button", { name: /Projects & Education/i });
    fireEvent.click(projEduTab);

    expect(await screen.findByText("Raft Consensus Engine")).toBeInTheDocument();
    expect(screen.getByText(/University of California, Berkeley/i)).toBeInTheDocument();
    expect(screen.getByText(/AWS Certified Solutions Architect/i)).toBeInTheDocument();
  });

  it("switches tabs to raw text view and renders monospace extracted content", async () => {
    renderPage();

    const rawTab = await screen.findByRole("button", { name: /Raw Text/i });
    fireEvent.click(rawTab);

    expect(await screen.findByText("Extracted Raw Text")).toBeInTheDocument();
    expect(screen.getByText(/ALEX CHEN/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copy Text/i })).toBeInTheDocument();
  });

  it("renders parsing error alert when status is FAILED", async () => {
    const failedResume: MasterResumeDetailResponse = {
      ...mockResumeDetail,
      active_version: {
        ...mockResumeDetail.active_version!,
        processing_status: "FAILED",
        parsing_error: "Corrupted PDF cross-reference table: stream extraction failed.",
      },
    };

    vi.spyOn(resumesService, "getResume").mockResolvedValueOnce(failedResume);

    renderPage();

    expect(await screen.findByText("Resume Parsing Failed")).toBeInTheDocument();
    expect(screen.getByText(/Corrupted PDF cross-reference table/i)).toBeInTheDocument();
  });
});
