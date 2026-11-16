import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProfileCard } from "../components/ProfileCard";
import type { CandidateProfile } from "@/types/candidate";
import { candidateService } from "@/services/candidate.service";

const mockProfile: CandidateProfile = {
  id: "c-123",
  user_id: "u-456",
  full_name: "Jane Developer",
  headline: "Senior Backend Engineer",
  professional_summary: "Expert in async Python microservices and PostgreSQL.",
  current_role: "Staff Architect",
  total_experience_months: 96,
  city: "San Francisco",
  country: "United States",
  work_authorization: "US Citizen",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-05T12:00:00Z",
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ProfileCard & ProfileEditForm", () => {
  it("renders candidate profile fields correctly", () => {
    renderWithClient(<ProfileCard profile={mockProfile} />);

    expect(screen.getByText("Jane Developer")).toBeInTheDocument();
    expect(screen.getByText("Senior Backend Engineer")).toBeInTheDocument();
    expect(
      screen.getByText("Expert in async Python microservices and PostgreSQL.")
    ).toBeInTheDocument();
    expect(screen.getByText("Staff Architect")).toBeInTheDocument();
    expect(screen.getByText("8 years")).toBeInTheDocument();
    expect(screen.getByText("San Francisco, United States")).toBeInTheDocument();
    expect(screen.getByText("US Citizen")).toBeInTheDocument();
  });

  it("toggles edit form when 'Edit Profile' is clicked", () => {
    renderWithClient(<ProfileCard profile={mockProfile} />);

    const editBtn = screen.getByRole("button", { name: /Edit Profile/i });
    fireEvent.click(editBtn);

    expect(screen.getByLabelText(/Full Name/i)).toHaveValue("Jane Developer");
    expect(screen.getByLabelText(/Headline/i)).toHaveValue("Senior Backend Engineer");
    expect(screen.getByRole("button", { name: /Save Changes/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Cancel/i })).toBeInTheDocument();
  });

  it("validates full name requirement on form submission", async () => {
    renderWithClient(<ProfileCard profile={mockProfile} />);

    fireEvent.click(screen.getByRole("button", { name: /Edit Profile/i }));

    const nameInput = screen.getByLabelText(/Full Name/i);
    fireEvent.change(nameInput, { target: { value: "   " } });

    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(screen.getByText(/Full name cannot be blank/i)).toBeInTheDocument();
    });
  });

  it("submits updated profile payload to candidateService", async () => {
    const updateSpy = vi.spyOn(candidateService, "updateProfile").mockResolvedValueOnce({
      ...mockProfile,
      full_name: "Jane Doe Updated",
    });

    renderWithClient(<ProfileCard profile={mockProfile} />);

    fireEvent.click(screen.getByRole("button", { name: /Edit Profile/i }));

    const nameInput = screen.getByLabelText(/Full Name/i);
    fireEvent.change(nameInput, { target: { value: "Jane Doe Updated" } });

    fireEvent.click(screen.getByRole("button", { name: /Save Changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          full_name: "Jane Doe Updated",
        })
      );
    });
  });
});

