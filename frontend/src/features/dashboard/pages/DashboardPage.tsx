import { Link } from "react-router-dom";
import { Play, User, PlayCircle, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/Button";
import { useCandidateProfile, useCandidateSkills } from "@/hooks/useCandidateProfile";
import { useSystemLiveness, useSystemReadiness } from "@/hooks/useSystemHealth";
import { usePipelineRuns } from "@/hooks/usePipelineRuns";
import { CandidateSummaryCard } from "../components/CandidateSummaryCard";
import { SystemReadinessCard } from "../components/SystemReadinessCard";
import { PipelineActivityCard } from "../components/PipelineActivityCard";

export function DashboardPage() {
  const { data: profile, isLoading: isProfileLoading } = useCandidateProfile();
  const { data: skills } = useCandidateSkills();
  const { data: readiness, isLoading: isReadinessLoading } = useSystemReadiness();
  const { data: liveness } = useSystemLiveness();
  const { data: runsResponse, isLoading: isRunsLoading } = usePipelineRuns({ page_size: 1 });

  const isLoading = isProfileLoading && isReadinessLoading && isRunsLoading;
  const latestRun = runsResponse?.items?.[0] || null;
  const totalRuns = runsResponse?.pagination?.total_items || 0;

  if (isLoading) {
    return <LoadingState message="Connecting to JobRadar AI workspace..." />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Intelligence Dashboard"
        description="Unified workspace overview connecting candidate evidence, active pipeline runs, and infrastructure telemetry"
        breadcrumbs={[]}
        actions={
          <div className="flex items-center gap-2">
            <Link to="/pipeline">
              <Button variant="primary" size="sm" className="gap-1.5 shadow-xs">
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Trigger Pipeline Run</span>
              </Button>
            </Link>
          </div>
        }
      />

      {/* Main 3-Column Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <CandidateSummaryCard
          profile={profile}
          skillsCount={skills?.length || 0}
        />

        <PipelineActivityCard
          latestRun={latestRun}
          totalRunsCount={totalRuns}
        />

        <SystemReadinessCard
          readiness={readiness}
          liveness={liveness}
          isLoading={isReadinessLoading}
        />
      </div>

      {/* Architectural Invariants & Navigation Quick Links */}
      <div className="rounded-card border border-terminal-warmBorder bg-terminal-warmSurface p-6 shadow-card">
        <h3 className="text-sm font-bold font-display text-terminal-dark mb-2 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-terminal-primary" />
          <span>Core System Invariants & Guarantees</span>
        </h3>
        <p className="text-xs text-terminal-muted leading-relaxed max-w-3xl mb-4 font-sans">
          JobRadar AI coordinates automated job discovery and application tailoring under strict integrity bounds.
          Matching operates via a 3-layer deterministic and LLM hierarchy, while resume tailoring enforces Evidence Vault claim validation to eliminate hallucinations.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-terminal-warmBorder">
          <Link
            to="/profile"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <User className="w-4 h-4 text-terminal-primary" />
              <div>
                <span className="text-xs font-semibold font-display text-terminal-dark block">Candidate Profile & Skills</span>
                <span className="text-[11px] text-terminal-muted">Edit summary, credentials, and search preferences</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium">&rarr;</span>
          </Link>

          <Link
            to="/pipeline"
            className="flex items-center justify-between p-3 rounded-card border border-terminal-warmBorder bg-terminal-warm/60 hover:bg-terminal-warm transition-colors"
          >
            <div className="flex items-center gap-2.5">
              <PlayCircle className="w-4 h-4 text-terminal-primary" />
              <div>
                <span className="text-xs font-semibold font-display text-terminal-dark block">Pipeline Runs</span>
                <span className="text-[11px] text-terminal-muted">Inspect end-to-end execution, discovery, and notification status</span>
              </div>
            </div>
            <span className="text-xs text-terminal-primary font-mono font-medium">&rarr;</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

