import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Download,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
  ShieldCheck,
  Copy,
  Check,
} from "lucide-react";
import { isResumeParsing, useResume, useResumeContent, useResumeVersions, useActivateResume } from "@/hooks/useResumes";
import { resumesService } from "@/services/resumes.service";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { formatBytes, formatDate, triggerBlobDownload } from "@/lib/utils";
import { ParsedSectionsView } from "../components/ParsedSectionsView";
import { ResumeVersionsList } from "../components/ResumeVersionsList";

export function ResumeDetailPage() {
  const { resumeId } = useParams<{ resumeId: string }>();
  const [isDownloading, setIsDownloading] = useState(false);
  const [copiedSha, setCopiedSha] = useState(false);

  const {
    data: resume,
    isLoading: isResumeLoading,
    error: resumeError,
    refetch: refetchResume,
  } = useResume(resumeId || "");

  const isParsing = isResumeParsing(resume?.active_version?.processing_status);
  const {
    data: parsedContent,
    isLoading: isContentLoading,
    error: contentError,
  } = useResumeContent(resumeId || "", Boolean(resume) && !isParsing);

  const { data: versions } = useResumeVersions(resumeId || "");

  const activateMutation = useActivateResume();

  if (isResumeLoading) {
    return <LoadingState message="Loading master resume details & parsed sections..." />;
  }

  if (resumeError || !resume) {
    return (
      <ErrorState
        title="Resume Not Found"
        message="The requested master resume could not be retrieved. It may have been deleted or the ID is invalid."
        onRetry={() => refetchResume()}
        action={
          <Link to="/resumes">
            <Button variant="outline" size="sm">
              &larr; Back to Resumes
            </Button>
          </Link>
        }
      />
    );
  }

  const handleActivate = async () => {
    if (!resume.id) return;
    try {
      await activateMutation.mutateAsync(resume.id);
      refetchResume();
    } catch {
      // Handled by react query mutation state
    }
  };

  const handleDownload = async () => {
    if (!resume.id) return;
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

  const handleCopySha = () => {
    if (!resume.checksum_sha256) return;
    navigator.clipboard.writeText(resume.checksum_sha256);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  const isPdf =
    resume.mime_type.toLowerCase().includes("pdf") ||
    resume.original_filename.toLowerCase().endsWith(".pdf");

  const activeVersion = resume.active_version;
  const parsingError = activeVersion?.parsing_error;
  const isFailed = activeVersion?.processing_status === "FAILED";

  return (
    <div className="space-y-6">
      {/* Navigation Breadcrumb & Back button */}
      <div>
        <Link
          to="/resumes"
          className="inline-flex items-center gap-1.5 text-xs text-terminal-muted hover:text-terminal-dark transition-colors font-medium mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Resumes
        </Link>
      </div>

      {/* Hero Header Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="w-10 h-10 rounded-card bg-terminal-warm flex items-center justify-center text-terminal-primary border border-terminal-warmBorder">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-xl font-bold font-display text-terminal-dark">
                      {resume.original_filename}
                    </h1>
                    <Badge variant="neutral" className="font-mono text-xs uppercase">
                      {isPdf ? "PDF" : "DOCX"}
                    </Badge>
                    {resume.is_active && (
                      <Badge variant="lime" withDot>
                        ACTIVE MASTER RESUME
                      </Badge>
                    )}
                    {activeVersion && (
                      <Badge
                        variant={
                          activeVersion.processing_status === "COMPLETED"
                            ? "success"
                            : activeVersion.processing_status === "FAILED"
                            ? "danger"
                            : "warning"
                        }
                        withDot
                      >
                        {activeVersion.processing_status}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-terminal-muted mt-0.5">
                    Storage Key: <span className="font-mono text-terminal-dark">{resume.storage_key}</span>
                  </p>
                </div>
              </div>

              {/* Monospace Metadata Badges */}
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-terminal-muted pt-1">
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="w-3.5 h-3.5 text-terminal-muted" />
                  Uploaded: {formatDate(resume.created_at)}
                </span>
                <span className="font-mono font-medium text-terminal-dark">
                  Size: {formatBytes(resume.file_size_bytes)}
                </span>
                {activeVersion && (
                  <span className="flex items-center gap-1 font-mono">
                    <Layers className="w-3.5 h-3.5 text-terminal-muted" />
                    Version: v{activeVersion.version_number}
                  </span>
                )}
                <div className="flex items-center gap-1 font-mono text-[11px] text-terminal-muted bg-terminal-warm px-2 py-0.5 rounded border border-terminal-warmBorder">
                  <span className="truncate max-w-[200px]" title={resume.checksum_sha256}>
                    SHA: {resume.checksum_sha256}
                  </span>
                  <button
                    onClick={handleCopySha}
                    className="p-0.5 text-terminal-muted hover:text-terminal-dark"
                    title="Copy full SHA-256"
                  >
                    {copiedSha ? <Check className="w-3 h-3 text-terminal-success" /> : <Copy className="w-3 h-3" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Actions Bar */}
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              {!resume.is_active && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleActivate}
                  isLoading={activateMutation.isPending}
                  disabled={activateMutation.isPending}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  Set as Active
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                isLoading={isDownloading}
                disabled={isDownloading}
              >
                <Download className="w-4 h-4" />
                Download Original
              </Button>
              <Link to="/tailored-resumes">
                <Button variant="primary" size="sm">
                  <Sparkles className="w-4 h-4" />
                  Tailor for Jobs
                </Button>
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Parsing Error Banner if any */}
      {isFailed && (
        <Alert variant="error" title="Resume Parsing Failed">
          {parsingError || "An error occurred during deterministic text extraction and section parsing."}
        </Alert>
      )}

      {/* Main Content Layout: Parsed Sections & Version History */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Parsed Sections View (3 columns on large screens) */}
        <div className="lg:col-span-3 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold font-display text-terminal-dark flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-terminal-primary" />
              Parsed Structured Content
            </h2>
            <span className="text-xs text-terminal-muted font-mono">
              Deterministic AST & Section Parser
            </span>
          </div>

          {isParsing || isContentLoading ? (
            <LoadingState message="Extracting structured sections..." />
          ) : contentError ? (
            <Alert variant="warning" title="Could Not Retrieve Structured Content">
              Structured parsed content is unavailable for this resume version.
            </Alert>
          ) : (
            <ParsedSectionsView
              content={parsedContent || activeVersion?.structured_content}
              rawText={parsedContent?.raw_text || activeVersion?.structured_content?.raw_text}
            />
          )}
        </div>

        {/* Sidebar: Version History & Technical Details (1 column) */}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Layers className="w-4 h-4 text-terminal-primary" />
                Resume Versions ({versions?.length || (resume.versions?.length || 1)})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ResumeVersionsList
                versions={versions && versions.length > 0 ? versions : resume.versions}
                currentVersionId={activeVersion?.id}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Storage & Truthfulness</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-terminal-muted leading-relaxed">
              <p>
                This master resume forms the foundational layer of candidate evidence in the JobRadar AI Evidence Vault.
              </p>
              <p>
                All tailored resumes strictly cite facts parsed from this source document. No claims or metric fabrications are ever injected.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
