import { useState } from "react";
import { Play, PlayCircle, RefreshCw } from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { usePipelineRuns } from "@/hooks/usePipelineRuns";
import { useCandidateProfile } from "@/hooks/useCandidateProfile";
import { PipelineRunsTable } from "../components/PipelineRunsTable";
import { PipelineRunDetailModal } from "../components/PipelineRunDetailModal";
import { TriggerRunModal } from "../components/TriggerRunModal";
import type { PipelineRunStatus } from "@/types/pipeline";

export function PipelineMonitoringPage() {
  const [selectedStatus, setSelectedStatus] = useState<PipelineRunStatus | undefined>(undefined);
  const [activeDetailId, setActiveDetailId] = useState<string | null>(null);
  const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);

  const { data: profile } = useCandidateProfile();
  const {
    data: runsResponse,
    isLoading,
    error,
    refetch,
    isFetching,
  } = usePipelineRuns({ status: selectedStatus });

  const runs = runsResponse?.items || [];
  const hasActiveRun = runs.some((r) => r.status === "PENDING" || r.status === "RUNNING");

  const filterTabs: Array<{ label: string; value?: PipelineRunStatus }> = [
    { label: "All Runs", value: undefined },
    { label: "Running", value: "RUNNING" },
    { label: "Completed", value: "COMPLETED" },
    { label: "Partially Done", value: "PARTIALLY_COMPLETED" },
    { label: "Failed", value: "FAILED" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline Runs"
        description="End-to-end orchestration monitoring coordinating discovery, matching, AI tailoring, and email delivery"
        breadcrumbs={[{ label: "Pipeline Runs" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="gap-1.5"
              title="Refresh runs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh</span>
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsTriggerModalOpen(true)}
              className="gap-1.5 shadow-xs"
              disabled={!profile}
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Trigger Pipeline Run</span>
            </Button>
          </div>
        }
      />

      {/* Active Run Banner */}
      {hasActiveRun && (
        <div className="p-3.5 rounded-card bg-terminal-primary/10 border border-terminal-primary/30 flex items-center justify-between text-xs text-terminal-dark shadow-subtle">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-terminal-primary/75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-terminal-primary" />
            </span>
            <span className="font-semibold font-display">
              An orchestrated pipeline run is currently processing in the background.
            </span>
          </div>
          <span className="text-terminal-muted font-mono text-[11px] hidden sm:inline">
            Auto-refreshing every 4 seconds
          </span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-1.5 pb-1 border-b border-terminal-warmBorder">
        {filterTabs.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setSelectedStatus(tab.value)}
            className={`px-3 py-1.5 rounded-card text-xs font-medium font-mono transition-colors ${
              selectedStatus === tab.value
                ? "bg-terminal-dark text-white font-semibold shadow-subtle"
                : "text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      {isLoading ? (
        <LoadingState message="Fetching pipeline execution records..." />
      ) : error ? (
        <ErrorState
          title="Could not load pipeline runs"
          message="Failed to retrieve pipeline runs from the backend. Please verify your connection."
          onRetry={() => refetch()}
        />
      ) : runs.length === 0 ? (
        <EmptyState
          icon={<PlayCircle className="w-6 h-6 text-terminal-muted" />}
          title="No Pipeline Runs Found"
          description={
            selectedStatus
              ? `No runs found matching status '${selectedStatus}'.`
              : "No pipeline runs have been executed yet. Click 'Trigger Pipeline Run' to start an orchestration cycle."
          }
          actionLabel={profile && !selectedStatus ? "Start First Run" : undefined}
          onAction={profile && !selectedStatus ? () => setIsTriggerModalOpen(true) : undefined}
        />
      ) : (
        <PipelineRunsTable
          runs={runs}
          onSelectRun={(id) => setActiveDetailId(id)}
        />
      )}

      {/* Modals */}
      {activeDetailId && (
        <PipelineRunDetailModal
          runId={activeDetailId}
          onClose={() => setActiveDetailId(null)}
        />
      )}

      {isTriggerModalOpen && profile && (
        <TriggerRunModal
          candidateProfileId={profile.id}
          onClose={() => setIsTriggerModalOpen(false)}
          onSuccess={(runId) => {
            setIsTriggerModalOpen(false);
            setActiveDetailId(runId);
            refetch();
          }}
        />
      )}
    </div>
  );
}

