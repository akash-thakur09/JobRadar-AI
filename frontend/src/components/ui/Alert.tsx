import * as React from "react";
import { cn } from "@/lib/utils";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "error";
  title?: string;
}

export function Alert({ className, variant = "info", title, children, ...props }: AlertProps) {
  const configs = {
    info: {
      wrapper: "bg-[#8DB4FF]/10 border-[#8DB4FF]/40 text-[#183B7E]",
      icon: <Info className="w-5 h-5 text-[#3C73DD] shrink-0 mt-0.5" />,
    },
    success: {
      wrapper: "bg-[#5BCB8A]/15 border-[#5BCB8A]/40 text-[#185C36]",
      icon: <CheckCircle2 className="w-5 h-5 text-[#185C36] shrink-0 mt-0.5" />,
    },
    warning: {
      wrapper: "bg-[#E6B84D]/15 border-[#E6B84D]/40 text-[#6E4C00]",
      icon: <TriangleAlert className="w-5 h-5 text-[#8A6000] shrink-0 mt-0.5" />,
    },
    error: {
      wrapper: "bg-[#E05A47]/15 border-[#E05A47]/40 text-[#8A1F11]",
      icon: <AlertCircle className="w-5 h-5 text-[#8A1F11] shrink-0 mt-0.5" />,
    },
  };

  const { wrapper, icon } = configs[variant];

  return (
    <div
      role="alert"
      className={cn("flex items-start gap-3 p-4 rounded-card border text-sm shadow-subtle", wrapper, className)}
      {...props}
    >
      {icon}
      <div className="space-y-0.5">
        {title && <h5 className="font-semibold font-display leading-snug">{title}</h5>}
        <div className="text-xs leading-relaxed opacity-95">{children}</div>
      </div>
    </div>
  );
}
