import * as React from "react";
import { FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface EmptyStateProps {
  icon?: React.ReactNode | React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  action?: React.ReactNode;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
  action,
}: EmptyStateProps) {
  const renderIcon = () => {
    if (!icon) return <FolderOpen className="w-6 h-6 text-terminal-muted" />;
    if (React.isValidElement(icon)) return icon;
    if (typeof icon === "function" || (typeof icon === "object" && icon !== null)) {
      const IconComp = icon as React.ComponentType<{ className?: string }>;
      return <IconComp className="w-6 h-6 text-terminal-muted" />;
    }
    return null;
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-card border-2 border-dashed border-terminal-warmBorder bg-terminal-warmSurface shadow-subtle">
      <div className="w-12 h-12 rounded-full bg-terminal-warm flex items-center justify-center text-terminal-muted mb-4 border border-terminal-warmBorder">
        {renderIcon()}
      </div>
      <h3 className="text-base font-semibold font-display text-terminal-dark">{title}</h3>
      <p className="text-sm text-terminal-muted max-w-sm mt-1 mb-6">{description}</p>
      {action ? (
        action
      ) : actionLabel && onAction ? (
        <Button variant="outline" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
