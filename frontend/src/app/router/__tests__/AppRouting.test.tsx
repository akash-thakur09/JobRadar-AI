import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MemoryRouter, RouterProvider, createMemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "@/app/layouts/Sidebar";
import { Header } from "@/app/layouts/Header";
import { AppLayout } from "@/app/layouts/AppLayout";
import { DashboardPage } from "@/features/dashboard/pages/DashboardPage";
import { PlaceholderPage } from "@/features/placeholder/pages/PlaceholderPage";
import { Globe } from "lucide-react";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("App Shell & Routing Navigation", () => {
  it("renders sidebar with brand title and navigation links", () => {
    renderWithClient(
      <MemoryRouter initialEntries={["/"]}>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText("JobRadar AI")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Candidate Profile")).toBeInTheDocument();
    expect(screen.getByText("Job Discovery")).toBeInTheDocument();
    expect(screen.getByText("Job Matches")).toBeInTheDocument();
    expect(screen.getByText("Resumes")).toBeInTheDocument();
    expect(screen.getByText("Notifications")).toBeInTheDocument();
    expect(screen.getByText("Pipeline Runs")).toBeInTheDocument();
  });

  it("renders Header with workspace title and status pill", () => {
    renderWithClient(
      <MemoryRouter initialEntries={["/"]}>
        <Header />
      </MemoryRouter>
    );

    expect(screen.getByText("JobRadar AI Workspace")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Pipeline Runs/i })).toBeInTheDocument();
  });

  it("renders placeholder page for unimplemented milestone routes", () => {
    renderWithClient(
      <MemoryRouter initialEntries={["/resumes"]}>
        <PlaceholderPage
          title="Resume Management"
          description="Tailored resumes"
          icon={Globe}
          targetMilestone="Milestone 14"
          plannedFeatures={["Uploads", "Tailoring"]}
        />
      </MemoryRouter>
    );

    expect(screen.getByText("Resume Management Module")).toBeInTheDocument();
    expect(screen.getByText(/Planned for Milestone 14/i)).toBeInTheDocument();
    expect(screen.getByText("Uploads")).toBeInTheDocument();
  });

  it("supports navigation via memory router", () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    queryClient.setQueryData(["candidate", "profile"], {
      id: "c-1",
      full_name: "Test Candidate",
      total_experience_months: 60,
    });
    queryClient.setQueryData(["health", "readiness"], {
      status: "healthy",
      timestamp: new Date().toISOString(),
      components: { database: "healthy", redis: "healthy" },
    });
    queryClient.setQueryData(["pipeline", "list", { page_size: 1 }], {
      items: [],
      pagination: {
        total_items: 0,
        page: 1,
        page_size: 1,
        total_pages: 0,
        has_next: false,
        has_previous: false,
      },
    });

    const testRouter = createMemoryRouter(
      [
        {
          path: "/",
          element: <AppLayout />,
          children: [
            { index: true, element: <DashboardPage /> },
            {
              path: "jobs",
              element: <div>Job Discovery Destination</div>,
            },
          ],
        },
      ],
      { initialEntries: ["/"] }
    );

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={testRouter} />
      </QueryClientProvider>
    );

    expect(screen.getByText("Intelligence Dashboard")).toBeInTheDocument();

    // Click on Job Discovery in sidebar (href: /jobs)
    const discoveryLink = screen.getByRole("link", { name: /Job Discovery/i });
    fireEvent.click(discoveryLink);

    expect(screen.getByText("Job Discovery Destination")).toBeInTheDocument();
  });
});
