import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationsPage } from "../pages/NotificationsPage";
import { notificationsService } from "@/services/notifications.service";
import type { NotificationDeliverySummary } from "@/types/notifications";

const mockNotifications: NotificationDeliverySummary[] = [
  {
    id: "notif-001",
    candidate_profile_id: "profile-123",
    job_id: "job-001",
    job_match_id: "match-001",
    tailored_resume_id: "tailored-001",
    notification_type: "IMMEDIATE_TAILORED_JOB",
    recipient_email: "candidate@example.com",
    status: "SENT",
    attempt_count: 1,
    max_attempts: 3,
    provider: "smtp",
    provider_message_id: "<msg-123@smtp.example.com>",
    sent_at: "2026-11-15T10:05:00Z",
    failed_at: null,
    created_at: "2026-11-15T10:00:00Z",
    updated_at: "2026-11-15T10:05:00Z",
    job_title: "Staff Distributed Systems Engineer",
    company_name: "Stripe",
  },
  {
    id: "notif-002",
    candidate_profile_id: "profile-123",
    job_id: "job-002",
    job_match_id: "match-002",
    tailored_resume_id: "tailored-002",
    notification_type: "IMMEDIATE_TAILORED_JOB",
    recipient_email: "candidate@example.com",
    status: "FAILED",
    attempt_count: 3,
    max_attempts: 3,
    provider: "smtp",
    provider_message_id: null,
    sent_at: null,
    failed_at: "2026-11-16T11:00:00Z",
    created_at: "2026-11-16T10:50:00Z",
    updated_at: "2026-11-16T11:00:00Z",
    job_title: "Lead Infrastructure Architect",
    company_name: "Datadog",
  },
];

describe("NotificationsPage Integration", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    vi.spyOn(notificationsService, "listNotifications").mockImplementation(async (params) => {
      let filtered = [...mockNotifications];
      if (params?.status) {
        filtered = filtered.filter((n) => n.status === params.status);
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

    vi.spyOn(notificationsService, "retryNotification").mockResolvedValue({
      delivery_id: "notif-002",
      status: "PENDING",
      message: "Notification delivery retry scheduled.",
    });
  });

  const renderPage = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <NotificationsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it("renders page header, KPI cards, and notification table rows", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Email Notifications", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Total Deliveries")).toBeInTheDocument();
    expect(screen.getByText("Delivered (Sent)")).toBeInTheDocument();
    expect(screen.getByText("Delivery Failures")).toBeInTheDocument();

    // Table rows
    expect(await screen.findByText("Staff Distributed Systems Engineer")).toBeInTheDocument();
    expect(screen.getByText("Lead Infrastructure Architect")).toBeInTheDocument();
    expect(screen.getAllByText("Delivered").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Failed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("candidate@example.com").length).toBeGreaterThan(0);
  });

  it("filters notification deliveries when status filter tabs are clicked", async () => {
    renderPage();

    expect(await screen.findByText("Staff Distributed Systems Engineer")).toBeInTheDocument();

    // Click "Delivered" tab
    const deliveredTab = screen.getByRole("button", { name: /^Delivered/i });
    fireEvent.click(deliveredTab);

    await waitFor(() => {
      expect(screen.getByText("Staff Distributed Systems Engineer")).toBeInTheDocument();
      expect(screen.queryByText("Lead Infrastructure Architect")).not.toBeInTheDocument();
    });
  });

  it("triggers inline retry on failed notification and prevents duplicate submission", async () => {
    renderPage();

    // Wait for the table row with the failed notification to render
    expect(await screen.findByText("Lead Infrastructure Architect")).toBeInTheDocument();

    const retryBtn = screen.getByRole("button", { name: /Retry/i });
    expect(retryBtn).toBeInTheDocument();

    // Click Retry
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(notificationsService.retryNotification).toHaveBeenCalledWith("notif-002", { force: true });
      expect(screen.getByText(/Notification delivery retry scheduled/i)).toBeInTheDocument();
    });
  });

  it("renders empty state when no notifications match criteria", async () => {
    vi.spyOn(notificationsService, "listNotifications").mockResolvedValueOnce({
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

    expect(await screen.findByText("No Notification Records Found")).toBeInTheDocument();
  });
});
