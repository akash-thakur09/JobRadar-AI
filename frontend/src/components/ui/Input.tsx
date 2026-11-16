import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", label, error, helperText, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-semibold text-terminal-dark">
            {label}
            {props.required && <span className="text-terminal-error ml-0.5">*</span>}
          </label>
        )}
        <input
          id={inputId}
          type={type}
          ref={ref}
          className={cn(
            "w-full rounded-card border border-terminal-warmBorder bg-white px-3 py-2 text-sm text-terminal-dark placeholder:text-terminal-muted focus:border-terminal-primary focus:outline-none focus:ring-1 focus:ring-terminal-primary disabled:cursor-not-allowed disabled:bg-terminal-warm/60 disabled:text-terminal-muted transition-colors shadow-subtle",
            error && "border-terminal-error focus:border-terminal-error focus:ring-terminal-error",
            className
          )}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-desc` : undefined}
          {...props}
        />
        {error && (
          <p id={`${inputId}-error`} className="text-xs text-terminal-errorText font-medium">
            {error}
          </p>
        )}
        {!error && helperText && (
          <p id={`${inputId}-desc`} className="text-xs text-terminal-muted">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
