import { RotateCcw, Target, Shield } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface MatchFiltersProps {
  minScore: string;
  eligibility: string;
  onMinScoreChange: (value: string) => void;
  onEligibilityChange: (value: string) => void;
  onReset: () => void;
}

export function MatchFilters({
  minScore,
  eligibility,
  onMinScoreChange,
  onEligibilityChange,
  onReset,
}: MatchFiltersProps) {
  const hasActiveFilters = Boolean(minScore || eligibility);

  return (
    <div className="p-4 rounded-card border border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
      <div className="flex items-center gap-3 flex-wrap">
        {/* Min Score Filter */}
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-terminal-muted shrink-0" />
          <select
            value={minScore}
            onChange={(e) => onMinScoreChange(e.target.value)}
            className="h-9 px-3 text-xs rounded-card border border-terminal-warmBorder bg-white text-terminal-dark font-sans focus:outline-none focus:ring-1 focus:ring-terminal-primary shadow-subtle"
            aria-label="Filter by minimum score"
          >
            <option value="">All Match Scores</option>
            <option value="50">Qualified (50%+)</option>
            <option value="70">Good Alignment (70%+)</option>
            <option value="80">Strong Alignment (80%+)</option>
            <option value="90">Exceptional (90%+)</option>
          </select>
        </div>

        {/* Eligibility Filter */}
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-terminal-muted shrink-0" />
          <select
            value={eligibility}
            onChange={(e) => onEligibilityChange(e.target.value)}
            className="h-9 px-3 text-xs rounded-card border border-terminal-warmBorder bg-white text-terminal-dark font-sans focus:outline-none focus:ring-1 focus:ring-terminal-primary shadow-subtle"
            aria-label="Filter by eligibility"
          >
            <option value="">All Eligibility Outcomes</option>
            <option value="ELIGIBLE">Eligible Only</option>
            <option value="INELIGIBLE_EXPERIENCE">Ineligible: Experience</option>
            <option value="INELIGIBLE_LOCATION">Ineligible: Location</option>
            <option value="INELIGIBLE_WORK_AUTH">Ineligible: Work Auth</option>
            <option value="INELIGIBLE_MANDATORY_SKILL">Ineligible: Mandatory Skill</option>
          </select>
        </div>
      </div>

      {hasActiveFilters && (
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          className="h-9 px-3 text-xs gap-1.5 text-terminal-muted hover:text-terminal-dark border-dashed self-start sm:self-auto"
          title="Reset all filters"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Filters</span>
        </Button>
      )}
    </div>
  );
}
