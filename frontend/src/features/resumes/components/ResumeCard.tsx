import { useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  Download,
  CheckCircle,
  Eye,
  Clock,
  Layers,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useActivateResume } from "@/hooks/useResumes";
import { resumesService } from "@/services/resumes.service";
import { formatBytes, formatDate, triggerBlobDownload } from "@/lib/utils";
import type { MasterResumeSummary, ResumeProcessingStatus } from "@/types/resumes";

interface ResumeCardProps {
  resume: MasterResumeSummary;
  onActivateSuccess?: () => void;
}

export function ResumeCard({ resume, onActivateSuccess }: ResumeCardProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const activateMutation = useActivateResume();

  const handleActivate = async () => {
    try {
      await activateMutation.mutateAsync(resume.id);
      if (onActivateSuccess) onActivateSuccess();
    } catch {
      // Handled by react query mutation state
    }
  };

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      const { data, filename } = await resumesService.downloadResumeFile(resume.id);
      const downloadName = filename || resume.original_filename || `resume-${resume.id}.pdf`;
      triggerBlobDownload(data, downloadName);
    } catch (err) {
      console.error("Failed to download resume:", err);
    } finally {
      setIsDownloading(false);
    }
  };

  const isPdf =
    resume.mime_type.toLowerCase().includes("pdf") ||
    resume.original_filename.toLowerCase().endsWith(".pdf");

  const status: ResumeProcessingStatus =
    resume.latest_version?.processing_status || "COMPLETED";

  const renderStatusBadge = () => {
    switch (status) {
      case "COMPLETED":
        return (
          <Badge variant="success" withDot>
            Parsed
          </Badge>
        );
      case "PROCESSING":
        return (
          <Badge variant="warning" withDot>
            Parsing...
          </Badge>
        );
      case "FAILED":
        return (
          <Badge variant="danger" withDot>
            Parse Failed
          </Badge>
        );
      case "PENDING":
      default:
        return (
          <Badge variant="neutral" withDot>
            Pending
          </Badge>
        );
    }
  };

  return (
    <Card className={`relative overflow-hidden transition-all duration-200 hover:border-terminal-muted/60 ${
      resume.is_active ? "border-l-4 border-l-[#D6FF3F] bg-terminal-warmSurface" : ""
    }`}>
      <CardContent className="p-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          {/* File details & badges */}
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-card bg-terminal-warm flex items-center justify-center text-terminal-primary border border-terminal-warmBorder shrink-0">
              <FileText className="w-5 h-5" />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to={`/resumes/${resume.id}`}
                  className="text-base font-semibold font-display text-terminal-dark hover:text-terminal-primary transition-colors leading-tight"
                >
                  {resume.original_filename}
                </Link>

                <Badge variant="neutral" className="font-mono text-[10px] uppercase">
                  {isPdf ? "PDF" : "DOCX"}
                </Badge>

                {resume.is_active && (
                  <Badge variant="lime" withDot>
                    ACTIVE MASTER RESUME
                  </Badge>
                )}

                {renderStatusBadge()}
              </div>

              {/* Meta details */}
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-2 text-xs text-terminal-muted">
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDate(resume.created_at)}
                </span>

                <span className="font-mono">{formatBytes(resume.file_size_bytes)}</span>

                {resume.latest_version && (
                  <span className="flex items-center gap-1 font-mono">
                    <Layers className="w-3.5 h-3.5" />
                    v{resume.latest_version.version_number}
                  </span>
                )}

                <span className="font-mono text-[11px] text-terminal-muted/80 truncate max-w-[200px]" title={resume.checksum_sha256}>
                  SHA: {resume.checksum_sha256.substring(0, 8)}...
                </span>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2 sm:self-center shrink-0">
            {!resume.is_active && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleActivate}
                isLoading={activateMutation.isPending}
                disabled={activateMutation.isPending}
                title="Designate this resume as the active master resume for matching and tailoring"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Set as Active
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              isLoading={isDownloading}
              disabled={isDownloading}
              title="Download original file"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </Button>

            <Link to={`/resumes/${resume.id}`}>
              <Button variant="secondary" size="sm">
                <Eye className="w-3.5 h-3.5" />
                View Parsed
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
