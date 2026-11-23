import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import {
  useCandidateProfile,
  useCandidatePreferences,
  useCandidateSkills,
} from "@/hooks/useCandidateProfile";
import { ProfileCard } from "../components/ProfileCard";
import { PreferencesCard } from "../components/PreferencesCard";
import { SkillsList } from "../components/SkillsList";
import { ProfileCompletionWidget } from "../components/ProfileCompletionWidget";
import { User } from "lucide-react";

export function CandidateProfilePage() {
  const {
    data: profile,
    isLoading: isProfileLoading,
    error: profileError,
    refetch: refetchProfile,
  } = useCandidateProfile();

  const { data: preferences, isLoading: isPreferencesLoading } = useCandidatePreferences();
  const { data: skills, isLoading: isSkillsLoading } = useCandidateSkills();

  const isLoading = isProfileLoading || isPreferencesLoading || isSkillsLoading;

  if (isLoading) {
    return <LoadingState message="Loading candidate profile and preferences from backend..." />;
  }

  if (profileError) {
    return (
      <div>
        <PageHeader
          title="Candidate Profile"
          description="Manage your professional summary, job matching preferences, and verified skills"
          breadcrumbs={[{ label: "Candidate Profile" }]}
        />
        <ErrorState
          title="Could not load candidate profile"
          message="Failed to fetch candidate profile from the backend. Please ensure the server is active."
          onRetry={() => refetchProfile()}
        />
      </div>
    );
  }

  if (!profile) {
    return (
      <div>
        <PageHeader
          title="Candidate Profile"
          breadcrumbs={[{ label: "Candidate Profile" }]}
        />
        <EmptyState
          icon={<User className="w-6 h-6 text-terminal-muted" />}
          title="No Profile Found"
          description="No active candidate profile is registered in the database."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Candidate Profile"
        description="Verified credentials, matching preferences, and evidence records utilized by the AI tailoring engine"
        breadcrumbs={[{ label: "Candidate Profile" }]}
      />

      {/* Profile Readiness & Completion Widget */}
      <ProfileCompletionWidget
        profile={profile}
        preferences={preferences}
        skills={skills}
      />

      <div className="grid grid-cols-1 gap-6">
        {/* Core Profile Card */}
        <ProfileCard profile={profile} />

        {/* Preferences and Skills side-by-side on wide screens */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {preferences && <PreferencesCard preferences={preferences} />}
          {skills && <SkillsList skills={skills} />}
        </div>
      </div>
    </div>
  );
}
