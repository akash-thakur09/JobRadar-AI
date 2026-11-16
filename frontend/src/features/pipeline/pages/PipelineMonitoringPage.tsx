import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Play,
  PlayCircle,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  FileCheck,
  Send,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/Button";
import { usePipelineRuns } from "@/hooks/usePipelineRuns";
import { useCandidateProfile } from "@/hooks/useCandidateProfile";
import { PipelineRunsTable } from "../components/PipelineRunsTable";
import { TriggerRunModal } from "../components/TriggerRunModal";
import type { PipelineRunStatus } from "@/types/pipeline";

export function PipelineMonitoringPage() {
  const navigate = useNavigate();
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedStatus, setSelectedStatus] = useState<PipelineRunStatus | undefined>(undefined);
  const [isTriggerModalOpen, setIsTriggerModalOpen] = useState(false);

  const { data: profile } = useCandidateProfile();

  // Paginated runs list
  const {
    data: runsResponse,
    isLoading,
    error,
    refetch,
    isFetching,
  } = usePipelineRuns({
    status: selectedStatus,
    page: currentPage,
    page_size: 10,
  });

  // Global metric queries (server-side counts) to avoid pagination page calculation bias
  const { data: totalRunsData } = usePipelineRuns({ page: 1, page_size: 1 });
  const { data: completedRunsData } = usePipelineRuns({ status: "COMPLETED", page: 1, page_size: 1 });
  const { data: failedRunsData } = usePipelineRuns({ status: "FAILED", page: 1, page_size: 1 });
  const { data: runningRunsData } = usePipelineRuns({ status: "RUNNING", page: 1, page_size: 1 });
  const { data: pendingRunsData } = usePipelineRuns({ status: "PENDING", page: 1, page_size: 1 });

  const totalRuns = totalRunsData?.pagination?.total_items ?? 0;
  const completedRuns = completedRunsData?.pagination?.total_items ?? 0;
  const failedRuns = failedRunsData?.pagination?.total_items ?? 0;
  const activeRuns =
    (runningRunsData?.pagination?.total_items ?? 0) +
    (pendingRunsData?.pagination?.total_items ?? 0);

  const runs = useMemo(() => runsResponse?.items || [], [runsResponse]);
  const pagination = runsResponse?.pagination;
  const latestRun = runs[0] || null;

  const hasActiveRun = runs.some((r) => r.status === "PENDING" || r.status === "RUNNING");

  const filterTabs: Array<{ label: string; value?: PipelineRunStatus; count?: number }> = [
    { label: "All Runs", value: undefined, count: totalRuns },
    { label: "Running", value: "RUNNING", count: runningRunsData?.pagination?.total_items },
    { label: "Completed", value: "COMPLETED", count: completedRuns },
    { label: "Partially Done", value: "PARTIALLY_COMPLETED" },
    { label: "Failed", value: "FAILED", count: failedRuns },
  ];

  const handleStatusChange = (val?: PipelineRunStatus) => {
    setSelectedStatus(val);
    setCurrentPage(1);
  };

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

      {/* Global Operational Metrics Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Total Executions</span>
            <Layers className="w-4 h-4 text-terminal-muted" />
          </div>
          <div className="text-2xl font-bold font-mono text-terminal-dark">{totalRuns}</div>
          <span className="text-[11px] text-terminal-muted font-mono mt-1 block">
            Orchestrated pipeline cycles
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Successful Executions</span>
            <CheckCircle2 className="w-4 h-4 text-[#5BCB8A]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#1B5E20]">{completedRuns}</div>
          <span className="text-[11px] text-[#2E7D32] font-mono mt-1 block">
            End-to-end completed cycles
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Active / Pending</span>
            <Clock className="w-4 h-4 text-[#8DB4FF]" />
          </div>
          <div className="text-2xl font-bold font-mono text-[#0039A6]">{activeRuns}</div>
          <span className="text-[11px] text-terminal-muted font-mono mt-1 block">
            Workers actively processing
          </span>
        </div>

        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
          <div className="flex items-center justify-between text-terminal-muted mb-2">
            <span className="text-xs font-mono font-medium">Failed Executions</span>
            <AlertTriangle className="w-4 h-4 text-[#E05A47]" />
          </div>
          <div className="text-2xl font-bold font-mono text-terminal-errorText">{failedRuns}</div>
          <span className="text-[11px] text-terminal-errorText font-mono mt-1 block">
            Pipeline errors or interruptions
          </span>
        </div>
      </div>

      {/* Latest Cycle Throughput Telemetry */}
      {latestRun && (
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold font-mono uppercase tracking-wider text-terminal-muted">
                Latest Pipeline Telemetry
              </span>
              <span className="font-mono text-xs text-terminal-dark font-medium">
                (Run {latestRun.id.slice(0, 8)}...)
              </span>
            </div>
            <button
              onClick={() => navigate(`/pipeline/${latestRun.id}`)}
              className="text-xs text-terminal-primary hover:underline font-mono"
            >
              Inspect Complete Metrics →
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
            <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/60">
              <div className="flex items-center justify-center gap-1.5 text-terminal-muted mb-1">
                <Play className="w-3.5 h-3.5 text-terminal-primary" />
                <span className="font-mono text-[10px] uppercase font-bold">Discovered</span>
              </div>
              <span className="font-bold text-base font-mono text-terminal-dark">
                {latestRun.jobs_discovered}
              </span>
            </div>

            <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/60">
              <div className="flex items-center justify-center gap-1.5 text-terminal-muted mb-1">
                <Sparkles className="w-3.5 h-3.5 text-[#8DB4FF]" />
                <span className="font-mono text-[10px] uppercase font-bold">Qualified</span>
              </div>
              <span className="font-bold text-base font-mono text-[#3B4D00]">
                {latestRun.matches_qualified}
              </span>
            </div>

            <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/60">
              <div className="flex items-center justify-center gap-1.5 text-terminal-muted mb-1">
                <FileCheck className="w-3.5 h-3.5 text-[#5BCB8A]" />
                <span className="font-mono text-[10px] uppercase font-bold">Tailored PDFs</span>
              </div>
              <span className="font-bold text-base font-mono text-terminal-dark">
                {latestRun.resumes_generated}
              </span>
            </div>

            <div className="p-2.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder/60">
              <div className="flex items-center justify-center gap-1.5 text-terminal-muted mb-1">
                <Send className="w-3.5 h-3.5 text-[#E6B84D]" />
                <span className="font-mono text-[10px] uppercase font-bold">Emails Sent</span>
              </div>
              <span className="font-bold text-base font-mono text-terminal-dark">
                {latestRun.notifications_sent}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Active Run Pulsing Banner */}
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
            onClick={() => handleStatusChange(tab.value)}
            className={`px-3 py-1.5 rounded-card text-xs font-medium font-mono transition-colors flex items-center gap-1.5 ${
              selectedStatus === tab.value
                ? "bg-terminal-dark text-white font-semibold shadow-subtle"
                : "text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`px-1.5 py-0.2 rounded text-[10px] ${
                  selectedStatus === tab.value
                    ? "bg-white/20 text-white"
                    : "bg-terminal-warm text-terminal-muted"
                }`}
              >
                {tab.count}
              </span>
            )}
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
        <div className="space-y-4">
          <PipelineRunsTable
            runs={runs}
            onSelectRun={(id) => navigate(`/pipeline/${id}`)}
          />

          {/* Pagination Controls */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-2 text-xs font-mono text-terminal-muted">
              <span>
                Showing page {pagination.page} of {pagination.total_pages} ({pagination.total_items} total runs)
              </span>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={!pagination.has_prev}
                  className="gap-1 h-8 px-2.5 text-xs"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => p + 1)}
                  disabled={!pagination.has_next}
                  className="gap-1 h-8 px-2.5 text-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Trigger Run Modal */}
      {isTriggerModalOpen && profile && (
        <TriggerRunModal
          candidateProfileId={profile.id}
          onClose={() => setIsTriggerModalOpen(false)}
          onSuccess={(runId) => {
            setIsTriggerModalOpen(false);
            navigate(`/pipeline/${runId}`);
            refetch();
          }}
        />
      )}
    </div>
  );
}
