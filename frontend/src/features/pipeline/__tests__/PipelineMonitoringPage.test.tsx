import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PipelineMonitoringPage } from "../pages/PipelineMonitoringPage";
import { pipelineService } from "@/services/pipeline.service";
import { candidateService } from "@/services/candidate.service";
import type { PipelineRunSummary } from "@/types/pipeline";
import type { CandidateProfile } from "@/types/candidate";

const mockCandidate: CandidateProfile = {
  id: "profile-123",
  user_id: "user-123",
  full_name: "Alex Chen",
  headline: "Principal Systems Engineer",
  professional_summary: "Distributed systems architect.",
  current_role: "Staff Engineer",
  total_experience_months: 120,
  city: "San Francisco",
  country: "United States",
  work_authorization: "US Citizen",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
};

const mockRuns: PipelineRunSummary[] = [
  {
    id: "run-001-comp",
    candidate_profile_id: "profile-123",
    trigger_type: "MANUAL",
    status: "COMPLETED",
    started_at: "2026-11-15T10:00:00Z",
    completed_at: "2026-11-15T10:03:00Z",
    created_at: "2026-11-15T09:59:50Z",
    updated_at: "2026-11-15T10:03:00Z",
    jobs_discovered: 12,
    matches_qualified: 4,
    resumes_generated: 4,
    notifications_sent: 4,
    error_summary: null,
  },
  {
    id: "run-002-runn",
    candidate_profile_id: "profile-123",
    trigger_type: "SCHEDULED",
    status: "RUNNING",
    started_at: "2026-11-16T12:00:00Z",
    completed_at: null,
    created_at: "2026-11-16T11:59:50Z",
    updated_at: "2026-11-16T12:01:00Z",
    jobs_discovered: 8,
    matches_qualified: 2,
    resumes_generated: 1,
    notifications_sent: 0,
    error_summary: null,
  },
];

describe("PipelineMonitoringPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(candidateService, "getProfile").mockResolvedValue(mockCandidate);

    vi.spyOn(pipelineService, "listPipelineRuns").mockImplementation(async (params) => {
      let filtered = [...mockRuns];
      if (params?.status) {
        filtered = filtered.filter((r) => r.status === params.status);
      }
      return {
        items: filtered,
        pagination: {
          page: params?.page || 1,
          page_size: params?.page_size || 10,
          total_items: filtered.length,
          total_pages: 1,
          has_next: false,
          has_prev: false,
        },
      };
    });

    vi.spyOn(pipelineService, "startPipelineRun").mockResolvedValue({
      id: "run-new-003",
      candidate_profile_id: "profile-123",
      trigger_type: "MANUAL",
      status: "PENDING",
      started_at: null,
      completed_at: null,
      created_at: "2026-11-16T12:30:00Z",
      updated_at: "2026-11-16T12:30:00Z",
      metrics: {
        jobs_discovered: 0,
        jobs_created: 0,
        jobs_updated: 0,
        jobs_normalized: 0,
        jobs_deduplicated: 0,
        jobs_evaluated: 0,
        matches_created: 0,
        matches_qualified: 0,
        semantic_analyses_completed: 0,
        semantic_analyses_failed: 0,
        resumes_generated: 0,
        resumes_failed: 0,
        notifications_sent: 0,
        notifications_failed: 0,
      },
      error_summary: null,
    });
  });

  const renderPage = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PipelineMonitoringPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders operational metrics console, telemetry summary, and runs table", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Pipeline Runs", level: 1 })).toBeInTheDocument();
    expect(await screen.findByText("Latest Pipeline Telemetry")).toBeInTheDocument();
    expect(screen.getByText("Total Executions")).toBeInTheDocument();
    expect(screen.getByText("Successful Executions")).toBeInTheDocument();

    // Table rows
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Running").length).toBeGreaterThan(0);
  });

  it("filters runs table by status when tabs are selected", async () => {
    renderPage();

    expect(await screen.findByRole("table")).toBeInTheDocument();
    const table = screen.getByRole("table");

    expect(within(table).getByText(/run-001/i)).toBeInTheDocument();
    expect(within(table).getByText(/run-002/i)).toBeInTheDocument();

    // Click "Running" tab
    const runningTab = screen.getByRole("button", { name: /^Running/i });
    fireEvent.click(runningTab);

    await waitFor(() => {
      const currentTable = screen.getByRole("table");
      expect(within(currentTable).getByText(/run-002/i)).toBeInTheDocument();
      expect(within(currentTable).queryByText(/run-001/i)).not.toBeInTheDocument();
    });
  });

  it("opens manual trigger modal and submits run request", async () => {
    renderPage();

    const triggerBtn = await screen.findByRole("button", { name: /Trigger Pipeline Run/i });
    await waitFor(() => {
      expect(triggerBtn).not.toBeDisabled();
    });

    fireEvent.click(triggerBtn);

    // Modal opens
    expect(await screen.findByRole("heading", { name: "Start Pipeline Run" })).toBeInTheDocument();

    // Submit modal trigger via Enqueue Run button
    const confirmBtn = screen.getByRole("button", { name: /Enqueue Run/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(pipelineService.startPipelineRun).toHaveBeenCalledWith({
        candidate_profile_id: "profile-123",
        trigger_type: "MANUAL",
        metadata: {
          client: "JobRadar AI Web Console",
          triggered_by: "User manual request",
        },
      });
    });
  });

  it("renders empty state when no pipeline runs exist", async () => {
    vi.spyOn(pipelineService, "listPipelineRuns").mockResolvedValueOnce({
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

    expect(await screen.findByText("No Pipeline Runs Found")).toBeInTheDocument();
  });
});
