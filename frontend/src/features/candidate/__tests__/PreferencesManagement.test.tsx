import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PreferencesCard } from "../components/PreferencesCard";
import { candidateService } from "@/services/candidate.service";
import type { CandidatePreferences } from "@/types/candidate";

const mockPreferences: CandidatePreferences = {
  id: "pref-101",
  candidate_profile_id: "c-101",
  minimum_relevance_score: 75,
  preferred_titles: ["Backend Engineer", "Cloud Architect"],
  preferred_workplace_types: ["REMOTE", "HYBRID"],
  preferred_locations: ["Seattle, WA", "Remote - US"],
  preferred_employment_types: ["FULL_TIME"],
  max_job_age_days: 21,
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-05T12:00:00Z",
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Preferences Management Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders preferences in view mode with correct data", () => {
    renderWithClient(<PreferencesCard preferences={mockPreferences} />);

    expect(screen.getByText("Job Matching Preferences")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
    expect(screen.getByText("21 days")).toBeInTheDocument();
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Cloud Architect")).toBeInTheDocument();
    expect(screen.getByText("Seattle, WA")).toBeInTheDocument();
    expect(screen.getByText("Remote - US")).toBeInTheDocument();
    expect(screen.getByText("REMOTE")).toBeInTheDocument();
    expect(screen.getByText("HYBRID")).toBeInTheDocument();
    expect(screen.getByText("FULL TIME")).toBeInTheDocument();
  });

  it("toggles edit mode when 'Edit Preferences' is clicked and cancels back to view mode", () => {
    renderWithClient(<PreferencesCard preferences={mockPreferences} />);

    const editBtn = screen.getByRole("button", { name: /Edit Preferences/i });
    fireEvent.click(editBtn);

    expect(screen.getByText("Save Preferences")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    expect(screen.queryByText("Save Preferences")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Edit Preferences/i })).toBeInTheDocument();
  });

  it("adds and removes target title tags in edit mode", async () => {
    renderWithClient(<PreferencesCard preferences={mockPreferences} />);

    fireEvent.click(screen.getByRole("button", { name: /Edit Preferences/i }));

    const titleInput = screen.getByPlaceholderText(/e\.g\. Senior Backend Engineer/i);
    fireEvent.change(titleInput, { target: { value: "Staff Platform Engineer" } });

    // Click Add Title button next to title input
    const addBtn = screen.getByRole("button", { name: /Add Title/i });
    fireEvent.click(addBtn);

    expect(screen.getByText("Staff Platform Engineer")).toBeInTheDocument();

    // Remove an existing title
    const removeBtn = screen.getByRole("button", { name: /Remove title Backend Engineer/i });
    fireEvent.click(removeBtn);

    expect(screen.queryByText("Backend Engineer")).not.toBeInTheDocument();
  });

  it("submits updated preferences and calls candidateService.updatePreferences", async () => {
    const updateSpy = vi.spyOn(candidateService, "updatePreferences").mockResolvedValue({
      ...mockPreferences,
      minimum_relevance_score: 85,
      max_job_age_days: 14,
    });

    renderWithClient(<PreferencesCard preferences={mockPreferences} />);

    fireEvent.click(screen.getByRole("button", { name: /Edit Preferences/i }));

    // Change max age days
    const ageInput = screen.getByDisplayValue("21");
    fireEvent.change(ageInput, { target: { value: "14" } });

    const saveBtn = screen.getByRole("button", { name: /Save Preferences/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          max_job_age_days: 14,
        })
      );
      expect(screen.getByText(/Preferences updated successfully!/i)).toBeInTheDocument();
    });
  });
});
