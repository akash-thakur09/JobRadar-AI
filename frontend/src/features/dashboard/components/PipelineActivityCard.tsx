import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, PlayCircle, Layers, Bell, FileText } from "lucide-react";
import type { PipelineRunSummary } from "@/types/pipeline";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/features/pipeline/components/StatusBadge";
import { formatDate } from "@/lib/utils";

export interface PipelineActivityCardProps {
  latestRun: PipelineRunSummary | null | undefined;
  totalRunsCount: number;
}

export function PipelineActivityCard({ latestRun, totalRunsCount }: PipelineActivityCardProps) {
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
        <CardContent className="text-center py-6">
          <div className="w-10 h-10 rounded-full bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted mx-auto mb-2">
            <PlayCircle className="w-5 h-5" />
          </div>
          <p className="text-xs text-terminal-muted mb-3 font-mono">No pipeline runs have been executed yet.</p>
          <Link to="/pipeline">
            <Button variant="outline" size="sm">Go to Pipeline Monitoring</Button>
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col justify-between">
      <CardHeader className="flex flex-row items-start justify-between pb-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <PlayCircle className="w-4 h-4 text-terminal-primary" />
            <span>Latest Pipeline Run</span>
          </CardTitle>
          <CardDescription>
            {totalRunsCount} total execution{totalRunsCount === 1 ? "" : "s"} recorded
          </CardDescription>
        </div>
        <Link to="/pipeline">
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs gap-1 text-terminal-primary hover:text-terminal-primaryHover">
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </Link>
      </CardHeader>

      <CardContent className="space-y-4 flex-1">
        {/* Run status & trigger */}
        <div className="flex items-center justify-between p-3 rounded-card bg-terminal-warm/60 border border-terminal-warmBorder">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-terminal-dark">
                {latestRun.id.slice(0, 8)}...
              </span>
              <StatusBadge status={latestRun.status} />
            </div>
            <span className="text-[11px] text-terminal-muted block mt-0.5 font-mono">
              Triggered via {latestRun.trigger_type} &bull; {formatDate(latestRun.created_at)}
            </span>
          </div>
        </div>

        {/* 4 Core Summary Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          <div className="p-2.5 rounded-card bg-terminal-warmSurface border border-terminal-warmBorder">
            <Layers className="w-3.5 h-3.5 mx-auto text-terminal-muted mb-1" />
            <span className="text-[10px] text-terminal-muted uppercase font-mono font-bold block">Discovered</span>
            <span className="font-bold text-sm font-mono text-terminal-dark">{latestRun.jobs_discovered}</span>
          </div>

          <div className="p-2.5 rounded-card bg-[#D6FF3F]/20 border border-[#B8E61A]/50">
            <CheckCircle2 className="w-3.5 h-3.5 mx-auto text-[#3B4D00] mb-1" />
            <span className="text-[10px] text-[#3B4D00] uppercase font-mono font-bold block">Qualified</span>
            <span className="font-bold text-sm font-mono text-[#3B4D00]">{latestRun.matches_qualified}</span>
          </div>

          <div className="p-2.5 rounded-card bg-[#FF5A36]/15 border border-[#FF5A36]/30">
            <FileText className="w-3.5 h-3.5 mx-auto text-[#8F230D] mb-1" />
            <span className="text-[10px] text-[#8F230D] uppercase font-mono font-bold block">Tailored</span>
            <span className="font-bold text-sm font-mono text-[#8F230D]">{latestRun.resumes_generated}</span>
          </div>

          <div className="p-2.5 rounded-card bg-[#5BCB8A]/15 border border-[#5BCB8A]/40">
            <Bell className="w-3.5 h-3.5 mx-auto text-[#185C36] mb-1" />
            <span className="text-[10px] text-[#185C36] uppercase font-mono font-bold block">Delivered</span>
            <span className="font-bold text-sm font-mono text-[#185C36]">{latestRun.notifications_sent}</span>
          </div>
        </div>

        {latestRun.error_summary && (
          <p className="text-[11px] font-mono text-[#6E4C00] bg-[#E6B84D]/15 p-2 rounded-card border border-[#E6B84D]/40 truncate">
            Notice: {latestRun.error_summary}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

