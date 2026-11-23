import { useState } from "react";
import { Eye, StopCircle } from "lucide-react";
import type { PipelineRunSummary } from "@/types/pipeline";
import { StatusBadge } from "./StatusBadge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { useCancelPipelineRun } from "@/hooks/usePipelineRuns";

export interface PipelineRunsTableProps {
  runs: PipelineRunSummary[];
  onSelectRun: (runId: string) => void;
}

export function PipelineRunsTable({ runs, onSelectRun }: PipelineRunsTableProps) {
  const cancelMutation = useCancelPipelineRun();
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const handleCancel = async (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to cancel this active pipeline run?")) {
      return;
    }
    setCancellingId(runId);
    try {
      await cancelMutation.mutateAsync(runId);
    } finally {
      setCancellingId(null);
    }
  };

  return (
    <div className="overflow-x-auto rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-card">
      <table className="w-full text-left text-xs text-terminal-dark">
        <thead className="bg-terminal-warm border-b border-terminal-warmBorder text-[10px] font-semibold text-terminal-muted uppercase font-mono tracking-wider">
          <tr>
            <th scope="col" className="px-4 py-3">Run ID</th>
            <th scope="col" className="px-4 py-3">Trigger</th>
            <th scope="col" className="px-4 py-3">Status</th>
            <th scope="col" className="px-4 py-3 text-center">Jobs</th>
            <th scope="col" className="px-4 py-3 text-center">Matches</th>
            <th scope="col" className="px-4 py-3 text-center">Tailored</th>
            <th scope="col" className="px-4 py-3 text-center">Emails</th>
            <th scope="col" className="px-4 py-3">Created</th>
            <th scope="col" className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-terminal-warmBorder/60">
          {runs.map((run) => {
            const isActive = run.status === "PENDING" || run.status === "RUNNING";

            return (
              <tr
                key={run.id}
                onClick={() => onSelectRun(run.id)}
                className="hover:bg-terminal-warm/60 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3 font-mono font-medium text-terminal-dark truncate max-w-[140px]">
                  {run.id.slice(0, 8)}...
                </td>
                <td className="px-4 py-3 font-mono">
                  <span className="font-semibold text-terminal-dark">{run.trigger_type}</span>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={run.status} />
                </td>
                <td className="px-4 py-3 text-center font-mono font-medium text-terminal-dark">
                  {run.jobs_discovered}
                </td>
                <td className="px-4 py-3 text-center font-mono">
                  <span className={`px-2 py-0.5 rounded font-mono font-bold ${run.matches_qualified > 0 ? "bg-[#D6FF3F]/25 text-[#3B4D00]" : "text-terminal-muted"}`}>
                    {run.matches_qualified}
                  </span>
                </td>
                <td className="px-4 py-3 text-center font-mono font-medium text-terminal-dark">
                  {run.resumes_generated}
                </td>
                <td className="px-4 py-3 text-center font-mono font-medium text-terminal-dark">
                  {run.notifications_sent}
                </td>
                <td className="px-4 py-3 text-terminal-muted font-mono whitespace-nowrap">
                  {formatDate(run.created_at)}
                </td>
                <td className="px-4 py-3 text-right whitespace-nowrap">
                  <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onSelectRun(run.id)}
                      className="h-7 px-2 text-xs"
                      title="Inspect Run"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1 text-terminal-muted" />
                      <span>Details</span>
                    </Button>

                    {isActive && (
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={(e) => handleCancel(e, run.id)}
                        isLoading={cancellingId === run.id}
                        className="h-7 px-2 text-xs"
                        title="Cancel Active Run"
                      >
                        <StopCircle className="w-3.5 h-3.5 mr-1" />
                        <span>Cancel</span>
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

