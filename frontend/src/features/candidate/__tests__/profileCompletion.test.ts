import { describe, it, expect } from "vitest";
import { calculateProfileCompletion } from "../utils/profileCompletion";
import type { CandidateProfile, CandidatePreferences, CandidateSkill } from "@/types/candidate";

const fullProfile: CandidateProfile = {
  id: "c-1",
  user_id: "u-1",
  full_name: "Jane Doe",
  headline: "Principal Engineer",
  professional_summary: "Over a decade building distributed systems and high performance microservices.",
  current_role: "Principal Architect",
  total_experience_months: 120,
  city: "San Francisco",
  country: "United States",
  work_authorization: "US Citizen",
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const fullPreferences: CandidatePreferences = {
  id: "pref-1",
  candidate_profile_id: "c-1",
  minimum_relevance_score: 80,
  preferred_titles: ["Principal Engineer"],
  preferred_workplace_types: ["REMOTE"],
  preferred_locations: ["Remote - US"],
  preferred_employment_types: ["FULL_TIME"],
  max_job_age_days: 14,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
};

const sampleSkills: CandidateSkill[] = [
  {
    id: "sk-1",
    candidate_profile_id: "c-1",
    skill_name: "Python",
    category: "backend",
    experience_months: 96,
    is_core: true,
    created_at: "2026-11-01T00:00:00Z",
  },
];

describe("calculateProfileCompletion", () => {
  it("returns 0% when no profile, preferences, or skills exist", () => {
    const result = calculateProfileCompletion(undefined, undefined, []);
    expect(result.score).toBe(0);
    expect(result.completedCount).toBe(0);
    expect(result.totalCount).toBe(9);
    expect(result.criteria.every((c) => !c.isComplete)).toBe(true);
  });

  it("returns 100% when all 9 checkpoints are satisfied", () => {
    const result = calculateProfileCompletion(fullProfile, fullPreferences, sampleSkills);
    expect(result.score).toBe(100);
    expect(result.completedCount).toBe(9);
    expect(result.totalCount).toBe(9);
    expect(result.criteria.every((c) => c.isComplete)).toBe(true);
  });

  it("calculates partial completion when profile fields are missing", () => {
    const partialProfile: CandidateProfile = {
      ...fullProfile,
      headline: "",
      professional_summary: "",
      city: "",
      country: "",
    };

    const result = calculateProfileCompletion(partialProfile, fullPreferences, sampleSkills);
    // Missing: headline (10), summary (15), location (10) -> completed 6 of 9
    expect(result.completedCount).toBe(6);
    expect(result.score).toBe(65);

    const headlineItem = result.criteria.find((c) => c.id === "headline");
    expect(headlineItem?.isComplete).toBe(false);

    const summaryItem = result.criteria.find((c) => c.id === "summary");
    expect(summaryItem?.isComplete).toBe(false);

    const locationItem = result.criteria.find((c) => c.id === "location");
    expect(locationItem?.isComplete).toBe(false);
  });

  it("marks skills checkpoint incomplete if skills array is empty", () => {
    const result = calculateProfileCompletion(fullProfile, fullPreferences, []);
    expect(result.completedCount).toBe(8);
    expect(result.score).toBe(90);

    const skillsItem = result.criteria.find((c) => c.id === "skills");
    expect(skillsItem?.isComplete).toBe(false);
  });

  it("marks preferences checkpoint incomplete if preferences are undefined or empty", () => {
    const result = calculateProfileCompletion(fullProfile, undefined, sampleSkills);
    expect(result.completedCount).toBe(8);
    expect(result.score).toBe(90);

    const prefItem = result.criteria.find((c) => c.id === "preferences");
    expect(prefItem?.isComplete).toBe(false);
  });
});
