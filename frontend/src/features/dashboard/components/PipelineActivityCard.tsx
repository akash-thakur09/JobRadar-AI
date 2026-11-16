import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  PlayCircle,
  Layers,
  Bell,
  FileText,
  AlertTriangle,
  Play,
  Clock,
} from "lucide-react";
import type { PipelineRunSummary } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/features/pipeline/components/StatusBadge";
import { formatDate } from "@/lib/utils";

export interface PipelineActivityCardProps {
  latestRun: PipelineRunSummary | null | undefined;
  totalRunsCount: number;
  recentRuns?: PipelineRunSummary[];
  onSelectRun?: (runId: string) => void;
  onTriggerRun?: () => void;
}

export function PipelineActivityCard({
  latestRun,
  totalRunsCount,
  recentRuns = [],
  onSelectRun,
  onTriggerRun,
}: PipelineActivityCardProps) {
  if (!latestRun) {
    return (
      <Card className="h-full flex flex-col justify-between">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="w-4 h-4 text-terminal-primary" />
            <span>Pipeline Activity</span>
          </CardTitle>
          <CardDescription>Automated discovery and tailoring orchestration</CardDescription>
        </CardHeader>
        <CardContent className="text-center py-8">
          <div className="w-10 h-10 rounded-full bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted mx-auto mb-2">
            <PlayCircle className="w-5 h-5" />
          </div>
          <p className="text-xs text-terminal-muted mb-4 font-mono">No pipeline runs have been executed yet.</p>
          {onTriggerRun ? (
            <Button variant="primary" size="sm" onClick={onTriggerRun} className="gap-1.5 shadow-subtle">
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Trigger First Run</span>
            </Button>
          ) : (
            <Link to="/pipeline">
              <Button variant="outline" size="sm">Go to Pipeline Monitoring</Button>
            </Link>
          )}
        </CardContent>
      </Card>
    );
  }

  // Display other recent runs if available (excluding latest)
  const secondaryRuns = recentRuns.filter((r) => r.id !== latestRun.id).slice(0, 3);

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="w-4 h-4 text-terminal-primary" />
            <span>Pipeline Orchestration</span>
          </CardTitle>
          <CardDescription>
            {totalRunsCount} total execution{totalRunsCount === 1 ? "" : "s"} &bull; Discovery to Email delivery
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {onTriggerRun && (
            <Button
              variant="outline"
              size="sm"
              onClick={onTriggerRun}
              className="h-7 px-2 text-xs gap-1 hidden sm:inline-flex"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>Run</span>
            </Button>
          )}
          <Link to="/pipeline">
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1 text-terminal-primary hover:text-terminal-primaryHover">
              <span>All Runs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </Link>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 flex-1">
        {/* Latest Run Header Card */}
        <div
          onClick={() => onSelectRun?.(latestRun.id)}
          className={`p-3.5 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder ${
            onSelectRun ? "cursor-pointer hover:border-terminal-muted transition-colors" : ""
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-terminal-dark">
                {latestRun.id.slice(0, 8)}...
              </span>
              <StatusBadge status={latestRun.status} />
            </div>
            <span className="text-[10px] font-mono text-terminal-muted uppercase font-bold">
              Latest Run
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] font-mono text-terminal-muted pt-1">
            <span>Trigger: <strong className="text-terminal-dark font-mono">{latestRun.trigger_type}</strong></span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-terminal-muted" />
              {formatDate(latestRun.started_at || latestRun.created_at)}
            </span>
          </div>

          {/* 4 Core Phase Counters */}
          <div className="grid grid-cols-4 gap-1.5 text-center mt-3 pt-2.5 border-t border-terminal-warmBorder/60">
            <div className="p-1.5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
              <Layers className="w-3 h-3 mx-auto text-terminal-muted mb-0.5" />
              <span className="text-[9px] text-terminal-muted uppercase font-mono font-bold block truncate">Jobs</span>
              <span className="font-bold text-xs font-mono text-terminal-dark">{latestRun.jobs_discovered}</span>
            </div>

            <div className="p-1.5 rounded-card bg-[#D6FF3F]/20 border border-[#B8E61A]/50">
              <CheckCircle2 className="w-3 h-3 mx-auto text-[#3B4D00] mb-0.5" />
              <span className="text-[9px] text-[#3B4D00] uppercase font-mono font-bold block truncate">Match</span>
              <span className="font-bold text-xs font-mono text-[#3B4D00]">{latestRun.matches_qualified}</span>
            </div>

            <div className="p-1.5 rounded-card bg-[#FF5A36]/15 border border-[#FF5A36]/30">
              <FileText className="w-3 h-3 mx-auto text-[#8F230D] mb-0.5" />
              <span className="text-[9px] text-[#8F230D] uppercase font-mono font-bold block truncate">Tailored</span>
              <span className="font-bold text-xs font-mono text-[#8F230D]">{latestRun.resumes_generated}</span>
            </div>

            <div className="p-1.5 rounded-card bg-[#5BCB8A]/15 border border-[#5BCB8A]/40">
              <Bell className="w-3 h-3 mx-auto text-[#185C36] mb-0.5" />
              <span className="text-[9px] text-[#185C36] uppercase font-mono font-bold block truncate">Emails</span>
              <span className="font-bold text-xs font-mono text-[#185C36]">{latestRun.notifications_sent}</span>
            </div>
          </div>
        </div>

        {/* Notice/Failure Callout */}
        {latestRun.error_summary && (
          <div className="flex items-start gap-2 p-2.5 rounded-card bg-[#E6B84D]/15 border border-[#E6B84D]/40 text-xs text-[#6E4C00] font-mono">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-[#6E4C00]" />
            <span className="line-clamp-2">Notice: {latestRun.error_summary}</span>
          </div>
        )}

        {/* Secondary Recent Runs list */}
        {secondaryRuns.length > 0 && (
          <div className="pt-2 border-t border-terminal-warmBorder">
            <span className="text-[10px] font-mono font-bold uppercase text-terminal-muted block mb-2">
              Previous Executions
            </span>
            <div className="space-y-1.5">
              {secondaryRuns.map((run) => (
                <div
                  key={run.id}
                  onClick={() => onSelectRun?.(run.id)}
                  className={`flex items-center justify-between p-2 rounded-card bg-terminal-warm/30 border border-terminal-warmBorder text-xs ${
                    onSelectRun ? "cursor-pointer hover:bg-terminal-warm transition-colors" : ""
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-xs text-terminal-dark font-medium truncate max-w-[80px]">
                      {run.id.slice(0, 8)}
                    </span>
                    <StatusBadge status={run.status} />
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-terminal-muted shrink-0">
                    <span>{run.matches_qualified} matches</span>
                    <span>&bull;</span>
                    <span>{formatDate(run.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
