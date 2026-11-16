import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PipelineRunDetailPage } from "../pages/PipelineRunDetailPage";
import { pipelineService } from "@/services/pipeline.service";
import type { PipelineRun } from "@/types/pipeline";

const mockCompletedRun: PipelineRun = {
  id: "run-comp-1234",
  candidate_profile_id: "profile-123",
  trigger_type: "MANUAL",
  status: "COMPLETED",
  started_at: "2026-11-15T10:00:00Z",
  completed_at: "2026-11-15T10:02:30Z",
  created_at: "2026-11-15T09:59:50Z",
  updated_at: "2026-11-15T10:02:30Z",
  metrics: {
    jobs_discovered: 15,
    jobs_created: 10,
    jobs_updated: 5,
    jobs_normalized: 15,
    jobs_deduplicated: 3,
    jobs_evaluated: 12,
    matches_created: 6,
    matches_qualified: 3,
    semantic_analyses_completed: 3,
    semantic_analyses_failed: 0,
    resumes_generated: 3,
    resumes_failed: 0,
    notifications_sent: 3,
    notifications_failed: 0,
  },
  error_summary: null,
  metadata: {
    sources_scanned: ["greenhouse", "lever"],
    batch_size: 50,
  },
};

const mockRunningRun: PipelineRun = {
  id: "run-act-5678",
  candidate_profile_id: "profile-123",
  trigger_type: "SCHEDULED",
  status: "RUNNING",
  started_at: "2026-11-16T12:00:00Z",
  completed_at: null,
  created_at: "2026-11-16T11:59:50Z",
  updated_at: "2026-11-16T12:01:00Z",
  metrics: {
    jobs_discovered: 10,
    jobs_created: 8,
    jobs_updated: 2,
    jobs_normalized: 5,
    jobs_deduplicated: 1,
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
};

describe("PipelineRunDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(pipelineService, "getPipelineRun").mockResolvedValue(mockCompletedRun);
    vi.spyOn(pipelineService, "cancelPipelineRun").mockResolvedValue({
      pipeline_run_id: "run-act-5678",
      status: "CANCELLED",
      message: "Pipeline run cancelled.",
    });
  });

  const renderPage = (id = "run-comp-1234") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/pipeline/${id}`]}>
          <Routes>
            <Route path="/pipeline/:runId" element={<PipelineRunDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders complete pipeline telemetry, stage metrics, and metadata for completed run", async () => {
    renderPage("run-comp-1234");

    expect(await screen.findByRole("heading", { name: "Pipeline Execution Run", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
    expect(screen.getByText("Trigger: MANUAL")).toBeInTheDocument();
    expect(screen.getByText("2m 30s")).toBeInTheDocument();

    // Stage metrics
    expect(screen.getByText("Phase 1: Job Discovery")).toBeInTheDocument();
    expect(screen.getByText("Phase 2: Normalization & Canonical")).toBeInTheDocument();
    expect(screen.getByText("Phase 3: Deterministic Matching")).toBeInTheDocument();
    expect(screen.getByText("Phase 4: LLM Semantic Analysis")).toBeInTheDocument();
    expect(screen.getByText("Phase 5: Resume Tailoring & PDF")).toBeInTheDocument();
    expect(screen.getByText("Phase 6: Notifications & Delivery")).toBeInTheDocument();

    // Metadata
    expect(screen.getByText("Run Metadata & Configuration")).toBeInTheDocument();
    expect(screen.getByText(/greenhouse/i)).toBeInTheDocument();
  });

  it("renders active running banner and allows cancellation of active run", async () => {
    vi.spyOn(pipelineService, "getPipelineRun").mockResolvedValueOnce(mockRunningRun);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPage("run-act-5678");

    expect(await screen.findByText("Running")).toBeInTheDocument();
    expect(
      screen.getByText(/Pipeline run is actively executing. Telemetry is auto-refreshing in real time./i)
    ).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: /Cancel Run/i });
    expect(cancelBtn).toBeInTheDocument();

    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(pipelineService.cancelPipelineRun).toHaveBeenCalledWith("run-act-5678");
    });
  });

  it("renders error summary when execution failed", async () => {
    const mockFailedRun: PipelineRun = {
      ...mockCompletedRun,
      status: "FAILED",
      error_summary: "LLM Ollama timeout after 60 seconds connecting to model llama3:8b",
    };
    vi.spyOn(pipelineService, "getPipelineRun").mockResolvedValueOnce(mockFailedRun);

    renderPage("run-failed");

    expect(await screen.findByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Execution Error Summary")).toBeInTheDocument();
    expect(screen.getByText(/LLM Ollama timeout after 60 seconds/i)).toBeInTheDocument();
  });

  it("renders error state when run is not found", async () => {
    vi.spyOn(pipelineService, "getPipelineRun").mockRejectedValueOnce(new Error("Run not found"));

    renderPage("run-999");

    expect(await screen.findByText("Pipeline Run Not Found")).toBeInTheDocument();
  });
});
