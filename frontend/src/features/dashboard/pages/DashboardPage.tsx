import { useState } from "react";
import { Link } from "react-router-dom";
import { User, PlayCircle, ShieldCheck, FileText, Sparkles } from "lucide-react";
import { LoadingState } from "@/components/common/LoadingState";
import {
  useCandidatePreferences,
  useCandidateProfile,
  useCandidateSkills,
} from "@/hooks/useCandidateProfile";
import { useSystemLiveness, useSystemReadiness } from "@/hooks/useSystemHealth";
import { usePipelineRuns } from "@/hooks/usePipelineRuns";
import { useJobs } from "@/hooks/useJobs";
import { useMatches } from "@/hooks/useMatches";
import { calculateProfileCompletion } from "@/features/candidate/utils/profileCompletion";
import { TriggerRunModal } from "@/features/pipeline/components/TriggerRunModal";
import { PipelineRunDetailModal } from "@/features/pipeline/components/PipelineRunDetailModal";
import { DashboardGreeting } from "../components/DashboardGreeting";
import { DashboardMetricsOverview } from "../components/DashboardMetricsOverview";
import { RecentJobsCard } from "../components/RecentJobsCard";
import { RecentMatchesCard } from "../components/RecentMatchesCard";
import { CandidateSummaryCard } from "../components/CandidateSummaryCard";
import { SystemReadinessCard } from "../components/SystemReadinessCard";
import { PipelineActivityCard } from "../components/PipelineActivityCard";

export function DashboardPage() {
  const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const { data: profile, isLoading: isProfileLoading } = useCandidateProfile();
  const { data: preferences } = useCandidatePreferences();
  const { data: skills } = useCandidateSkills();
  const { data: readiness, isLoading: isReadinessLoading } = useSystemReadiness();
  const { data: liveness } = useSystemLiveness();

  const {
    data: runsResponse,
    isLoading: isRunsLoading,
    refetch: refetchRuns,
  } = usePipelineRuns({ page_size: 5 });

  const { data: jobsResponse } = useJobs({ page_size: 5 });
  const { data: matchesResponse } = useMatches({ page_size: 5 });

  const isLoading = isProfileLoading && isReadinessLoading && isRunsLoading;

  const runs = runsResponse?.items || [];
  const latestRun = runs[0] || null;
  const totalRuns = runsResponse?.pagination?.total_items || 0;
  const totalJobs = jobsResponse?.pagination?.total_items || 0;
  const totalMatches = matchesResponse?.pagination?.total_items || 0;
  const hasActiveRun = runs.some((r) => r.status === "PENDING" || r.status === "RUNNING");

  const { score: readinessScore } = calculateProfileCompletion(profile, preferences, skills);

  if (isLoading) {
    return <LoadingState message="Connecting to JobRadar AI intelligence workspace..." />;
  }

  return (
    <div className="space-y-6">
      {/* 1. Personalized Greeting & Fast Action Console */}
      <DashboardGreeting
        profile={profile}
        onTriggerRun={() => setIsTriggerModalOpen(true)}
      />

      {/* 2. Top-Level Operational Metrics Overview */}
      <DashboardMetricsOverview
        totalJobs={totalJobs}
        totalMatches={totalMatches}
        readinessScore={readinessScore}
        totalRuns={totalRuns}
        hasActiveRun={hasActiveRun}
      />

      {/* 3. Main Dashboard Intelligence & Pipeline Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Job Discoveries & Scored Matches (7 cols on lg) */}
        <div className="lg:col-span-7 space-y-6">
          <RecentMatchesCard />
          <RecentJobsCard />
        </div>

        {/* Right Column: Candidate Evidence & Infrastructure Telemetry (5 cols on lg) */}
        <div className="lg:col-span-5 space-y-6">
          <CandidateSummaryCard
            profile={profile}
            skillsCount={skills?.length || 0}
          />

          <PipelineActivityCard
            latestRun={latestRun}
            totalRunsCount={totalRuns}
            recentRuns={runs}
            onSelectRun={(runId) => setSelectedRunId(runId)}
            onTriggerRun={() => setIsTriggerModalOpen(true)}
          />

          <SystemReadinessCard
            readiness={readiness}
            liveness={liveness}
            isLoading={isReadinessLoading}
          />
        </div>
      </div>

      {/* 4. Architectural Invariants & Navigation Quick Links */}
      <div className="rounded-card border border-terminal-warmBorder bg-terminal-warmSurface p-6 shadow-card">
        <h3 className="text-sm font-bold font-display text-terminal-dark mb-2 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-terminal-primary" />
          <span>Core System Invariants & Guarantees</span>
        </h3>
        <p className="text-xs text-terminal-muted leading-relaxed max-w-3xl mb-4 font-sans">
          JobRadar AI coordinates automated job discovery and application tailoring under strict integrity bounds.
          Matching operates via a 3-layer deterministic and LLM hierarchy, while resume tailoring enforces Evidence Vault claim validation to eliminate hallucinations.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-terminal-warmBorder">
          <Link
            to="/profile"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <User className="w-4 h-4 text-terminal-primary shrink-0" />
              <div className="truncate">
                <span className="text-xs font-semibold font-display text-terminal-dark block truncate">Candidate Profile</span>
                <span className="text-[11px] text-terminal-muted truncate block">Preferences & skills</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium ml-2">&rarr;</span>
          </Link>

          <Link
            to="/resumes"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <FileText className="w-4 h-4 text-terminal-primary shrink-0" />
              <div className="truncate">
                <span className="text-xs font-semibold font-display text-terminal-dark block truncate">Master Resumes</span>
                <span className="text-[11px] text-terminal-muted truncate block">Upload & AST parser</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium ml-2">&rarr;</span>
          </Link>

          <Link
            to="/tailored-resumes"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <Sparkles className="w-4 h-4 text-terminal-primary shrink-0" />
              <div className="truncate">
                <span className="text-xs font-semibold font-display text-terminal-dark block truncate">Tailored Resumes</span>
                <span className="text-[11px] text-terminal-muted truncate block">ATS PDFs & audits</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium ml-2">&rarr;</span>
          </Link>

          <Link
            to="/pipeline"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5 overflow-hidden">
              <PlayCircle className="w-4 h-4 text-terminal-primary shrink-0" />
              <div className="truncate">
                <span className="text-xs font-semibold font-display text-terminal-dark block truncate">Pipeline Runs</span>
                <span className="text-[11px] text-terminal-muted truncate block">End-to-end telemetry</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium ml-2">&rarr;</span>
          </Link>
        </div>
      </div>

      {/* Trigger Run Modal */}
      {isTriggerModalOpen && profile && (
        <TriggerRunModal
          candidateProfileId={profile.id}
          onClose={() => setIsTriggerModalOpen(false)}
          onSuccess={(runId) => {
            setIsTriggerModalOpen(false);
            setSelectedRunId(runId);
            refetchRuns();
          }}
        />
      )}

      {/* Pipeline Detail Modal */}
      {selectedRunId && (
        <PipelineRunDetailModal
          runId={selectedRunId}
          onClose={() => setSelectedRunId(null)}
        />
      )}
    </div>
  );
}
