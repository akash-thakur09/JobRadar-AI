import { useParams } from "react-router-dom";
import {
  Play,
  AlertTriangle,
  FileCheck,
  Briefcase,
  Sparkles,
  Layers,
  StopCircle,
  Bell,
  RefreshCw,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "../components/StatusBadge";
import { usePipelineRun, useCancelPipelineRun } from "@/hooks/usePipelineRuns";
import { formatDate } from "@/lib/utils";

function calculateDuration(
  startStr: string | null | undefined,
  endStr: string | null | undefined
): string {
  if (!startStr) return "Not started";
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  const diffSec = Math.max(0, Math.floor((end - start) / 1000));

  if (diffSec < 60) return `${diffSec}s`;
  const mins = Math.floor(diffSec / 60);
  const secs = diffSec % 60;
  return `${mins}m ${secs}s`;
}

export function PipelineRunDetailPage() {
  const { runId = "" } = useParams<{ runId: string }>();

  const { data: run, isLoading, error, refetch, isFetching } = usePipelineRun(runId);
  const cancelMutation = useCancelPipelineRun();

  const isActive = run?.status === "PENDING" || run?.status === "RUNNING";

  const handleCancel = async () => {
    if (!run || !isActive) return;
    if (!window.confirm("Are you sure you want to cancel this active pipeline run?")) {
      return;
    }
    await cancelMutation.mutateAsync(run.id);
  };

  if (isLoading) {
    return <LoadingState message="Loading pipeline execution telemetry..." />;
  }

  if (error || !run) {
    return (
      <ErrorState
        title="Pipeline Run Not Found"
        message="Unable to locate the specified pipeline execution record."
        onRetry={() => refetch()}
      />
    );
  }

  const duration = calculateDuration(run.started_at, run.completed_at);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline Execution Run"
        description="Comprehensive operational telemetry across discovery, matching, AI tailoring, and email delivery"
        breadcrumbs={[
          { label: "Pipeline Runs", href: "/pipeline" },
          { label: `${run.id.slice(0, 8)}...` },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="gap-1.5"
              title="Refresh run status"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </Button>

            {isActive && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
                className="gap-1.5 shadow-xs"
              >
                <StopCircle className="w-3.5 h-3.5" />
                <span>{cancelMutation.isPending ? "Cancelling..." : "Cancel Run"}</span>
              </Button>
            )}
          </div>
        }
      />

      {/* Active Run Real-Time Notice */}
      {isActive && (
        <div className="p-4 rounded-card bg-terminal-primary/10 border border-terminal-primary/30 flex items-center justify-between text-xs text-terminal-dark shadow-subtle">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-terminal-primary/75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-terminal-primary" />
            </span>
            <span className="font-semibold font-display">
              Pipeline run is actively executing. Telemetry is auto-refreshing in real time.
            </span>
          </div>
          <span className="text-terminal-muted font-mono text-[11px] hidden sm:inline">
            Status: {run.status}
          </span>
        </div>
      )}

      {/* Hero Overview Card */}
      <div className="p-5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-terminal-warmBorder">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-lg font-bold font-display text-terminal-dark">
                Execution {run.id.slice(0, 8)}
              </h2>
              <StatusBadge status={run.status} />
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-terminal-warm border border-terminal-warmBorder text-terminal-dark">
                Trigger: {run.trigger_type}
              </span>
            </div>
            <p className="text-xs text-terminal-muted font-mono mt-0.5">
              Run UUID: {run.id}
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-[10px] uppercase font-bold text-terminal-muted block">
                Total Duration
              </span>
              <span className="font-bold text-sm text-terminal-dark">{duration}</span>
            </div>
          </div>
        </div>

        {/* Execution Timestamps Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 text-xs">
          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Created At
            </span>
            <span className="font-mono text-terminal-dark">{formatDate(run.created_at)}</span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Started At
            </span>
            <span className="font-mono text-terminal-dark">
              {run.started_at ? formatDate(run.started_at) : "—"}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Completed At
            </span>
            <span className="font-mono text-terminal-dark">
              {run.completed_at ? formatDate(run.completed_at) : isActive ? "Running..." : "—"}
            </span>
          </div>

          <div>
            <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block mb-0.5">
              Candidate Profile ID
            </span>
            <span className="font-mono text-terminal-muted truncate block max-w-[160px]" title={run.candidate_profile_id}>
              {run.candidate_profile_id}
            </span>
          </div>
        </div>
      </div>

      {/* Error Notice if present */}
      {run.error_summary && (
        <div className="p-4 rounded-card border border-terminal-error/40 bg-terminal-error/10 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-terminal-errorText shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs font-mono">
            <span className="font-bold text-terminal-errorText font-display block">
              Execution Error Summary
            </span>
            <p className="text-terminal-errorText whitespace-pre-wrap">{run.error_summary}</p>
          </div>
        </div>
      )}

      {/* Stage-by-Stage Results Telemetry */}
      <div className="space-y-4">
        <h3 className="text-sm font-bold uppercase font-mono tracking-wider text-terminal-muted">
          Stage-by-Stage Operational Results
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Phase 1: Discovery */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <Play className="w-4 h-4 text-terminal-primary" />
              <span>Phase 1: Job Discovery</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Discovered</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_discovered}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Created</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_created}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Updated</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_updated}
                </span>
              </div>
            </div>
          </div>

          {/* Phase 2: Normalization */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <Layers className="w-4 h-4 text-[#8DB4FF]" />
              <span>Phase 2: Normalization & Canonical</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Normalized</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_normalized}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Deduplicated</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_deduplicated}
                </span>
              </div>
            </div>
          </div>

          {/* Phase 3: Matching */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <Sparkles className="w-4 h-4 text-[#D6FF3F]" />
              <span>Phase 3: Deterministic Matching</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Evaluated</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.jobs_evaluated}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Matches</span>
                <span className="font-bold text-base font-mono text-terminal-dark">
                  {run.metrics.matches_created}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Qualified</span>
                <span className="font-bold text-base font-mono text-[#3B4D00]">
                  {run.metrics.matches_qualified}
                </span>
              </div>
            </div>
          </div>

          {/* Phase 4: Semantic Analysis */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <Briefcase className="w-4 h-4 text-terminal-primary" />
              <span>Phase 4: LLM Semantic Analysis</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Completed</span>
                <span className="font-bold text-base font-mono text-[#1B5E20]">
                  {run.metrics.semantic_analyses_completed}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Failed / Skipped</span>
                <span className="font-bold text-base font-mono text-terminal-muted">
                  {run.metrics.semantic_analyses_failed}
                </span>
              </div>
            </div>
          </div>

          {/* Phase 5: Tailored Resumes */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <FileCheck className="w-4 h-4 text-[#5BCB8A]" />
              <span>Phase 5: Resume Tailoring & PDF</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">PDFs Generated</span>
                <span className="font-bold text-base font-mono text-[#1B5E20]">
                  {run.metrics.resumes_generated}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Tailoring Failed</span>
                <span className="font-bold text-base font-mono text-terminal-muted">
                  {run.metrics.resumes_failed}
                </span>
              </div>
            </div>
          </div>

          {/* Phase 6: Notifications */}
          <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card">
            <div className="flex items-center gap-2 mb-3 text-xs font-bold font-display text-terminal-dark">
              <Bell className="w-4 h-4 text-[#E6B84D]" />
              <span>Phase 6: Notifications & Delivery</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Emails Sent</span>
                <span className="font-bold text-base font-mono text-[#1B5E20]">
                  {run.metrics.notifications_sent}
                </span>
              </div>
              <div className="bg-terminal-warm/60 p-2.5 rounded-card border border-terminal-warmBorder/60">
                <span className="text-[10px] text-terminal-muted font-mono block">Delivery Failed</span>
                <span className="font-bold text-base font-mono text-terminal-muted">
                  {run.metrics.notifications_failed}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata / Telemetry Inspector if available */}
      {run.metadata && Object.keys(run.metadata).length > 0 && (
        <div className="p-4 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder shadow-card space-y-2">
          <span className="text-xs font-bold font-mono uppercase tracking-wider text-terminal-muted block">
            Run Metadata & Configuration
          </span>
          <pre className="p-3 rounded-card bg-terminal-dark text-white font-mono text-xs overflow-x-auto">
            {JSON.stringify(run.metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
