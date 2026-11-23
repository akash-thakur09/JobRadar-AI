import { CheckCircle2, Clock, AlertTriangle, RefreshCw } from "lucide-react";
import type { NotificationDeliveryStatus } from "@/types/notifications";

export interface NotificationStatusBadgeProps {
  status: NotificationDeliveryStatus;
  className?: string;
}

export function NotificationStatusBadge({ status, className = "" }: NotificationStatusBadgeProps) {
  switch (status) {
    case "SENT":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-[#5BCB8A]/15 text-[#1B5E20] border border-[#5BCB8A]/40 ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32]" />
          <span>Delivered</span>
        </span>
      );

    case "PROCESSING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-[#8DB4FF]/15 text-[#0039A6] border border-[#8DB4FF]/40 ${className}`}
        >
          <RefreshCw className="w-3.5 h-3.5 text-[#0052CC] animate-spin" />
          <span>Processing</span>
        </span>
      );

    case "PENDING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-[#E6B84D]/15 text-[#6E4C00] border border-[#E6B84D]/40 ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-[#B27B00]" />
          <span>Pending</span>
        </span>
      );

    case "FAILED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-[#E05A47]/15 text-[#8A1C0E] border border-[#E05A47]/40 ${className}`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-[#C62828]" />
          <span>Failed</span>
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-terminal-warm border border-terminal-warmBorder text-terminal-muted ${className}`}
        >
          <span>{status}</span>
        </span>
      );
  }
}

