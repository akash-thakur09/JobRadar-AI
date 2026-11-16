import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "danger" | "neutral" | "brand" | "lime" | "ai";
  withDot?: boolean;
}

export function Badge({ className, variant = "neutral", withDot = false, children, ...props }: BadgeProps) {
  const variants = {
    brand: "bg-[#FF5A36]/10 text-[#C93B1D] border-[#FF5A36]/30",
    lime: "bg-[#D6FF3F]/25 text-[#3B4D00] border-[#B8E61A]/50 font-semibold",
    ai: "bg-[#8DB4FF]/15 text-[#183B7E] border-[#8DB4FF]/40",
    success: "bg-[#5BCB8A]/15 text-[#185C36] border-[#5BCB8A]/40",
    warning: "bg-[#E6B84D]/15 text-[#6E4C00] border-[#E6B84D]/40",
    danger: "bg-[#E05A47]/15 text-[#8A1F11] border-[#E05A47]/40",
    neutral: "bg-[#20201F]/5 text-[#20201F] border-[#20201F]/15",
  };

  const dots = {
    brand: "bg-[#FF5A36]",
    lime: "bg-[#7EAB00]",
    ai: "bg-[#5586E8]",
    success: "bg-[#5BCB8A]",
    warning: "bg-[#E6B84D]",
    danger: "bg-[#E05A47]",
    neutral: "bg-[#AAA69E]",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide",
        variants[variant],
        className
      )}
      {...props}
    >
      {withDot && <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", dots[variant])} />}
      {children}
    </span>
  );
}
