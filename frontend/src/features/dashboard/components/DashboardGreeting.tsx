import { Calendar, Play, User } from "lucide-react";
import { Link } from "react-router-dom";
import type { CandidateProfile } from "@/types/candidate";
import { Button } from "@/components/ui/Button";

export interface DashboardGreetingProps {
  profile: CandidateProfile | null | undefined;
  onTriggerRun: () => void;
}

function getGreetingTime(date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function formatTerminalDate(date = new Date()): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

export function DashboardGreeting({ profile, onTriggerRun }: DashboardGreetingProps) {
  const greeting = getGreetingTime();
  const currentDate = formatTerminalDate();
  const candidateName = profile?.full_name || "Candidate";

  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-xs font-mono text-terminal-muted">
          <Calendar className="w-3.5 h-3.5 text-terminal-primary" />
          <span>{currentDate}</span>
          <span>&bull;</span>
          <span className="text-terminal-dark font-medium">Intelligence Dashboard</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold font-display text-terminal-dark tracking-tight">
          {greeting}, {candidateName}
        </h1>
        <p className="text-xs sm:text-sm text-terminal-muted font-sans max-w-2xl">
          {profile?.headline || profile?.current_role
            ? `${profile.headline || profile.current_role} • JobRadar AI is monitoring upstream postings and scoring opportunities against your Evidence Vault.`
            : "JobRadar AI is actively monitoring upstream sources and scoring opportunities against your Evidence Vault."}
        </p>
      </div>

      <div className="flex items-center gap-2.5 shrink-0">
        <Link to="/profile">
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            <User className="w-3.5 h-3.5" />
            <span>Manage Profile</span>
          </Button>
        </Link>
        <Button
          variant="primary"
          size="sm"
          onClick={onTriggerRun}
          className="gap-1.5 shadow-subtle text-xs"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Trigger Run</span>
        </Button>
      </div>
    </div>
  );
}
