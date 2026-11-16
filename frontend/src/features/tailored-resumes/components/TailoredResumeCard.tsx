import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Download,
  Eye,
  Sparkles,
  Building2,
  Clock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useJob } from "@/hooks/useJobs";
import { tailoredResumesService } from "@/services/tailored-resumes.service";
import { formatDate, formatBytes, triggerBlobDownload } from "@/lib/utils";
import type { TailoredResumeSummary, TailoredResumeStatus } from "@/types/tailored-resumes";

interface TailoredResumeCardProps {
  tailoredResume: TailoredResumeSummary;
}

export function TailoredResumeCard({ tailoredResume }: TailoredResumeCardProps) {
  const [isDownloading, setIsDownloading] = useState(false);

  // Retrieve canonical job to display title and company
  const { data: job } = useJob(tailoredResume.job_id);

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      const { data, filename } = await tailoredResumesService.downloadTailoredPdf(tailoredResume.id);
      const downloadName = filename || tailoredResume.file_name || `tailored-resume-${tailoredResume.id.substring(0, 8)}.pdf`;
      triggerBlobDownload(data, downloadName);
    } catch (err) {
      console.error("Failed to download tailored PDF:", err);
    } finally {
      setIsDownloading(false);
    }
  };

  const renderStatusBadge = (status: TailoredResumeStatus) => {
    switch (status) {
      case "COMPLETED":
        return (
          <Badge variant="success" withDot>
            Ready (ATS)
          </Badge>
        );
      case "FAILED":
        return (
          <Badge variant="danger" withDot>
            Failed
          </Badge>
        );
      case "RENDERING":
      case "VALIDATING":
      case "PROCESSING":
        return (
          <Badge variant="warning" withDot className="animate-pulse">
            {status}
          </Badge>
        );
      case "PENDING":
      default:
        return (
          <Badge variant="neutral" withDot>
            Queued
          </Badge>
        );
    }
  };

  const isCompleted = tailoredResume.generation_status === "COMPLETED";

  return (
    <Card className="hover:border-terminal-muted/60 transition-all">
      <CardContent className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-card bg-terminal-primary/10 text-terminal-primary border border-terminal-primary/20 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to={`/tailored-resumes/${tailoredResume.id}`}
                  className="text-base font-semibold font-display text-terminal-dark hover:text-terminal-primary transition-colors leading-tight"
                >
                  {job?.title || "Tailored Application"}
                </Link>

                <Badge
                  variant={tailoredResume.rendering_strategy === "PRESERVED" ? "lime" : "neutral"}
                  className="font-mono text-[10px]"
                >
                  {tailoredResume.rendering_strategy}
                </Badge>

                {renderStatusBadge(tailoredResume.generation_status)}
              </div>

              {/* Company & Job info */}
              <div className="flex items-center gap-2 mt-1 text-xs text-terminal-dark font-medium">
                <Building2 className="w-3.5 h-3.5 text-terminal-muted" />
                <span>{job?.canonical_company_name || "Company Details Pending"}</span>
                {job?.normalized_location && (
                  <span className="text-terminal-muted font-normal">&bull; {job.normalized_location}</span>
                )}
              </div>

              {/* Meta details */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-2 text-xs text-terminal-muted font-mono">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDate(tailoredResume.created_at)}
                </span>

                {tailoredResume.file_size_bytes && (
                  <span>{formatBytes(tailoredResume.file_size_bytes)}</span>
                )}

                {tailoredResume.generation_attempts > 1 && (
                  <span>Attempts: {tailoredResume.generation_attempts}</span>
                )}
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2 sm:self-center shrink-0">
            {isCompleted && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                isLoading={isDownloading}
                disabled={isDownloading}
              >
                <Download className="w-3.5 h-3.5" />
                Download PDF
              </Button>
            )}

            <Link to={`/tailored-resumes/${tailoredResume.id}`}>
              <Button variant="secondary" size="sm">
                <Eye className="w-3.5 h-3.5" />
                View & Audit
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
