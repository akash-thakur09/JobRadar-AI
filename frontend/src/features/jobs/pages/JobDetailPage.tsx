import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Building2,
  MapPin,
  Calendar,
  ExternalLink,
  Sparkles,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { useJob } from "@/hooks/useJobs";
import { useReevaluateMatch } from "@/hooks/useMatches";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { formatDate } from "@/lib/utils";
import { JobSourcesList } from "../components/JobSourcesList";

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [evaluateSuccessMsg, setEvaluateSuccessMsg] = useState<string | null>(null);

  const { data: job, isLoading, error, refetch } = useJob(jobId || "");
  const reevaluateMutation = useReevaluateMatch();

  const handleEvaluateMatch = async () => {
    if (!jobId) return;
    try {
      const matchResult = await reevaluateMutation.mutateAsync({ jobId });
      setEvaluateSuccessMsg("Match evaluation completed!");
      setTimeout(() => {
        if (matchResult?.id) {
          navigate(`/matches/${matchResult.id}`);
        }
      }, 1200);
    } catch {
      // Error captured by mutation state
    }
  };

  if (isLoading) {
    return <LoadingState message="Loading canonical job details..." />;
  }

  if (error || !job) {
    return (
      <ErrorState
        title="Job Not Found"
        message="The requested canonical job could not be retrieved. It may have expired or the identifier is invalid."
        onRetry={() => refetch()}
        action={
          <Link to="/jobs">
            <Button variant="outline" size="sm">
              &larr; Back to Job Discovery
            </Button>
          </Link>
        }
      />
    );
  }

  const getWorkplaceBadgeVariant = (wp: string) => {
    switch (wp?.toUpperCase()) {
      case "REMOTE":
        return "success";
      case "HYBRID":
        return "warning";
      case "ONSITE":
        return "neutral";
      default:
        return "neutral";
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status?.toUpperCase()) {
      case "ACTIVE":
        return "success";
      case "DISCOVERED":
        return "brand";
      case "EXPIRED":
      case "ARCHIVED":
        return "danger";
      default:
        return "neutral";
    }
  };

  const displayDate = job.posted_at || job.first_seen_at || job.created_at;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button & Breadcrumbs */}
      <div className="flex items-center justify-between">
        <Link
          to="/jobs"
          className="inline-flex items-center gap-1.5 text-xs font-mono font-medium text-terminal-muted hover:text-terminal-dark transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Opportunities</span>
        </Link>
      </div>

      {/* Main Header Card */}
      <Card className="relative overflow-hidden border-terminal-warmBorder shadow-card">
        {evaluateSuccessMsg && (
          <div className="absolute top-3 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-card bg-terminal-success text-[#185C36] text-xs font-medium border border-terminal-success/40 shadow-dropdown animate-bounce">
            <CheckCircle2 className="w-4 h-4" />
            <span>{evaluateSuccessMsg} Redirecting to match analysis...</span>
          </div>
        )}

        <CardContent className="p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={getStatusBadgeVariant(job.status)} className="font-mono text-xs uppercase px-2 py-0.5">
                  {job.status}
                </Badge>
                {job.workplace_type && (
                  <Badge variant={getWorkplaceBadgeVariant(job.workplace_type)} className="font-mono text-xs uppercase px-2 py-0.5">
                    {job.workplace_type}
                  </Badge>
                )}
                {job.employment_type && job.employment_type !== "UNKNOWN" && (
                  <span className="text-xs font-mono text-terminal-muted bg-terminal-warm px-2 py-0.5 rounded border border-terminal-warmBorder">
                    {job.employment_type.replace("_", " ")}
                  </span>
                )}
              </div>

              <h1 className="text-2xl sm:text-3xl font-bold font-display text-terminal-dark tracking-tight">
                {job.title}
              </h1>

              <div className="flex items-center gap-3 text-xs sm:text-sm text-terminal-muted flex-wrap font-sans">
                <span className="font-semibold text-terminal-dark flex items-center gap-1.5">
                  <Building2 className="w-4 h-4 text-terminal-muted" />
                  <span>{job.canonical_company_name}</span>
                </span>
                <span>&bull;</span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4 text-terminal-muted" />
                  <span>{job.normalized_location || "Location not specified"}</span>
                </span>
                {displayDate && (
                  <>
                    <span>&bull;</span>
                    <span className="flex items-center gap-1 font-mono text-xs">
                      <Calendar className="w-3.5 h-3.5 text-terminal-muted" />
                      <span>{formatDate(displayDate)}</span>
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 shrink-0 pt-2 md:pt-0">
              <Button
                variant="outline"
                size="sm"
                onClick={handleEvaluateMatch}
                disabled={reevaluateMutation.isPending}
                isLoading={reevaluateMutation.isPending}
                className="gap-1.5 text-xs shadow-subtle"
                title="Run deterministic Layer 1 & 2 evaluation for this opportunity"
              >
                <Sparkles className="w-3.5 h-3.5 text-terminal-primary" />
                <span>Evaluate Match</span>
              </Button>

              {job.canonical_application_url && (
                <a
                  href={job.canonical_application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full sm:w-auto"
                >
                  <Button variant="primary" size="sm" className="w-full gap-1.5 text-xs shadow-subtle">
                    <span>Apply on Company Site</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Button>
                </a>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Description Content Section */}
      <Card>
        <CardHeader className="border-b border-terminal-warmBorder/60 pb-3">
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <FileText className="w-4 h-4 text-terminal-primary" />
            <span>Job Description & Responsibilities</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          {job.description_text ? (
            <div className="text-xs sm:text-sm text-terminal-dark/90 font-sans leading-relaxed whitespace-pre-wrap space-y-4 font-normal">
              {job.description_text}
            </div>
          ) : (
            <p className="text-xs text-terminal-muted italic font-mono">
              No description text was captured for this canonical opportunity.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Provenance & Discovery Sources */}
      <JobSourcesList
        sources={job.sources || []}
        dedupFingerprint={job.dedup_fingerprint_sha256}
      />
    </div>
  );
}
