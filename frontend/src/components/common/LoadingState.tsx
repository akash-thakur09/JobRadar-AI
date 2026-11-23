import { Spinner } from "@/components/ui/Spinner";

export interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({ message = "Loading information...", className }: LoadingStateProps) {
  return (
    <div
      role="status"
      className={`flex flex-col items-center justify-center p-12 text-center rounded-card border border-terminal-warmBorder bg-terminal-warmSurface/70 ${className || ""}`}
    >
      <Spinner size="lg" label={message} />
      <p className="text-xs text-terminal-muted mt-3 font-mono">{message}</p>
    </div>
  );
}

