import { X, Calendar, AlertTriangle, Play, CheckCircle2, FileText, Bell, Layers } from "lucide-react";
import { usePipelineRun } from "@/hooks/usePipelineRuns";
import { StatusBadge } from "./StatusBadge";
import { Spinner } from "@/components/ui/Spinner";
import { formatDate } from "@/lib/utils";

export interface PipelineRunDetailModalProps {
  runId: string;
  onClose: () => void;
}

export function PipelineRunDetailModal({ runId, onClose }: PipelineRunDetailModalProps) {
  const { data: run, isLoading, error } = usePipelineRun(runId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-terminal-dark/70 backdrop-blur-xs">
      <div className="bg-terminal-warmSurface rounded-card shadow-dropdown border border-terminal-warmBorder max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-terminal-warmBorder sticky top-0 bg-terminal-warmSurface/95 backdrop-blur-xs z-10">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold font-display text-terminal-dark">Pipeline Run Details</h3>
              {run && <StatusBadge status={run.status} />}
            </div>
            <p className="text-xs text-terminal-muted font-mono mt-0.5 truncate">ID: {runId}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-terminal-muted hover:text-terminal-dark hover:bg-terminal-warm transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6">
          {isLoading && (
            <div className="py-12 flex justify-center">
              <Spinner size="lg" label="Loading pipeline execution details..." />
            </div>
          )}

          {error && (
            <div className="p-4 rounded-card bg-terminal-error/10 border border-terminal-error/30 text-terminal-errorText text-xs font-mono">
              Failed to load details for this pipeline run.
            </div>
          )}

          {run && (
            <>
              {/* Error Alert if present */}
              {run.error_summary && (
                <div className="p-3.5 rounded-card bg-[#E6B84D]/15 border border-[#E6B84D]/40 flex items-start gap-2.5 text-xs text-[#6E4C00] font-mono">
                  <AlertTriangle className="w-4 h-4 text-[#6E4C00] shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Execution Notice: </span>
                    <span>{run.error_summary}</span>
                  </div>
                </div>
              )}

              {/* Execution Timestamps & Context */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder text-xs">
                <div>
                  <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block">Trigger</span>
                  <span className="font-semibold font-mono text-terminal-dark">{run.trigger_type}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block">Started</span>
                  <span className="text-terminal-dark font-mono font-medium">{formatDate(run.started_at)}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block">Completed</span>
                  <span className="text-terminal-dark font-mono font-medium">{formatDate(run.completed_at)}</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-mono font-bold text-terminal-muted block">Created</span>
                  <span className="text-terminal-dark font-mono font-medium">{formatDate(run.created_at)}</span>
                </div>
              </div>

              {/* Operational Metrics by Phase */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold uppercase font-mono tracking-wider text-terminal-muted">
                  Phase Execution Metrics
                </h4>

                {/* Phase 1 & 2 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface">
                    <div className="flex items-center gap-2 mb-3 text-xs font-semibold font-display text-terminal-dark">
                      <Play className="w-3.5 h-3.5 text-terminal-primary" />
                      <span>Phase 1: Job Discovery</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Discovered</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_discovered}</span>
                      </div>
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Created</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_created}</span>
                      </div>
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Updated</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_updated}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface">
                    <div className="flex items-center gap-2 mb-3 text-xs font-semibold font-display text-terminal-dark">
                      <Layers className="w-3.5 h-3.5 text-terminal-primary" />
                      <span>Phase 2: Normalization</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Normalized</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_normalized}</span>
                      </div>
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Deduplicated</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_deduplicated}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Phase 3 & 4 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface">
                    <div className="flex items-center gap-2 mb-3 text-xs font-semibold font-display text-terminal-dark">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#185C36]" />
                      <span>Phase 3: Matching</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Evaluated</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.jobs_evaluated}</span>
                      </div>
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Matches</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.matches_created}</span>
                      </div>
                      <div className="bg-[#D6FF3F]/20 p-2 rounded-card border border-[#B8E61A]/50">
                        <span className="text-[10px] text-[#3B4D00] font-mono font-bold block">Qualified</span>
                        <span className="font-bold text-sm font-mono text-[#3B4D00]">{run.metrics.matches_qualified}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface">
                    <div className="flex items-center gap-2 mb-3 text-xs font-semibold font-display text-terminal-dark">
                      <FileText className="w-3.5 h-3.5 text-terminal-primary" />
                      <span>Phase 4: Tailoring & PDF</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-center">
                      <div className="bg-[#FF5A36]/15 p-2 rounded-card border border-[#FF5A36]/30">
                        <span className="text-[10px] text-[#8F230D] font-mono font-bold block">Resumes Built</span>
                        <span className="font-bold text-sm font-mono text-[#8F230D]">{run.metrics.resumes_generated}</span>
                      </div>
                      <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                        <span className="text-[10px] text-terminal-muted font-mono block">Failures</span>
                        <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.resumes_failed}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Phase 5 */}
                <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface">
                  <div className="flex items-center gap-2 mb-3 text-xs font-semibold font-display text-terminal-dark">
                    <Bell className="w-3.5 h-3.5 text-terminal-primary" />
                    <span>Phase 5: Notification Delivery</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    <div className="bg-[#5BCB8A]/15 p-2 rounded-card border border-[#5BCB8A]/40">
                      <span className="text-[10px] text-[#185C36] font-mono font-bold block">Emails Sent</span>
                      <span className="font-bold text-sm font-mono text-[#185C36]">{run.metrics.notifications_sent}</span>
                    </div>
                    <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                      <span className="text-[10px] text-terminal-muted font-mono block">Failed Emails</span>
                      <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.notifications_failed}</span>
                    </div>
                    <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                      <span className="text-[10px] text-terminal-muted font-mono block">LLM Analyses</span>
                      <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.semantic_analyses_completed}</span>
                    </div>
                    <div className="bg-terminal-warm/60 p-2 rounded-card border border-terminal-warmBorder/60">
                      <span className="text-[10px] text-terminal-muted font-mono block">LLM Degradations</span>
                      <span className="font-bold text-sm font-mono text-terminal-dark">{run.metrics.semantic_analyses_failed}</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-terminal-warmBorder bg-terminal-warm rounded-b-card flex items-center justify-between text-xs text-terminal-muted font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            Last updated: {formatDate(run?.updated_at)}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder text-terminal-dark font-medium hover:bg-terminal-warm transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

