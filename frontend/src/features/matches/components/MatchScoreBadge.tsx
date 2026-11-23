import { cn } from "@/lib/utils";

export interface MatchScoreBadgeProps {
  score: number | string;
  size?: "sm" | "md" | "lg";
  className?: string;
  showLabel?: boolean;
}

export function MatchScoreBadge({
  score,
  size = "md",
  className,
  showLabel = false,
}: MatchScoreBadgeProps) {
  const numericScore = typeof score === "number" ? score : parseFloat(score) || 0;
  const rounded = Math.round(numericScore);

  let colorClasses = "bg-terminal-error/15 text-terminal-errorText border-terminal-error/30";
  if (numericScore >= 80) {
    colorClasses = "bg-[#5BCB8A]/15 text-[#185C36] border-[#5BCB8A]/40";
  } else if (numericScore >= 60) {
    colorClasses = "bg-[#D6FF3F]/25 text-[#3B4D00] border-[#B8E61A]/50";
  } else if (numericScore >= 50) {
    colorClasses = "bg-terminal-amber/15 text-terminal-amberText border-terminal-amber/30";
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-mono font-bold",
    md: "px-2.5 py-1 text-sm font-mono font-bold",
    lg: "px-3.5 py-1.5 text-base sm:text-lg font-mono font-bold",
  }[size];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-card border shadow-subtle",
        sizeClasses,
        colorClasses,
        className
      )}
    >
      <span>{rounded}%</span>
      {showLabel && (
        <span className="text-[10px] font-sans font-semibold uppercase opacity-80">
          Match
        </span>
      )}
    </div>
  );
}

