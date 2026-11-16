import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { PageHeader } from "../PageHeader";
import { Breadcrumbs } from "../Breadcrumbs";
import { EmptyState } from "../EmptyState";
import { ErrorState } from "../ErrorState";
import { LoadingState } from "../LoadingState";

describe("Common Components", () => {
  describe("Breadcrumbs & PageHeader", () => {
    it("renders breadcrumbs trail", () => {
      render(
        <BrowserRouter>
          <Breadcrumbs
            items={[
              { label: "Overview", href: "/overview" },
              { label: "Profile" },
            ]}
          />
        </BrowserRouter>
      );

      expect(screen.getByText("Profile")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    });

    it("renders PageHeader with title and actions", () => {
      render(
        <BrowserRouter>
          <PageHeader
            title="System Dashboard"
            description="Overview metrics and telemetry"
            actions={<button>Action Btn</button>}
          />
        </BrowserRouter>
      );

      expect(screen.getByText("System Dashboard")).toBeInTheDocument();
      expect(screen.getByText("Overview metrics and telemetry")).toBeInTheDocument();
      expect(screen.getByText("Action Btn")).toBeInTheDocument();
    });
  });

  describe("EmptyState", () => {
    it("renders empty state information and action button", () => {
      const handleAction = vi.fn();
      render(
        <EmptyState
          title="No Jobs Discovered"
          description="Click the button to start crawling."
          actionLabel="Start Discovery"
          onAction={handleAction}
        />
      );

      expect(screen.getByText("No Jobs Discovered")).toBeInTheDocument();
      expect(screen.getByText("Click the button to start crawling.")).toBeInTheDocument();
      const btn = screen.getByRole("button", { name: "Start Discovery" });
      fireEvent.click(btn);
      expect(handleAction).toHaveBeenCalledTimes(1);
    });
  });

  describe("ErrorState", () => {
    it("renders error message and retry button", () => {
      const handleRetry = vi.fn();
      render(
        <ErrorState
          title="API Connection Failed"
          message="Server returned 500."
          onRetry={handleRetry}
        />
      );

      expect(screen.getByText("API Connection Failed")).toBeInTheDocument();
      expect(screen.getByText("Server returned 500.")).toBeInTheDocument();
      const retryBtn = screen.getByRole("button", { name: /Retry Request/i });
      fireEvent.click(retryBtn);
      expect(handleRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe("LoadingState", () => {
    it("renders loading message", () => {
      render(<LoadingState message="Loading candidates..." />);
      expect(screen.getAllByText("Loading candidates...").length).toBeGreaterThan(0);
    });
  });
});

