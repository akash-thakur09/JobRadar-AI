import type { CandidatePreferences, CandidateProfile, CandidateSkill } from "@/types/candidate";

export interface CompletionCriterion {
  id: string;
  label: string;
  isComplete: boolean;
  weight: number;
  tip: string;
}

export function calculateProfileCompletion(
  profile: CandidateProfile | null | undefined,
  preferences?: CandidatePreferences | null,
  skills?: CandidateSkill[] | null
): {
  score: number;
  criteria: CompletionCriterion[];
  completedCount: number;
  totalCount: number;
} {
  const criteria: CompletionCriterion[] = [
    {
      id: "name",
      label: "Full Name",
      isComplete: Boolean(profile?.full_name?.trim()),
      weight: 10,
      tip: "Required for resume tailoring header",
    },
    {
      id: "headline",
      label: "Professional Headline",
      isComplete: Boolean(profile?.headline?.trim()),
      weight: 10,
      tip: "Used for target role positioning",
    },
    {
      id: "summary",
      label: "Professional Summary",
      isComplete: Boolean(profile?.professional_summary && profile.professional_summary.length > 30),
      weight: 15,
      tip: "Enriches LLM semantic evaluation and resume summary section",
    },
    {
      id: "role",
      label: "Current Role",
      isComplete: Boolean(profile?.current_role?.trim()),
      weight: 10,
      tip: "Calibrates job title similarity scoring",
    },
    {
      id: "experience",
      label: "Work Experience",
      isComplete: Boolean(profile && profile.total_experience_months > 0),
      weight: 15,
      tip: "Gates Layer 1 deterministic experience eligibility",
    },
    {
      id: "location",
      label: "Location",
      isComplete: Boolean(profile?.city || profile?.country),
      weight: 10,
      tip: "Assists geographical eligibility filters",
    },
    {
      id: "work_auth",
      label: "Work Authorization",
      isComplete: Boolean(profile?.work_authorization?.trim()),
      weight: 10,
      tip: "Gates strict legal work authorization checks",
    },
    {
      id: "skills",
      label: "Evidence Vault Skills",
      isComplete: Boolean(skills && skills.length > 0),
      weight: 10,
      tip: "Strictly enforces truthful skill matching without hallucinations",
    },
    {
      id: "preferences",
      label: "Matching Preferences",
      isComplete: Boolean(
        preferences &&
          (preferences.preferred_titles?.length > 0 ||
            preferences.preferred_workplace_types?.length > 0)
      ),
      weight: 10,
      tip: "Directs automated crawler to relevant opportunities",
    },
  ];

  const score = criteria.reduce((sum, item) => sum + (item.isComplete ? item.weight : 0), 0);
  const completedCount = criteria.filter((c) => c.isComplete).length;

  return {
    score: Math.min(100, score),
    criteria,
    completedCount,
    totalCount: criteria.length,
  };
}

