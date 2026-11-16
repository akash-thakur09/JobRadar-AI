import * as React from "react";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-card border-2 border-dashed border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
      <div className="w-12 h-12 rounded-full bg-terminal-warm flex items-center justify-center text-terminal-muted mb-4 border border-terminal-warmBorder">
        {icon || <FolderOpen className="w-6 h-6 text-terminal-muted" />}
      </div>
      <h3 className="text-base font-semibold font-display text-terminal-dark">{title}</h3>
      <p className="text-sm text-terminal-muted max-w-sm mt-1 mb-6">{description}</p>
      {actionLabel && onAction && (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

