import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Failed to load data",
  message = "An error occurred while communicating with the JobRadar AI backend. Please verify that the server is reachable and try again.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`p-6 rounded-card border border-terminal-error/30 bg-terminal-error/10 text-center flex flex-col items-center justify-center ${className || ""}`}
    >
      <div className="w-10 h-10 rounded-full bg-terminal-error/20 flex items-center justify-center text-terminal-error mb-3">
        <AlertCircle className="w-5 h-5" />
      </div>
      <h4 className="text-sm font-semibold font-display text-terminal-errorText mb-1">{title}</h4>
      <p className="text-xs text-terminal-errorText/90 max-w-md leading-relaxed mb-4">{message}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="gap-1.5 bg-terminal-warmSurface text-terminal-errorText border-terminal-error/40 hover:bg-terminal-error/10">
          <RotateCcw className="w-3.5 h-3.5" />
          Retry Request
        </Button>
      )}
    </div>
  );
}

