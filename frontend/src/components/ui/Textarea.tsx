import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, rows = 3, ...props }, ref) => {
    const generatedId = React.useId();
    const textareaId = id || generatedId;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={textareaId} className="block text-xs font-semibold text-terminal-dark">
            {label}
            {props.required && <span className="text-terminal-error ml-0.5">*</span>}
          </label>
        )}
        <textarea
          id={textareaId}
          ref={ref}
          rows={rows}
          className={cn(
            "w-full rounded-card border border-terminal-warmBorder bg-white px-3 py-2 text-sm text-terminal-dark placeholder:text-terminal-muted focus:border-terminal-primary focus:outline-none focus:ring-1 focus:ring-terminal-primary disabled:cursor-not-allowed disabled:bg-terminal-warm/60 disabled:text-terminal-muted transition-colors shadow-subtle",
            error && "border-terminal-error focus:border-terminal-error focus:ring-terminal-error",
            className
          )}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${textareaId}-error` : helperText ? `${textareaId}-desc` : undefined}
          {...props}
        />
        {error && (
          <p id={`${textareaId}-error`} className="text-xs text-terminal-errorText font-medium">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${textareaId}-desc`} className="text-xs text-terminal-muted">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
