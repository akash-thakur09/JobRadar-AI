import { Badge } from "@/components/ui/Badge";
import type { PipelineRunStatus } from "@/types/pipeline";

export interface StatusBadgeProps {
  status: PipelineRunStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  switch (status) {
    case "COMPLETED":
      return (
        <Badge variant="success" withDot>
          Completed
        </Badge>
      );
    case "RUNNING":
      return (
        <Badge variant="brand" withDot className="animate-pulse">
          Running
        </Badge>
      );
    case "PENDING":
      return (
        <Badge variant="warning" withDot>
          Pending
        </Badge>
      );
    case "PARTIALLY_COMPLETED":
      return (
        <Badge variant="warning" withDot>
          Partially Completed
        </Badge>
      );
    case "FAILED":
      return (
        <Badge variant="danger" withDot>
          Failed
        </Badge>
      );
    case "CANCELLED":
      return (
        <Badge variant="neutral" withDot>
          Cancelled
        </Badge>
      );
    default:
      return <Badge variant="neutral">{status}</Badge>;
  }
}

