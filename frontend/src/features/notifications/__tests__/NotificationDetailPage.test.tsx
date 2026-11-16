import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationDetailPage } from "../pages/NotificationDetailPage";
import { notificationsService } from "@/services/notifications.service";
import type { NotificationDeliveryRead } from "@/types/notifications";

const mockNotificationSent: NotificationDeliveryRead = {
  id: "notif-001",
  candidate_profile_id: "profile-123",
  job_id: "job-001",
  job_match_id: "match-001",
  tailored_resume_id: "tailored-001",
  notification_type: "IMMEDIATE_TAILORED_JOB",
  recipient_email: "alex.chen@example.com",
  status: "SENT",
  attempt_count: 1,
  max_attempts: 3,
  provider: "smtp",
  provider_message_id: "<20261115.12345@smtp.sendgrid.net>",
  sent_at: "2026-11-15T10:05:00Z",
  failed_at: null,
  last_error: null,
  created_at: "2026-11-15T10:00:00Z",
  updated_at: "2026-11-15T10:05:00Z",
  job_title: "Staff Distributed Systems Engineer",
  company_name: "Stripe",
  match_score: 92.5,
};

const mockNotificationFailed: NotificationDeliveryRead = {
  id: "notif-002",
  candidate_profile_id: "profile-123",
  job_id: "job-002",
  job_match_id: "match-002",
  tailored_resume_id: "tailored-002",
  notification_type: "IMMEDIATE_TAILORED_JOB",
  recipient_email: "alex.chen@example.com",
  status: "FAILED",
  attempt_count: 3,
  max_attempts: 3,
  provider: "smtp",
  provider_message_id: null,
  sent_at: null,
  failed_at: "2026-11-16T11:00:00Z",
  last_error: "SMTP connection timed out after 30000ms connecting to smtp.example.com:587",
  created_at: "2026-11-16T10:50:00Z",
  updated_at: "2026-11-16T11:00:00Z",
  job_title: "Lead Infrastructure Architect",
  company_name: "Datadog",
  match_score: 87.0,
};

describe("NotificationDetailPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(notificationsService, "getNotification").mockResolvedValue(mockNotificationSent);
    vi.spyOn(notificationsService, "retryNotification").mockResolvedValue({
      delivery_id: "notif-002",
      status: "PENDING",
      message: "Notification delivery retry scheduled.",
    });
  });

  const renderPage = (id = "notif-001") =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/notifications/${id}`]}>
          <Routes>
            <Route path="/notifications/:notificationId" element={<NotificationDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders notification details for delivered notification", async () => {
    renderPage("notif-001");

    expect(await screen.findByRole("heading", { name: "Notification Delivery Audit", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("alex.chen@example.com")).toBeInTheDocument();
    expect(screen.getByText("Delivered")).toBeInTheDocument();
    expect(screen.getByText("SMTP")).toBeInTheDocument();
    expect(screen.getByText("Staff Distributed Systems Engineer")).toBeInTheDocument();
    expect(screen.getByText("Stripe")).toBeInTheDocument();
    expect(screen.getByText("93%")).toBeInTheDocument(); // Math.round(92.5)
    expect(screen.getByText("<20261115.12345@smtp.sendgrid.net>")).toBeInTheDocument();
  });

  it("renders diagnostics and handles successful retry for failed delivery", async () => {
    vi.spyOn(notificationsService, "getNotification").mockResolvedValueOnce(mockNotificationFailed);

    renderPage("notif-002");

    expect(await screen.findByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Delivery Failure Diagnostics")).toBeInTheDocument();
    expect(screen.getByText(/SMTP connection timed out after 30000ms/i)).toBeInTheDocument();

    // Trigger retry
    const retryButtons = screen.getAllByRole("button", { name: /Retry/i });
    expect(retryButtons.length).toBeGreaterThan(0);
    fireEvent.click(retryButtons[0]!);

    await waitFor(() => {
      expect(notificationsService.retryNotification).toHaveBeenCalledWith("notif-002", { force: true });
      expect(screen.getByText(/Notification delivery retry scheduled/i)).toBeInTheDocument();
    });
  });

  it("handles retry error from backend and surfaces alert", async () => {
    vi.spyOn(notificationsService, "getNotification").mockResolvedValueOnce(mockNotificationFailed);
    vi.spyOn(notificationsService, "retryNotification").mockRejectedValueOnce(
      new Error("SMTP worker queue is full.")
    );

    renderPage("notif-002");

    expect(await screen.findByText("Failed")).toBeInTheDocument();

    const retryButtons = screen.getAllByRole("button", { name: /Retry/i });
    expect(retryButtons.length).toBeGreaterThan(0);
    fireEvent.click(retryButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText("SMTP worker queue is full.")).toBeInTheDocument();
    });
  });

  it("renders error state when notification is not found", async () => {
    vi.spyOn(notificationsService, "getNotification").mockRejectedValueOnce(
      new Error("Not found")
    );

    renderPage("notif-999");

    expect(await screen.findByText("Notification Not Found")).toBeInTheDocument();
  });
});
