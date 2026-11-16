import { CheckCircle2, AlertCircle, Sparkles } from "lucide-react";
import type { CandidatePreferences, CandidateProfile, CandidateSkill } from "@/types/candidate";
import { Badge } from "@/components/ui/Badge";
import { calculateProfileCompletion } from "../utils/profileCompletion";

export interface ProfileCompletionWidgetProps {
  profile: CandidateProfile | null | undefined;
  preferences?: CandidatePreferences | null;
  skills?: CandidateSkill[] | null;
  className?: string;
}

export function ProfileCompletionWidget({
  profile,
  preferences,
  skills,
  className,
}: ProfileCompletionWidgetProps) {
  const { score, criteria, completedCount, totalCount } = calculateProfileCompletion(
    profile,
    preferences,
    skills
  );

  const isExcellent = score >= 80;
  const isModerate = score >= 50 && score < 80;

  return (
    <div
      className={`rounded-card border border-terminal-warmBorder bg-terminal-warmSurface p-5 shadow-subtle ${
        className || ""
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-terminal-primary" />
            <h3 className="text-sm font-bold font-display text-terminal-dark">
              Profile Readiness & Evidence
            </h3>
          </div>
          <p className="text-xs text-terminal-muted mt-0.5 font-sans">
            Completing key credentials unlocks maximum precision across Layer 1 eligibility and Layer 2 scoring
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant={isExcellent ? "lime" : isModerate ? "warning" : "neutral"}
            withDot
            className="font-mono text-xs"
          >
            {score}% Ready
          </Badge>
          <span className="text-xs font-mono text-terminal-muted">
            {completedCount}/{totalCount} items
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 rounded-full bg-terminal-warm overflow-hidden border border-terminal-warmBorder/60 mb-4">
        <div
          className={`h-full transition-all duration-500 rounded-full ${
            isExcellent
              ? "bg-[#D6FF3F]"
              : isModerate
              ? "bg-[#E6B84D]"
              : "bg-terminal-primary"
          }`}
          style={{ width: `${score}%` }}
        />
      </div>

      {/* Criteria Breakdown Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-2 border-t border-terminal-warmBorder/60 text-xs">
        {criteria.map((item) => (
          <div
            key={item.id}
            className={`flex items-start gap-2 p-2 rounded-card border transition-colors ${
              item.isComplete
                ? "bg-terminal-warm/40 border-terminal-warmBorder/60 text-terminal-dark"
                : "bg-terminal-warmSurface border-dashed border-terminal-warmBorder text-terminal-muted"
            }`}
            title={item.tip}
          >
            {item.isComplete ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-[#185C36] mt-0.5 shrink-0" />
            ) : (
              <AlertCircle className="w-3.5 h-3.5 text-terminal-muted mt-0.5 shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <span className={`block truncate font-medium ${item.isComplete ? "text-terminal-dark" : "text-terminal-muted"}`}>
                {item.label}
              </span>
              <span className="text-[10px] text-terminal-muted truncate block font-sans">
                {item.tip}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
