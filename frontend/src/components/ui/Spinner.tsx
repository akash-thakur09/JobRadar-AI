import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

export function Spinner({ size = "md", className, label = "Loading..." }: SpinnerProps) {
  const sizes = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  };

  return (
    <div role="status" className="inline-flex items-center gap-2 text-terminal-muted">
      <Loader2 className={cn("animate-spin text-terminal-primary", sizes[size], className)} />
      {label && <span className="text-xs font-medium text-terminal-dark">{label}</span>}
      <span className="sr-only">{label}</span>
    </div>
  );
}
