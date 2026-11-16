import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SkillsList } from "../components/SkillsList";
import { candidateService } from "@/services/candidate.service";
import type { CandidateSkill } from "@/types/candidate";

const mockSkills: CandidateSkill[] = [
  {
    id: "sk-1",
    candidate_profile_id: "c-1",
    skill_name: "Python",
    category: "backend",
    experience_months: 84,
    is_core: true,
    created_at: "2026-11-01T10:00:00Z",
  },
  {
    id: "sk-2",
    candidate_profile_id: "c-1",
    skill_name: "PostgreSQL",
    category: "database",
    experience_months: 60,
    is_core: false,
    created_at: "2026-11-01T10:00:00Z",
  },
];

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("Skills Management Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders core competencies and technical skills separately", () => {
    renderWithClient(<SkillsList skills={mockSkills} />);

    expect(screen.getByText("Evidence Vault Skills")).toBeInTheDocument();
    expect(screen.getByText("2 Verified")).toBeInTheDocument();
    expect(screen.getByText(/Core Competencies \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Technical & Secondary Skills \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument();
  });

  it("opens Add Skill modal when 'Add Skill' button is clicked", () => {
    renderWithClient(<SkillsList skills={mockSkills} />);

    const addBtn = screen.getByRole("button", { name: /Add Skill/i });
    fireEvent.click(addBtn);

    expect(screen.getByRole("heading", { name: /Add Verified Skill/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. PostgreSQL, React/i)).toBeInTheDocument();
  });

  it("prevents adding duplicate skill with client-side validation message", async () => {
    renderWithClient(<SkillsList skills={mockSkills} />);

    fireEvent.click(screen.getByRole("button", { name: /Add Skill/i }));

    const input = screen.getByPlaceholderText(/e\.g\. PostgreSQL, React/i);
    // Enter existing skill name (case insensitive)
    fireEvent.change(input, { target: { value: "python" } });

    const submitBtn = screen.getByRole("button", { name: /Register Skill/i });
    fireEvent.click(submitBtn);

    expect(
      await screen.findByText(/Skill "python" is already registered in your Evidence Vault\./i)
    ).toBeInTheDocument();
  });

  it("submits new skill and calls candidateService.addSkill", async () => {
    const addSpy = vi.spyOn(candidateService, "addSkill").mockResolvedValue({
      id: "sk-3",
      candidate_profile_id: "c-1",
      skill_name: "Docker",
      category: "backend",
      experience_months: 12,
      is_core: false,
      created_at: "2026-11-16T10:00:00Z",
    });

    renderWithClient(<SkillsList skills={mockSkills} />);

    fireEvent.click(screen.getByRole("button", { name: /Add Skill/i }));

    const input = screen.getByPlaceholderText(/e\.g\. PostgreSQL, React/i);
    fireEvent.change(input, { target: { value: "Docker" } });

    const submitBtn = screen.getByRole("button", { name: /Register Skill/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(addSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          skill_name: "Docker",
          category: "backend",
        })
      );
      expect(screen.getByText(/Skill successfully added to Evidence Vault!/i)).toBeInTheDocument();
    });
  });

  it("opens Delete Skill modal and calls candidateService.deleteSkill on confirmation", async () => {
    const deleteSpy = vi.spyOn(candidateService, "deleteSkill").mockResolvedValue();

    renderWithClient(<SkillsList skills={mockSkills} />);

    // Click remove button on PostgreSQL
    const removeBtn = screen.getByRole("button", { name: /Remove skill PostgreSQL/i });
    fireEvent.click(removeBtn);

    expect(screen.getByRole("heading", { name: /^Remove Skill$/i })).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to remove/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: /Confirm Removal/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("sk-2");
      expect(screen.getByText(/Skill "PostgreSQL" removed from Evidence Vault\./i)).toBeInTheDocument();
    });
  });
});
