import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { EligibilityStatus } from "@/types/matches";
import { Badge } from "@/components/ui/Badge";

export interface EligibilityBadgeProps {
  status: EligibilityStatus;
  className?: string;
  showIcon?: boolean;
}

export function EligibilityBadge({ status, className, showIcon = true }: EligibilityBadgeProps) {
  switch (status) {
    case "ELIGIBLE":
      return (
        <Badge variant="success" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <CheckCircle2 className="w-3 h-3" />}
          <span>Eligible</span>
        </Badge>
      );

    case "INELIGIBLE_EXPERIENCE":
      return (
        <Badge variant="danger" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <XCircle className="w-3 h-3" />}
          <span>Ineligible: Experience</span>
        </Badge>
      );

    case "INELIGIBLE_LOCATION":
      return (
        <Badge variant="danger" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <XCircle className="w-3 h-3" />}
          <span>Ineligible: Location</span>
        </Badge>
      );

    case "INELIGIBLE_WORK_AUTH":
      return (
        <Badge variant="danger" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <XCircle className="w-3 h-3" />}
          <span>Ineligible: Work Auth</span>
        </Badge>
      );

    case "INELIGIBLE_MANDATORY_SKILL":
      return (
        <Badge variant="danger" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <XCircle className="w-3 h-3" />}
          <span>Ineligible: Required Skill</span>
        </Badge>
      );

    default:
      return (
        <Badge variant="neutral" className={`gap-1 font-mono text-[10px] ${className || ""}`}>
          {showIcon && <AlertCircle className="w-3 h-3" />}
          <span>{status.replace(/_/g, " ")}</span>
        </Badge>
      );
  }
}

