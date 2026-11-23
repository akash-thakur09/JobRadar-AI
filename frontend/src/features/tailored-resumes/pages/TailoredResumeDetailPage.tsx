import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Sparkles,
  Building2,
  Clock,
  RefreshCw,
  ShieldCheck,
  FileText,
  ExternalLink,
  CheckCircle2,
  Briefcase,
  BookOpen,
} from "lucide-react";
import { useTailoredResume, useCreateTailoredResume } from "@/hooks/useTailoredResumes";
import { useJob } from "@/hooks/useJobs";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { formatDate } from "@/lib/utils";
import { ClaimValidationReportCard } from "../components/ClaimValidationReportCard";
import { PdfPreviewViewer } from "../components/PdfPreviewViewer";

export function TailoredResumeDetailPage() {
  const { tailoredResumeId } = useParams<{ tailoredResumeId: string }>();
  const [activeTab, setActiveTab] = useState<"validation" | "content" | "preview">("preview");

  const {
    data: tailoredResume,
    isLoading,
    error,
    refetch,
  } = useTailoredResume(tailoredResumeId || "");

  const { data: job } = useJob(tailoredResume?.job_id || "");
  const regenerateMutation = useCreateTailoredResume();

  if (isLoading) {
    return <LoadingState message="Loading tailored resume & claim validation audit..." />;
  }

  if (error || !tailoredResume) {
    return (
      <ErrorState
        title="Tailored Resume Not Found"
        message="The requested tailored resume application could not be retrieved."
        onRetry={() => refetch()}
        action={
          <Link to="/tailored-resumes">
            <Button variant="outline" size="sm">
              &larr; Back to Tailored Resumes
            </Button>
          </Link>
        }
      />
    );
  }

  const handleRegenerate = async () => {
    try {
      await regenerateMutation.mutateAsync({
        job_match_id: tailoredResume.job_match_id,
        resume_version_id: tailoredResume.resume_version_id,
        force_regenerate: true,
      });
      refetch();
    } catch {
      // Handled by react query mutation state
    }
  };

  const isCompleted = tailoredResume.generation_status === "COMPLETED";
  const isFailed = tailoredResume.generation_status === "FAILED";
  const isProcessing =
    tailoredResume.generation_status === "PENDING" ||
    tailoredResume.generation_status === "PROCESSING" ||
    tailoredResume.generation_status === "VALIDATING" ||
    tailoredResume.generation_status === "RENDERING";

  const content = tailoredResume.tailored_content;

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb */}
      <div>
        <Link
          to="/tailored-resumes"
          className="inline-flex items-center gap-1.5 text-xs text-terminal-muted hover:text-terminal-dark transition-colors font-medium mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Tailored Resumes
        </Link>
      </div>

      {/* Hero Header Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <div className="w-10 h-10 rounded-card bg-terminal-primary/10 text-terminal-primary border border-terminal-primary/20 flex items-center justify-center shrink-0">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h1 className="text-xl font-bold font-display text-terminal-dark">
                      {job?.title || "Tailored Resume Document"}
                    </h1>

                    <Badge
                      variant={tailoredResume.rendering_strategy === "PRESERVED" ? "lime" : "neutral"}
                      className="font-mono text-xs"
                    >
                      {tailoredResume.rendering_strategy === "PRESERVED"
                        ? "Preserved Template"
                        : "ATS Fallback"}
                    </Badge>

                    <Badge
                      variant={isCompleted ? "success" : isFailed ? "danger" : "warning"}
                      withDot
                      className={isProcessing ? "animate-pulse" : ""}
                    >
                      {tailoredResume.generation_status}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2 mt-1 text-xs text-terminal-dark font-medium">
                    <Building2 className="w-3.5 h-3.5 text-terminal-muted" />
                    <span>{job?.canonical_company_name || "Company Details"}</span>
                    {job?.id && (
                      <Link
                        to={`/jobs/${job.id}`}
                        className="text-terminal-primary hover:underline flex items-center gap-1 ml-1"
                      >
                        View Job Details
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    )}
                    {tailoredResume.job_match_id && (
                      <Link
                        to={`/matches/${tailoredResume.job_match_id}`}
                        className="text-terminal-primary hover:underline flex items-center gap-1 ml-2"
                      >
                        View Match Evaluation
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </div>
              </div>

              {/* Metadata row */}
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-terminal-muted font-mono pt-1">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Generated: {formatDate(tailoredResume.created_at)}
                </span>
                {tailoredResume.completed_at && (
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-terminal-success" />
                    Completed: {formatDate(tailoredResume.completed_at)}
                  </span>
                )}
                <span>Attempts: {tailoredResume.generation_attempts}</span>
                {tailoredResume.file_name && (
                  <span className="text-terminal-dark">{tailoredResume.file_name}</span>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRegenerate}
                isLoading={regenerateMutation.isPending}
                disabled={regenerateMutation.isPending || isProcessing}
                title="Force re-generation with fresh claim validation"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Force Regenerate
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* In-Pipeline Auto-polling Banner */}
      {isProcessing && (
        <Alert variant="warning" title="Generation in Progress">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-terminal-warning" />
            <span>
              The truthful tailoring and PDF rendering pipeline is actively running (Stage:{" "}
              <strong>{tailoredResume.generation_status}</strong>). This page updates automatically.
            </span>
          </div>
        </Alert>
      )}

      {/* Validation Error Banner */}
      {tailoredResume.validation_error && (
        <Alert variant="error" title="Pipeline Error">
          {tailoredResume.validation_error}
        </Alert>
      )}

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-1 p-1 bg-terminal-warm rounded-card border border-terminal-warmBorder">
        <button
          onClick={() => setActiveTab("preview")}
          className={`px-4 py-2 rounded-md text-xs font-medium transition-all flex items-center gap-2 ${
            activeTab === "preview"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          PDF Document Preview
        </button>

        <button
          onClick={() => setActiveTab("validation")}
          className={`px-4 py-2 rounded-md text-xs font-medium transition-all flex items-center gap-2 ${
            activeTab === "validation"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          Claim Validation & Audit
        </button>

        <button
          onClick={() => setActiveTab("content")}
          className={`px-4 py-2 rounded-md text-xs font-medium transition-all flex items-center gap-2 ${
            activeTab === "content"
              ? "bg-terminal-warmSurface text-terminal-dark font-semibold shadow-xs border border-terminal-warmBorder"
              : "text-terminal-muted hover:text-terminal-dark"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          Tailored Content Structure
        </button>
      </div>

      {/* Tab: PDF Preview */}
      {activeTab === "preview" && (
        <PdfPreviewViewer
          tailoredResumeId={tailoredResume.id}
          fileName={tailoredResume.file_name}
          status={tailoredResume.generation_status}
        />
      )}

      {/* Tab: Claim Validation & Honesty Audit */}
      {activeTab === "validation" && (
        <ClaimValidationReportCard
          report={tailoredResume.validation_metadata}
          error={tailoredResume.validation_error}
        />
      )}

      {/* Tab: Tailored Content Structure */}
      {activeTab === "content" && (
        <div className="space-y-6">
          {/* Headline & Summary */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Tailored Professional Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {content?.headline && (
                <div className="p-3 bg-terminal-warm/60 rounded-card border border-terminal-warmBorder">
                  <span className="text-[10px] uppercase font-mono text-terminal-muted tracking-wider">
                    Target Headline
                  </span>
                  <p className="text-sm font-semibold text-terminal-dark mt-0.5">{content.headline}</p>
                </div>
              )}
              {content?.professional_summary ? (
                <p className="text-xs text-terminal-dark leading-relaxed">
                  {content.professional_summary}
                </p>
              ) : (
                <p className="text-xs text-terminal-muted italic">No tailored summary available.</p>
              )}
            </CardContent>
          </Card>

          {/* Tailored Skills */}
          {content?.skills && content.skills.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">
                  Tailored Skills Alignment ({content.skills.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {content.skills.map((skill, idx) => (
                    <Badge
                      key={idx}
                      variant="neutral"
                      className="font-mono text-xs px-3 py-1 bg-terminal-warm border-terminal-warmBorder text-terminal-dark"
                    >
                      {skill}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tailored Experience */}
          {content?.experience && content.experience.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold font-display text-terminal-dark flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-terminal-primary" />
                Tailored Work Experience
              </h3>
              {content.experience.map((exp, idx) => (
                <Card key={idx} className="border-l-4 border-l-terminal-secondary">
                  <CardContent className="p-5 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
                      <h4 className="text-sm font-bold font-display text-terminal-dark">
                        {exp.title} <span className="font-normal text-terminal-muted">at</span> {exp.company}
                      </h4>
                      {(exp.start_date || exp.end_date) && (
                        <span className="text-xs font-mono text-terminal-muted">
                          {exp.start_date || "—"} &ndash; {exp.end_date || "Present"}
                        </span>
                      )}
                    </div>
                    {exp.bullet_points && exp.bullet_points.length > 0 && (
                      <ul className="list-disc list-outside pl-4 space-y-1.5 text-xs text-terminal-dark leading-relaxed">
                        {exp.bullet_points.map((b, bIdx) => (
                          <li key={bIdx}>{b}</li>
                        ))}
                      </ul>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Tailoring Notes */}
          {content?.tailoring_notes && (
            <Card className="bg-terminal-warm/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs text-terminal-muted uppercase font-mono">
                  Tailoring Engine Rationale
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-terminal-dark italic leading-relaxed">
                  {content.tailoring_notes}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
