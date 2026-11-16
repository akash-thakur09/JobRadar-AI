import { Globe, Sparkles, UserCheck, PlayCircle } from "lucide-react";
import { Link } from "react-router-dom";

export interface DashboardMetricsOverviewProps {
  totalJobs: number;
  totalMatches: number;
  readinessScore: number;
  totalRuns: number;
  hasActiveRun?: boolean;
}

export function DashboardMetricsOverview({
  totalJobs,
  totalMatches,
  readinessScore,
  totalRuns,
  hasActiveRun = false,
}: DashboardMetricsOverviewProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {/* 1. Discovered Jobs */}
      <Link
        to="/discovery"
        className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle hover:border-terminal-muted/80 transition-all group"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted">
            Discovered Jobs
          </span>
          <div className="w-7 h-7 rounded-card bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted group-hover:text-terminal-primary transition-colors">
            <Globe className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-terminal-dark">
            {totalJobs}
          </span>
          <span className="text-[10px] font-mono text-terminal-muted">canonical</span>
        </div>
        <p className="text-[11px] text-terminal-muted mt-1 truncate">
          From verified career sources
        </p>
      </Link>

      {/* 2. Qualified Matches */}
      <Link
        to="/matches"
        className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle hover:border-terminal-muted/80 transition-all group"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-bold uppercase text-[#3B4D00]">
            Evaluated Matches
          </span>
          <div className="w-7 h-7 rounded-card bg-[#D6FF3F]/25 border border-[#B8E61A]/50 flex items-center justify-center text-[#3B4D00]">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-[#3B4D00]">
            {totalMatches}
          </span>
          <span className="text-[10px] font-mono text-[#3B4D00]/80">scored</span>
        </div>
        <p className="text-[11px] text-terminal-muted mt-1 truncate">
          Layer 1 & 2 evaluated
        </p>
      </Link>

      {/* 3. Profile Readiness */}
      <Link
        to="/profile"
        className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle hover:border-terminal-muted/80 transition-all group"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted">
            Profile Readiness
          </span>
          <div className="w-7 h-7 rounded-card bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted group-hover:text-terminal-primary transition-colors">
            <UserCheck className="w-3.5 h-3.5" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-terminal-dark">
            {readinessScore}%
          </span>
          <span className="text-[10px] font-mono text-terminal-muted">complete</span>
        </div>
        <p className="text-[11px] text-terminal-muted mt-1 truncate">
          Evidence Vault calibration
        </p>
      </Link>

      {/* 4. Pipeline Runs */}
      <Link
        to="/pipeline"
        className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle hover:border-terminal-muted/80 transition-all group"
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-mono font-bold uppercase text-terminal-muted">
            Pipeline Runs
          </span>
          <div className="w-7 h-7 rounded-card bg-terminal-warm border border-terminal-warmBorder flex items-center justify-center text-terminal-muted group-hover:text-terminal-primary transition-colors">
            <PlayCircle className={`w-3.5 h-3.5 ${hasActiveRun ? "text-terminal-primary animate-pulse" : ""}`} />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold font-mono text-terminal-dark">
            {totalRuns}
          </span>
          {hasActiveRun && (
            <span className="text-[10px] font-mono font-bold text-terminal-primary animate-pulse">
              RUNNING
            </span>
          )}
        </div>
        <p className="text-[11px] text-terminal-muted mt-1 truncate">
          {hasActiveRun ? "Execution in progress" : "End-to-end cycles"}
        </p>
      </Link>
    </div>
  );
}

