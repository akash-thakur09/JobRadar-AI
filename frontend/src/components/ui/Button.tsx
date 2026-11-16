import * as React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-card transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none active:scale-[0.98]";

    const variants = {
      primary:
        "bg-terminal-primary text-white hover:bg-terminal-primaryHover focus-visible:ring-terminal-primary shadow-subtle",
      secondary:
        "bg-terminal-secondary text-white hover:bg-terminal-elevated focus-visible:ring-terminal-secondary",
      outline:
        "border border-terminal-warmBorder bg-terminal-warmSurface text-terminal-dark hover:bg-terminal-warm hover:border-terminal-muted/60 focus-visible:ring-terminal-primary",
      ghost:
        "text-terminal-dark hover:bg-terminal-elevated/10 focus-visible:ring-terminal-elevated",
      danger:
        "bg-terminal-error text-white hover:bg-[#C94735] focus-visible:ring-terminal-error shadow-subtle",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-9 px-4 text-sm gap-2",
      lg: "h-11 px-6 text-base gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
