import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PipelineRunsTable } from "../components/PipelineRunsTable";
import { StatusBadge } from "../components/StatusBadge";
import type { PipelineRunSummary } from "@/types/pipeline";

const mockRuns: PipelineRunSummary[] = [
  {
    id: "run-1111-2222-3333",
    candidate_profile_id: "c-123",
    trigger_type: "MANUAL",
    status: "COMPLETED",
    started_at: "2026-11-05T12:00:00Z",
    completed_at: "2026-11-05T12:02:00Z",
    created_at: "2026-11-05T11:59:50Z",
    updated_at: "2026-11-05T12:02:00Z",
    jobs_discovered: 5,
    matches_qualified: 2,
    resumes_generated: 2,
    notifications_sent: 2,
    error_summary: null,
  },
  {
    id: "run-4444-5555-6666",
    candidate_profile_id: "c-123",
    trigger_type: "SCHEDULED",
    status: "RUNNING",
    started_at: "2026-11-05T13:00:00Z",
    completed_at: null,
    created_at: "2026-11-05T12:59:50Z",
    updated_at: "2026-11-05T13:00:10Z",
    jobs_discovered: 3,
    matches_qualified: 1,
    resumes_generated: 0,
    notifications_sent: 0,
    error_summary: null,
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Pipeline Monitoring Components", () => {
  describe("StatusBadge", () => {
    it("renders all run status variants cleanly", () => {
      const { rerender } = render(<StatusBadge status="COMPLETED" />);
      expect(screen.getByText("Completed")).toBeInTheDocument();

      rerender(<StatusBadge status="RUNNING" />);
      expect(screen.getByText("Running")).toBeInTheDocument();

      rerender(<StatusBadge status="PENDING" />);
      expect(screen.getByText("Pending")).toBeInTheDocument();

      rerender(<StatusBadge status="PARTIALLY_COMPLETED" />);
      expect(screen.getByText("Partially Completed")).toBeInTheDocument();

      rerender(<StatusBadge status="FAILED" />);
      expect(screen.getByText("Failed")).toBeInTheDocument();

      rerender(<StatusBadge status="CANCELLED" />);
      expect(screen.getByText("Cancelled")).toBeInTheDocument();
    });
  });

  describe("PipelineRunsTable", () => {
    it("renders pipeline runs and handles row selection", () => {
      const handleSelect = vi.fn();
      renderWithClient(
        <PipelineRunsTable runs={mockRuns} onSelectRun={handleSelect} />
      );

      expect(screen.getByText(/run-1111/i)).toBeInTheDocument();
      expect(screen.getByText(/run-4444/i)).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(screen.getByText("Running")).toBeInTheDocument();

      // Click row
      fireEvent.click(screen.getByText(/run-1111/i));
      expect(handleSelect).toHaveBeenCalledWith("run-1111-2222-3333");
    });

    it("renders cancel button for active running run", () => {
      renderWithClient(
        <PipelineRunsTable runs={mockRuns} onSelectRun={vi.fn()} />
      );

      const cancelButtons = screen.getAllByRole("button", { name: /Cancel/i });
      expect(cancelButtons.length).toBe(1); // Only for RUNNING run
    });
  });
});

