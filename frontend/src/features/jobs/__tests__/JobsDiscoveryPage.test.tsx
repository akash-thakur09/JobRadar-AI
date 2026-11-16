import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobsDiscoveryPage } from "../pages/JobsDiscoveryPage";
import { jobsService } from "@/services/jobs.service";
import type { JobSummary } from "@/types/jobs";

const mockJobs: JobSummary[] = [
  {
    id: "job-001",
    canonical_company_name: "Stripe",
    title: "Staff Backend Engineer",
    canonical_application_url: "https://stripe.com/jobs/1",
    workplace_type: "REMOTE",
    normalized_location: "Remote - US",
    employment_type: "FULL_TIME",
    posted_at: "2026-11-15T12:00:00Z",
    first_seen_at: "2026-11-15T12:00:00Z",
    last_seen_at: "2026-11-16T12:00:00Z",
    status: "ACTIVE",
    created_at: "2026-11-15T12:00:00Z",
  },
  {
    id: "job-002",
    canonical_company_name: "Datadog",
    title: "Distributed Systems Engineer",
    canonical_application_url: "https://datadog.com/jobs/2",
    workplace_type: "HYBRID",
    normalized_location: "New York, NY",
    employment_type: "FULL_TIME",
    posted_at: "2026-11-14T08:00:00Z",
    first_seen_at: "2026-11-14T08:00:00Z",
    last_seen_at: "2026-11-16T12:00:00Z",
    status: "DISCOVERED",
    created_at: "2026-11-14T08:00:00Z",
  },
];

describe("JobsDiscoveryPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(jobsService, "listJobs").mockResolvedValue({
      items: mockJobs,
      pagination: {
        page: 1,
        page_size: 15,
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
    });

    vi.spyOn(jobsService, "processPendingJobs").mockResolvedValue({
      queued_count: 5,
      processed_count: 5,
    });
  });

  const renderPage = (initialEntries = ["/jobs"]) =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <JobsDiscoveryPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header and job discovery cards with company and badges", async () => {
    renderPage();

    expect(screen.getByRole("heading", { level: 1, name: "Job Discovery" })).toBeInTheDocument();
    expect(
      screen.getByText(/Explore clean, deduplicated canonical opportunities/i)
    ).toBeInTheDocument();

    // Verify job cards
    expect(await screen.findByText("Staff Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Stripe")).toBeInTheDocument();
    expect(screen.getByText("Remote - US")).toBeInTheDocument();

    expect(screen.getByText("Distributed Systems Engineer")).toBeInTheDocument();
    expect(screen.getByText("Datadog")).toBeInTheDocument();
    expect(screen.getByText("New York, NY")).toBeInTheDocument();
  });

  it("renders external apply link with safe target and rel attributes", async () => {
    renderPage();

    await screen.findByText("Staff Backend Engineer");
    const applyLinks = screen.getAllByRole("link", { name: /Apply/i });
    expect(applyLinks.length).toBeGreaterThan(0);
    expect(applyLinks[0]).toHaveAttribute("target", "_blank");
    expect(applyLinks[0]).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("updates search input filter", async () => {
    renderPage();

    const searchInput = screen.getByLabelText("Search jobs");
    expect(searchInput).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "Backend" } });
    expect((searchInput as HTMLInputElement).value).toBe("Backend");
  });

  it("renders empty state when no jobs are returned", async () => {
    vi.spyOn(jobsService, "listJobs").mockResolvedValueOnce({
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

    renderPage(["/jobs"]);

    expect(await screen.findByText("No canonical jobs discovered yet")).toBeInTheDocument();
    expect(
      screen.getByText(/Execute a pipeline discovery run or process pending raw source records/i)
    ).toBeInTheDocument();
  });

  it("renders error state on API failure with retry action", async () => {
    vi.spyOn(jobsService, "listJobs").mockRejectedValueOnce(new Error("Database connection timeout"));

    renderPage();

    expect(await screen.findByText("Failed to Load Jobs")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });

  it("allows triggering pending jobs normalization process", async () => {
    renderPage();

    const processBtn = await screen.findByRole("button", { name: /Process Pending/i });
    fireEvent.click(processBtn);

    await waitFor(() => {
      expect(jobsService.processPendingJobs).toHaveBeenCalled();
    });
  });
});
