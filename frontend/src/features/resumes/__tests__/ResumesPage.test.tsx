import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResumesPage } from "../pages/ResumesPage";
import { resumesService } from "@/services/resumes.service";
import type { MasterResumeSummary } from "@/types/resumes";

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
  {
    id: "resume-002",
    candidate_profile_id: "profile-123",
    original_filename: "Alex_Chen_Staff_Backend.docx",
    mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    file_size_bytes: 89000,
    checksum_sha256: "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
    is_active: false,
    created_at: "2026-11-12T14:30:00Z",
    updated_at: "2026-11-12T14:30:00Z",
    latest_version: {
      id: "ver-002",
      version_number: 2,
      is_valid: true,
      processing_status: "COMPLETED",
      created_at: "2026-11-12T14:30:00Z",
    },
  },
];

describe("ResumesPage Integration", () => {
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
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });

    const secondResume = mockResumes[1]!;
    vi.spyOn(resumesService, "activateResume").mockResolvedValue({
      ...secondResume,
      is_active: true,
      storage_key: "resumes/profile-123/resume-002.docx",
      versions: [secondResume.latest_version!],
    });

    vi.spyOn(resumesService, "downloadResumeFile").mockResolvedValue({
      data: new Blob(["dummy content"], { type: "application/pdf" }),
      filename: "Alex_Chen_Principal_Engineer.pdf",
    });
  });

  const renderPage = (initialEntries = ["/resumes"]) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <ResumesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header and list of master resumes with badges and file size", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Master Resumes", level: 1 })).toBeInTheDocument();
    expect((await screen.findAllByText("Alex_Chen_Principal_Engineer.pdf")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Alex_Chen_Staff_Backend.docx")).toBeInTheDocument();
    expect(screen.getAllByText(/ACTIVE MASTER RESUME/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("PDF")).toBeInTheDocument();
    expect(screen.getByText("DOCX")).toBeInTheDocument();
  });

  it("renders active master resume callout banner when active resume exists", async () => {
    renderPage();

    expect(await screen.findByText("Primary Source")).toBeInTheDocument();
    expect(screen.getByText("Active Master Resume")).toBeInTheDocument();
  });

  it("renders empty state when no master resumes are uploaded", async () => {
    vi.spyOn(resumesService, "listResumes").mockResolvedValueOnce({
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

    expect(await screen.findByText("No Master Resumes Uploaded")).toBeInTheDocument();
    expect(screen.getByText("Upload Your First Resume")).toBeInTheDocument();
  });

  it("triggers Set as Active action when button is clicked", async () => {
    renderPage();

    const activateBtn = await screen.findByRole("button", { name: /Set as Active/i });
    expect(activateBtn).toBeInTheDocument();

    fireEvent.click(activateBtn);

    await waitFor(() => {
      expect(resumesService.activateResume).toHaveBeenCalledWith("resume-002");
    });
  });

  it("opens and closes the upload resume modal", async () => {
    renderPage();

    const uploadBtn = await screen.findByRole("button", { name: /Upload Resume/i });
    fireEvent.click(uploadBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Upload Master Resume" })).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("validates file format on upload attempt", async () => {
    renderPage();

    const uploadBtn = await screen.findByRole("button", { name: /Upload Resume/i });
    fireEvent.click(uploadBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    // Select invalid .txt file
    const invalidFile = new File(["test text"], "resume.txt", { type: "text/plain" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeInTheDocument();

    fireEvent.change(input, { target: { files: [invalidFile] } });

    expect(await screen.findByText(/Only PDF and DOCX files are supported/i)).toBeInTheDocument();
  });
});
